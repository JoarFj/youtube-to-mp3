import os
import time
import asyncio
import json
import queue
import threading
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
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


@app.post("/download-stream")
async def download_youtube_stream(request: YouTubeRequest):
    """
    Download YouTube content with real-time progress updates via Server-Sent Events.
    """
    video_id = youtube_downloader.extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    # Parse download types
    download_types = []
    if request.download_type == "both":
        download_types = ["transcript", "audio"]
    else:
        download_types = [t.strip() for t in request.download_type.split(',')]

    progress_queue = queue.Queue()

    def progress_callback(media_type, percent, speed, eta):
        progress_queue.put({
            'type': 'progress',
            'media_type': media_type,
            'percent': percent,
            'speed': speed,
            'eta': eta
        })

    def download_task():
        results = {
            'transcript_file': None,
            'audio_file': None,
            'video_file': None,
            'messages': []
        }

        # Download transcript
        if "transcript" in download_types:
            progress_queue.put({'type': 'status', 'message': 'Fetching transcript...'})
            transcript_file = youtube_downloader.download_transcript(
                request.url, progress_callback=progress_callback
            )
            if transcript_file:
                results['transcript_file'] = os.path.basename(transcript_file)
                results['messages'].append("Transcript downloaded")
            else:
                results['messages'].append("Transcript failed (no captions)")

        # Download audio
        if "audio" in download_types:
            audio_quality = request.audio_quality if request.audio_quality else config.AUDIO_QUALITY
            progress_queue.put({'type': 'status', 'message': f'Downloading audio ({audio_quality} kbps)...'})
            audio_file = youtube_downloader.download_audio(
                request.url, audio_quality=audio_quality, progress_callback=progress_callback
            )
            if audio_file:
                results['audio_file'] = os.path.basename(audio_file)
                results['messages'].append(f"Audio downloaded ({audio_quality} kbps)")
            else:
                results['messages'].append("Audio download failed")

        # Download video
        if "video" in download_types:
            video_quality = request.video_quality if request.video_quality else config.VIDEO_QUALITY
            progress_queue.put({'type': 'status', 'message': f'Downloading video ({video_quality}p)...'})
            video_file = youtube_downloader.download_video(
                request.url, video_quality=video_quality, progress_callback=progress_callback
            )
            if video_file:
                results['video_file'] = os.path.basename(video_file)
                results['messages'].append(f"Video downloaded ({video_quality}p)")
            else:
                results['messages'].append("Video download failed")

        progress_queue.put({'type': 'done', 'results': results})

    def generate():
        # Start download in background thread
        thread = threading.Thread(target=download_task)
        thread.start()

        while True:
            try:
                data = progress_queue.get(timeout=0.5)
                yield f"data: {json.dumps(data)}\n\n"
                if data.get('type') == 'done':
                    break
            except queue.Empty:
                # Send keepalive
                yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"

        thread.join()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/files/transcript/{filename}")
async def get_transcript(filename: str):
    """Download transcript file."""
    if not os.path.exists(config.TRANSCRIPTS_DIR):
        raise HTTPException(status_code=404, detail="Transcripts directory not found")

    file_path = os.path.join(config.TRANSCRIPTS_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Transcript file not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="text/plain"
    )


@app.get("/files/audio/{filename}")
async def get_audio(filename: str):
    """Download audio file."""
    if not os.path.exists(config.DOWNLOADS_DIR):
        raise HTTPException(status_code=404, detail="Downloads directory not found")

    file_path = os.path.join(config.DOWNLOADS_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="audio/mpeg"
    )


@app.get("/files/video/{filename}")
async def get_video(filename: str):
    """Download video file."""
    if not os.path.exists(config.DOWNLOADS_DIR):
        raise HTTPException(status_code=404, detail="Downloads directory not found")

    file_path = os.path.join(config.DOWNLOADS_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="video/mp4"
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
