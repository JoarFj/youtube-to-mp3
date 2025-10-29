"""
Configuration settings for YouTube downloader application.
"""

import os

# Directory settings
TRANSCRIPTS_DIR = os.getenv('TRANSCRIPTS_DIR', 'transcripts')
DOWNLOADS_DIR = os.getenv('DOWNLOADS_DIR', 'downloads')
TEMPLATES_DIR = os.getenv('TEMPLATES_DIR', 'templates')

# Audio settings
AUDIO_QUALITY = os.getenv('AUDIO_QUALITY', '192')  # kbps
AUDIO_FORMAT = os.getenv('AUDIO_FORMAT', 'mp3')
AUDIO_QUALITY_OPTIONS = ['128', '192', '256', '320']  # Available audio quality options in kbps

# Video settings
VIDEO_FORMAT = os.getenv('VIDEO_FORMAT', 'mp4')
VIDEO_QUALITY = os.getenv('VIDEO_QUALITY', '720')  # 720p, 1080p, best, etc.
VIDEO_QUALITY_OPTIONS = ['360', '480', '720', '1080']  # Available video quality options

# Subtitle settings
SUBTITLE_LANGUAGE = os.getenv('SUBTITLE_LANGUAGE', 'en')
SUBTITLE_FORMAT = os.getenv('SUBTITLE_FORMAT', 'vtt')

# API settings
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', '8000'))
API_TITLE = "YouTube Transcript & Media Downloader API"
API_DESCRIPTION = "Download YouTube video transcripts, audio (MP3), and video (MP4)"
API_VERSION = "1.0.0"

# yt-dlp settings
YT_DLP_QUIET = True
YT_DLP_NO_WARNINGS = False

# Cleanup settings
FILE_RETENTION_MINUTES = int(os.getenv('FILE_RETENTION_MINUTES', '1'))  # How long to keep files before auto-deletion
CLEANUP_INTERVAL_SECONDS = int(os.getenv('CLEANUP_INTERVAL_SECONDS', '60'))  # How often to run cleanup task
