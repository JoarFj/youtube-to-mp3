import os
import time
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import youtube_downloader
import logging
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION
)

# Set up templates
templates = Jinja2Templates(directory=config.TEMPLATES_DIR)

# Create directories
os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)
os.makedirs(config.DOWNLOADS_DIR, exist_ok=True)


class YouTubeRequest(BaseModel):
    url: str
    download_type: str = "both"  # "transcript", "audio", or "both"


class DownloadResponse(BaseModel):
    success: bool
    message: str
    transcript_file: Optional[str] = None
    audio_file: Optional[str] = None
    video_id: Optional[str] = None


@app.get("/")
async def root(request: Request):
    """Serve the web interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/download", response_model=DownloadResponse)
async def download_youtube(request: YouTubeRequest):
    """
    Download YouTube video transcript and/or audio.

    - **url**: YouTube video URL
    - **download_type**: "transcript", "audio", or "both"
    """
    try:
        logger.info(f"Received download request for: {request.url}, type: {request.download_type}")

        video_id = youtube_downloader.extract_video_id(request.url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        transcript_file = None
        audio_file = None
        messages = []

        # Download transcript
        if request.download_type in ["transcript", "both"]:
            logger.info("Starting transcript download...")
            transcript_file = youtube_downloader.download_transcript(request.url)
            if transcript_file:
                messages.append("Transcript downloaded successfully")
                logger.info(f"Transcript saved: {transcript_file}")
            else:
                messages.append("Transcript download failed (video may not have captions)")
                logger.warning("Transcript download failed")

        # Download audio - uses exact same logic as CLI
        if request.download_type in ["audio", "both"]:
            logger.info("Starting audio download...")
            audio_file = youtube_downloader.download_audio(request.url)
            if audio_file:
                # Wait a moment to ensure file is fully written
                time.sleep(2)
                messages.append("Audio downloaded successfully")
                logger.info(f"Audio saved: {audio_file}")
            else:
                messages.append("Audio download failed")
                logger.warning("Audio download failed")

        # Check if at least one succeeded
        if not transcript_file and not audio_file:
            return DownloadResponse(
                success=False,
                message="Failed to download both transcript and audio. " + ". ".join(messages),
                video_id=video_id
            )

        return DownloadResponse(
            success=True,
            message=". ".join(messages),
            transcript_file=transcript_file,
            audio_file=audio_file,
            video_id=video_id
        )

    except Exception as e:
        logger.error(f"Error in download_youtube: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/transcript/{video_id}")
async def get_transcript(video_id: str):
    """Download transcript file."""
    file_path = f"{config.TRANSCRIPTS_DIR}/{video_id}_transcript.txt"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Transcript file not found")

    return FileResponse(
        path=file_path,
        filename=f"{video_id}_transcript.txt",
        media_type="text/plain"
    )


@app.get("/files/audio/{video_id}")
async def get_audio(video_id: str):
    """Download audio file."""
    # Find the MP3 file in downloads directory
    if not os.path.exists(config.DOWNLOADS_DIR):
        raise HTTPException(status_code=404, detail="Downloads directory not found")

    mp3_files = [f for f in os.listdir(config.DOWNLOADS_DIR) if f.endswith(f'.{config.AUDIO_FORMAT}')]

    # Find the most recent file (as a simple heuristic)
    if not mp3_files:
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Get the most recently modified file
    mp3_files_with_time = [(f, os.path.getmtime(os.path.join(config.DOWNLOADS_DIR, f))) for f in mp3_files]
    mp3_files_with_time.sort(key=lambda x: x[1], reverse=True)
    audio_file = mp3_files_with_time[0][0]
    file_path = os.path.join(config.DOWNLOADS_DIR, audio_file)

    return FileResponse(
        path=file_path,
        filename=audio_file,
        media_type="audio/mpeg"
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
