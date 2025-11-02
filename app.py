import os
import time
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from contextlib import asynccontextmanager
import youtube_downloader
import logging
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def cleanup_old_files():
    """Background task to delete files older than FILE_RETENTION_MINUTES."""
    while True:
        try:
            await asyncio.sleep(config.CLEANUP_INTERVAL_SECONDS)

            current_time = time.time()
            retention_seconds = config.FILE_RETENTION_MINUTES * 60

            # Clean up downloads directory (audio and video)
            if os.path.exists(config.DOWNLOADS_DIR):
                for filename in os.listdir(config.DOWNLOADS_DIR):
                    file_path = os.path.join(config.DOWNLOADS_DIR, filename)
                    if os.path.isfile(file_path):
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > retention_seconds:
                            os.remove(file_path)
                            logger.info(f"Deleted old file: {filename} (age: {file_age/60:.1f} minutes)")

            # Clean up transcripts directory
            if os.path.exists(config.TRANSCRIPTS_DIR):
                for filename in os.listdir(config.TRANSCRIPTS_DIR):
                    file_path = os.path.join(config.TRANSCRIPTS_DIR, filename)
                    if os.path.isfile(file_path):
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > retention_seconds:
                            os.remove(file_path)
                            logger.info(f"Deleted old transcript: {filename} (age: {file_age/60:.1f} minutes)")

        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifespan - start background tasks on startup."""
    # Start cleanup task
    cleanup_task = asyncio.create_task(cleanup_old_files())
    logger.info(f"Started file cleanup task (retention: {config.FILE_RETENTION_MINUTES} minutes, interval: {config.CLEANUP_INTERVAL_SECONDS} seconds)")

    yield

    # Cleanup on shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION,
    lifespan=lifespan
)

# Set up templates
templates = Jinja2Templates(directory=config.TEMPLATES_DIR)

# Create directories
os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)
os.makedirs(config.DOWNLOADS_DIR, exist_ok=True)


class YouTubeRequest(BaseModel):
    url: str
    download_type: str = "both"  # "transcript", "audio", "video", or "both"
    audio_quality: Optional[str] = None  # Audio quality in kbps (128, 192, 256, 320)
    video_quality: Optional[str] = None  # Video quality (360, 480, 720, 1080)


class DownloadResponse(BaseModel):
    success: bool
    message: str
    transcript_file: Optional[str] = None
    audio_file: Optional[str] = None
    video_file: Optional[str] = None
    video_id: Optional[str] = None


@app.get("/")
async def root(request: Request):
    """Serve the web interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/download", response_model=DownloadResponse)
async def download_youtube(request: YouTubeRequest):
    """
    Download YouTube video transcript, audio, and/or video.

    - **url**: YouTube video URL
    - **download_type**: Comma-separated list: "transcript,audio,video" or combinations like "transcript,audio"
    """
    try:
        logger.info(f"Received download request for: {request.url}, type: {request.download_type}")

        video_id = youtube_downloader.extract_video_id(request.url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        # Parse download types (support both legacy "both" and new comma-separated format)
        download_types = []
        if request.download_type == "both":
            download_types = ["transcript", "audio"]
        else:
            download_types = [t.strip() for t in request.download_type.split(',')]

        transcript_file = None
        audio_file = None
        video_file = None
        messages = []

        # Download transcript
        if "transcript" in download_types:
            logger.info("Starting transcript download...")
            transcript_file = youtube_downloader.download_transcript(request.url)
            if transcript_file:
                messages.append("Transcript downloaded successfully")
                logger.info(f"Transcript saved: {transcript_file}")
            else:
                messages.append("Transcript download failed (video may not have captions)")
                logger.warning("Transcript download failed")

        # Download audio
        if "audio" in download_types:
            logger.info("Starting audio download...")
            audio_quality = request.audio_quality if request.audio_quality else config.AUDIO_QUALITY
            audio_file = youtube_downloader.download_audio(request.url, audio_quality=audio_quality)
            if audio_file:
                time.sleep(2)
                messages.append(f"Audio downloaded successfully ({audio_quality} kbps)")
                logger.info(f"Audio saved: {audio_file}")
            else:
                messages.append("Audio download failed")
                logger.warning("Audio download failed")

        # Download video
        if "video" in download_types:
            logger.info("Starting video download...")
            video_quality = request.video_quality if request.video_quality else config.VIDEO_QUALITY
            video_file = youtube_downloader.download_video(request.url, video_quality=video_quality)
            if video_file:
                time.sleep(2)
                messages.append(f"Video downloaded successfully ({video_quality}p)")
                logger.info(f"Video saved: {video_file}")
            else:
                messages.append("Video download failed")
                logger.warning("Video download failed")

        # Check if at least one succeeded
        if not transcript_file and not audio_file and not video_file:
            return DownloadResponse(
                success=False,
                message="All downloads failed. " + ". ".join(messages),
                video_id=video_id
            )

        return DownloadResponse(
            success=True,
            message=". ".join(messages),
            transcript_file=os.path.basename(transcript_file) if transcript_file else None,
            audio_file=os.path.basename(audio_file) if audio_file else None,
            video_file=os.path.basename(video_file) if video_file else None,
            video_id=video_id
        )

    except Exception as e:
        logger.error(f"Error in download_youtube: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/{file_type}/{filename}")
async def get_file(file_type: str, filename: str):
    """Download file (transcript, audio, or video)."""
    # Map file types to their directories and media types
    file_config = {
        "transcript": {
            "dir": config.TRANSCRIPTS_DIR,
            "media_type": "text/plain"
        },
        "audio": {
            "dir": config.DOWNLOADS_DIR,
            "media_type": "audio/mpeg"
        },
        "video": {
            "dir": config.DOWNLOADS_DIR,
            "media_type": "video/mp4"
        }
    }

    # Validate file type
    if file_type not in file_config:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file_type}")

    file_dir = file_config[file_type]["dir"]
    media_type = file_config[file_type]["media_type"]

    # Check directory exists
    if not os.path.exists(file_dir):
        raise HTTPException(status_code=404, detail=f"{file_type.capitalize()} directory not found")

    # Build and verify file path
    file_path = os.path.join(file_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"{file_type.capitalize()} file not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
