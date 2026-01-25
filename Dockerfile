FROM python:3.12-slim

# Install ffmpeg (required by yt-dlp for audio/video processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py config.py youtube_downloader.py ./
COPY templates/ templates/

# Create directories for downloads and transcripts
RUN mkdir -p downloads transcripts

# Expose the port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
