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

# Subtitle settings
SUBTITLE_LANGUAGE = os.getenv('SUBTITLE_LANGUAGE', 'en')
SUBTITLE_FORMAT = os.getenv('SUBTITLE_FORMAT', 'vtt')

# API settings
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', '8000'))
API_TITLE = "YouTube Transcript & Audio API"
API_DESCRIPTION = "Download YouTube video transcripts and convert videos to MP3"
API_VERSION = "1.0.0"

# yt-dlp settings
YT_DLP_QUIET = True
YT_DLP_NO_WARNINGS = False
