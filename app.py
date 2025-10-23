import os
import time
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import youtube_downloader
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="YouTube Transcript & Audio API",
    description="Download YouTube video transcripts and convert videos to MP3",
    version="1.0.0"
)

# Create directories
os.makedirs("transcripts", exist_ok=True)
os.makedirs("downloads", exist_ok=True)


class YouTubeRequest(BaseModel):
    url: str
    download_type: str = "both"  # "transcript", "audio", or "both"


class DownloadResponse(BaseModel):
    success: bool
    message: str
    transcript_file: Optional[str] = None
    audio_file: Optional[str] = None
    video_id: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web interface."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Transcript & Audio Downloader</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #555;
            }
            input[type="text"] {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                box-sizing: border-box;
            }
            select {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                width: 100%;
            }
            button:hover {
                background-color: #45a049;
            }
            button:disabled {
                background-color: #cccccc;
                cursor: not-allowed;
            }
            .result {
                margin-top: 20px;
                padding: 15px;
                border-radius: 5px;
                display: none;
            }
            .success {
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
            }
            .error {
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                color: #721c24;
            }
            .loading {
                text-align: center;
                color: #666;
                margin-top: 20px;
                display: none;
            }
            .download-link {
                display: inline-block;
                margin: 10px 10px 10px 0;
                padding: 10px 20px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
            }
            .download-link:hover {
                background-color: #0056b3;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>YouTube Transcript & Audio Downloader</h1>
            <form id="downloadForm">
                <div class="form-group">
                    <label for="url">YouTube URL:</label>
                    <input type="text" id="url" name="url" placeholder="https://www.youtube.com/watch?v=..." required>
                </div>
                <div class="form-group">
                    <label for="downloadType">Download Type:</label>
                    <select id="downloadType" name="downloadType">
                        <option value="both">Both (Transcript + Audio)</option>
                        <option value="transcript">Transcript Only</option>
                        <option value="audio">Audio Only</option>
                    </select>
                </div>
                <button type="submit" id="submitBtn">Download</button>
            </form>
            <div class="loading" id="loading">
                Processing... This may take a minute...
            </div>
            <div class="result" id="result"></div>
        </div>

        <script>
            document.getElementById('downloadForm').addEventListener('submit', async (e) => {
                e.preventDefault();

                const submitBtn = document.getElementById('submitBtn');
                const loading = document.getElementById('loading');
                const result = document.getElementById('result');

                const url = document.getElementById('url').value;
                const downloadType = document.getElementById('downloadType').value;

                // Reset and show loading
                result.style.display = 'none';
                loading.style.display = 'block';
                submitBtn.disabled = true;

                try {
                    const response = await fetch('/download', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            url: url,
                            download_type: downloadType
                        })
                    });

                    const data = await response.json();

                    loading.style.display = 'none';
                    result.style.display = 'block';

                    if (data.success) {
                        result.className = 'result success';
                        let html = '<strong>Success!</strong><br>' + data.message + '<br><br>';

                        if (data.transcript_file) {
                            html += `<a href="/files/transcript/${data.video_id}" class="download-link" download>Download Transcript</a>`;
                        }
                        if (data.audio_file) {
                            html += `<a href="/files/audio/${data.video_id}" class="download-link" download>Download Audio</a>`;
                        }

                        result.innerHTML = html;
                    } else {
                        result.className = 'result error';
                        result.innerHTML = '<strong>Error:</strong><br>' + data.message;
                    }
                } catch (error) {
                    loading.style.display = 'none';
                    result.style.display = 'block';
                    result.className = 'result error';
                    result.innerHTML = '<strong>Error:</strong><br>Failed to connect to server: ' + error.message;
                } finally {
                    submitBtn.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


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
    file_path = f"transcripts/{video_id}_transcript.txt"

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
    downloads_dir = "downloads"

    if not os.path.exists(downloads_dir):
        raise HTTPException(status_code=404, detail="Downloads directory not found")

    mp3_files = [f for f in os.listdir(downloads_dir) if f.endswith('.mp3')]

    # Find the most recent file (as a simple heuristic)
    if not mp3_files:
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Get the most recently modified file
    mp3_files_with_time = [(f, os.path.getmtime(os.path.join(downloads_dir, f))) for f in mp3_files]
    mp3_files_with_time.sort(key=lambda x: x[1], reverse=True)
    audio_file = mp3_files_with_time[0][0]
    file_path = os.path.join(downloads_dir, audio_file)

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
