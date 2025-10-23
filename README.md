# YouTube Transcript & Audio Downloader

A Python application that downloads YouTube video transcripts and converts videos to MP3 audio files. Available as both a command-line tool and a REST API with web interface.

## Features

- Download YouTube video transcripts as text files
- Download YouTube videos as MP3 audio files
- Support for both operations or individually
- Simple command-line interface
- FastAPI REST API with endpoints
- Web interface for easy usage

## Requirements

- Python 3.7+
- FFmpeg (required for audio conversion)

### Installing FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

## Installation

1. Clone or download this repository

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Option 1: Command Line Interface

#### Download both transcript and audio:
```bash
python youtube_downloader.py https://www.youtube.com/watch?v=VIDEO_ID
```

#### Download transcript only:
```bash
python youtube_downloader.py https://www.youtube.com/watch?v=VIDEO_ID --transcript-only
```

#### Download audio only:
```bash
python youtube_downloader.py https://www.youtube.com/watch?v=VIDEO_ID --audio-only
```

### Option 2: FastAPI Web Application

#### Start the API server:
```bash
python api.py
```

Or with uvicorn:
```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

#### Access the web interface:
Open your browser and go to: `http://localhost:8000`

#### API Endpoints:

**POST /download**
```bash
curl -X POST "http://localhost:8000/download" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID", "download_type": "both"}'
```

**GET /files/transcript/{video_id}**
- Download the transcript file

**GET /files/audio/{video_id}**
- Download the audio file

**GET /health**
- Health check endpoint

**GET /docs**
- Interactive API documentation (Swagger UI)

**GET /redoc**
- Alternative API documentation (ReDoc)

## Output

- Transcripts are saved to the `transcripts/` directory as `{video_id}_transcript.txt`
- Audio files are saved to the `downloads/` directory as `{video_title}.mp3`

## Libraries Used

- [youtube-transcript-api](https://pypi.org/project/youtube-transcript-api/) - For downloading video transcripts
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - For downloading and converting video to audio
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework for building APIs
- [Uvicorn](https://www.uvicorn.org/) - ASGI server for running FastAPI applications

## Notes

- Some videos may not have transcripts available
- The tool requires an active internet connection
- Audio quality is set to 192 kbps by default
- Make sure you have permission to download content from the videos you're accessing

## License

This project is for educational purposes. Please respect YouTube's Terms of Service and copyright laws.
