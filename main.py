from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import shutil
import os
import json
from services import (
    create_trailer,
    process_video_segments,
    detect_scenes,
    analyze_scene_emotions,
    generate_caption,
    extract_clips_with_captions
)

app = FastAPI(title="Movie Trailer Generator API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

class CaptionConfig(BaseModel):
    font: str = "Arial"
    font_size: int = 24
    color: str = "white"
    bg_color: str = "black"
    position: str = "bottom"

def save_upload_file(upload_file: UploadFile) -> str:
    if not upload_file.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a video file.")
    file_path = os.path.join(UPLOAD_DIR, upload_file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return file_path

@app.post("/trailer/generate")
async def generate_trailer(
    file: UploadFile = File(...),
    scene_types: List[str] = Form(["emotion", "fight"]),
    caption_font: str = Form("Arial"),
    caption_size: int = Form(24),
    caption_color: str = Form("white"),
    caption_bg: str = Form("black"),
    caption_position: str = Form("bottom"),
    duration: int = Form(90),
    style: str = Form("cinematic")
):
    caption_config = CaptionConfig(
        font=caption_font,
        font_size=caption_size,
        color=caption_color,
        bg_color=caption_bg,
        position=caption_position
    )
    
    input_path = save_upload_file(file)
    try:
        result_path = create_trailer(
            input_path,
            scene_types=scene_types,
            caption_style=caption_config.dict(),
            max_duration=duration
        )
        
        if result_path:
            return FileResponse(
                result_path,
                media_type="video/mp4",
                filename=f"trailer_{style}_{duration}s.mp4"
            )
        raise HTTPException(status_code=500, detail="Failed to generate trailer")
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

@app.post("/cleanup/")
async def cleanup_directories():
    for directory in [UPLOAD_DIR, OUTPUT_DIR]:
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory)
    return {"status": "Cleanup completed", "directories_cleaned": [UPLOAD_DIR, OUTPUT_DIR]}

@app.get("/health/")
async def health_check():
    return {
        "status": "healthy",
        "upload_dir": os.path.exists(UPLOAD_DIR),
        "output_dir": os.path.exists(OUTPUT_DIR)
    }
