# Trailer - Automatic Social Media Clip Generator

## 🚀 Overview
Trailer is an automated system that extracts short, engaging clips from long-form videos, generates captions, and creates social media-ready content. This project leverages AI to streamline content creation, making it easier for creators to repurpose their videos.

## ✨ Features
- **Extract Highlights**: Automatically generate 5 short clips from a long-form video
- **Customizable Clips**: Users can override default clip selections
- **AI-Generated Captions**: Automatic captions for each clip
- **Thumbnail Generation**: Generate attention-grabbing thumbnails
- **FastAPI Backend**: Provides APIs for video processing
- **Command-line Script**: Automate API calls from a terminal

## 🏗️ Tech Stack
- **Backend**: FastAPI
- **AI Models**: OpenAI Whisper for transcription, Google Perspective API for moderation
- **Video Processing**: FFmpeg
- **Deployment**: Heroku (or any cloud platform)

## 🛠️ Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/shanmukhpetla/trailer.git
   cd trailer
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```

## 🚀 Usage
### API Endpoints
- `POST /generate-clips/` - Upload a video to generate short clips
- `GET /clips/{video_id}` - Retrieve generated clips
- `POST /generate-thumbnail/` - Generate a thumbnail from a video frame

### CLI Usage
A Python script is available to interact with the API:
```bash
python cli.py --video input.mp4 --output-dir clips/
```

## 📌 Roadmap
- [ ] Add user authentication
- [ ] Support more customization options for clips
- [ ] Improve AI-driven highlight selection

## 🤝 Contributing
Pull requests are welcome! Please open an issue first to discuss proposed changes.

## 📜 License
This project is licensed under the MIT License.

---

### 🔗 Connect with Me
[GitHub](https://github.com/shanmukhpetla) | [LinkedIn](https://linkedin.com/in/shanmukhpetla)

