from scenedetect.detectors import ContentDetector
from scenedetect.scene_manager import save_images
from moviepy.editor import VideoFileClip
import moviepy.editor as mp
import openai
import tempfile
import os
import json
import re
from config import OPENAI_API_KEY
from scenedetect import VideoManager, SceneManager
import subprocess

openai.api_key = OPENAI_API_KEY

def process_video_segments(video_path, segment_duration=30):
    video = VideoFileClip(video_path, fps_source='fps')
    duration = video.duration
    segments = []
    for start in range(0, int(duration), segment_duration):
        end = min(start + segment_duration, duration)
        segments.append((start, end))
    print("✅ Video segmentation completed successfully")
    return segments, duration, video

def extract_audio(video_clip, output_path):
    """Extract audio using direct moviepy processing."""
    try:
        if video_clip.audio:
            video_clip.audio.write_audiofile(
                output_path,
                ffmpeg_params=[
                    "-ac", "1",
                    "-ar", "16000",
                    "-acodec", "pcm_s16le",
                    "-y"  # Force overwrite
                ],
                verbose=False,
                logger=None,
                fps=16000
            )
            print("⚡ Audio extraction completed successfully")
            return True
    except:
        # Direct ffmpeg approach with timeout
        command = [
            'ffmpeg', '-y',
            '-i', video_clip.filename,
            '-vn', '-acodec', 'pcm_s16le',
            '-ar', '16000', '-ac', '1',
            output_path
        ]
        subprocess.run(command, capture_output=True, timeout=300)  # 5-minute timeout
        print("⚡ Audio extraction completed using optimized method")
        return True


def detect_scenes(video_path):
    try:
        video_manager = VideoManager([video_path])
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector())
        video_manager.set_downscale_factor()
        video_manager.start()
        scene_manager.detect_scenes(frame_source=video_manager)
        scene_list = scene_manager.get_scene_list()
        scenes = [(start.get_seconds(), end.get_seconds()) for start, end in scene_list]
        video_manager.release()
        print("✅ Scene detection completed successfully")
        return scenes
    except Exception as e:
        print(f"❌ Error detecting scenes: {e}")
        return []

def analyze_scene_emotions(transcripts, scenes, intensity_threshold=5):
    scene_emotions = []
    print(f"Analyzing {len(scenes)} scenes for emotional content...")
    
    for start, end in scenes:
        relevant_text = " ".join([t[1] for t in transcripts if start <= t[0] <= end])
        if not relevant_text:
            continue
            
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an AI that analyzes emotional content in text. Focus on detecting intimate romantic scenes (kisses, embraces), comedy moments, and emotional scenes with high intensity."},
                    {"role": "user", "content": f"Analyze the following text and identify the primary emotions present. Return a JSON with 'emotions' as an array of emotions (romantic_kiss, romantic_embrace, sad, happy, funny, etc.) and 'intensity' as a number from 1-10: {relevant_text}"}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            try:
                emotion_data = json.loads(content)
            except:
                # Fallback regex extraction
                emotions_match = re.search(r'"emotions":\s*\[(.*?)\]', content, re.DOTALL)
                intensity_match = re.search(r'"intensity":\s*(\d+)', content)
                emotions = []
                if emotions_match:
                    emotions_str = emotions_match.group(1)
                    emotions = [e.strip().strip('"\'') for e in emotions_str.split(',')]
                intensity = 5
                if intensity_match:
                    intensity = int(intensity_match.group(1))
                emotion_data = {
                    "emotions": emotions,
                    "intensity": intensity
                }
            
            # Only include scenes with intensity above threshold
            if emotion_data.get("intensity", 0) >= intensity_threshold:
                scene_emotions.append({
                    "start": start,
                    "end": end,
                    "emotions": emotion_data.get("emotions", []),
                    "intensity": emotion_data.get("intensity", 5),
                    "text": relevant_text
                })
                
        except Exception as e:
            print(f"❌ Error analyzing scene emotions {start}-{end}: {e}")
    
    print("✅ Scene emotion analysis completed successfully")
    return scene_emotions



def generate_caption(text, style=None):
    if not text.strip():
        return ""
    style_prompt = f" with style {style}" if style else ""
    prompt = f"Generate captions for the following text{style_prompt}: {text}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates captions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        print("✅ Caption generation completed successfully")
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error generating caption: {e}")
        return text[:50] + "..." if len(text) > 50 else text

def extract_clips_with_captions(video, transcripts, timestamps, output_path, caption_style=None):
    clips = []
    for start, end in timestamps:
        try:
            clip = video.subclip(start, end)
            relevant_text = " ".join([t[1] for t in transcripts if start <= t[0] <= end])
            if relevant_text:
                caption_text = generate_caption(relevant_text, caption_style)
                caption = mp.TextClip(caption_text, fontsize=24, color='white', bg_color='black')
                caption = caption.set_position(("center", "bottom")).set_duration(clip.duration)
                clip = mp.CompositeVideoClip([clip, caption])
            clips.append(clip)
        except Exception as e:
            print(f"❌ Error processing clip {start}-{end}: {e}")
    
    if not clips:
        print("❌ No valid clips to process")
        return None
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_video = mp.concatenate_videoclips(clips)
    final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
    print("✅ Clip extraction and caption overlay completed successfully")
    return output_path



def parse_timestamps_from_response(content):
    """Parse timestamps from OpenAI response with better error handling."""
    try:
        # First try direct JSON parsing
        return json.loads(content)
    except json.JSONDecodeError:
        # If that fails, try to extract JSON array using regex
        match = re.search(r'\[\s*\[.+?\]\s*\]', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
                
        # If all else fails, look for pairs of numbers
        pairs = re.findall(r'\[(\d+\.?\d*),\s*(\d+\.?\d*)\]', content)
        if pairs:
            return [[float(start), float(end)] for start, end in pairs]
            
    return []

def create_trailer(video_path, scene_types=None, caption_style=None, max_duration=90):
    if not os.path.exists(video_path):
        print(f"Video file not found: {video_path}")
        return None

    if not scene_types:
        scene_types = ["exciting"]

    segments, duration, video = process_video_segments(video_path)
    transcripts = []
    scenes = detect_scenes(video_path)

    try:
        # Extract transcripts from video segments
        for start, end in segments:
            segment = video.subclip(start, end)
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                if extract_audio(segment, temp_audio.name):
                    with open(temp_audio.name, "rb") as audio_file:
                        try:
                            result = openai.Audio.transcribe("whisper-1", audio_file)
                            transcripts.append((start, result["text"]))
                        except Exception as e:
                            print(f"Error transcribing segment {start}-{end}: {e}")
                os.unlink(temp_audio.name)
            segment.close()

        if not transcripts:
            print("No transcripts generated")
            return None

        if scenes:
            print(f"Analyzing {len(scenes)} scenes for emotional content...")
            scene_emotions = analyze_scene_emotions(transcripts, scenes)
            
            # Filter scenes based on requested scene types and duration
            matching_scenes = []
            total_duration = 0
            
            for scene in scene_emotions:
                scene_duration = scene["end"] - scene["start"]
                if total_duration + scene_duration <= max_duration:
                    if any(emotion_type.lower() in [e.lower() for e in scene["emotions"]] for emotion_type in scene_types):
                        matching_scenes.append((scene["start"], scene["end"]))
                        total_duration += scene_duration
                        if total_duration >= max_duration:
                            break

            if matching_scenes:
                print(f"Found {len(matching_scenes)} scenes matching requested types: {scene_types}")
                output_path = os.path.join("outputs", f"trailer_{'_'.join(scene_types)}.mp4")
                result_path = extract_clips_with_captions(video, transcripts, matching_scenes, output_path, caption_style)
                return result_path

        # Fallback to OpenAI scene selection if needed
        combined_transcript = " ".join([t[1] for t in transcripts])
        scene_types_str = ", ".join(scene_types)
        
        system_prompt = f"""You are a video editing AI. Analyze the transcript and identify timestamps for {scene_types_str} scenes.
        Return timestamps as a JSON array of arrays: [[start1, end1], [start2, end2]].
        Total duration should not exceed {max_duration} seconds.
        Each timestamp should represent a coherent scene that matches one of these types: {scene_types_str}."""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined_transcript}
            ],
            temperature=0.7
        )

        content = response.choices[0].message.content.strip()
        timestamps = parse_timestamps_from_response(content)

        if timestamps:
            output_path = os.path.join("outputs", f"trailer_{'_'.join(scene_types)}.mp4")
            result_path = extract_clips_with_captions(video, transcripts, timestamps, output_path, caption_style)
            return result_path
        else:
            print("No suitable timestamps found")
            return None

    except Exception as e:
        print(f"Error creating trailer: {e}")
        return None
    finally:
        video.close()
