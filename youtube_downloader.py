import os
import sys
import yt_dlp
import re
import config

# Detect if running on Android
try:
    from kivy.utils import platform
    IS_ANDROID = platform == 'android'
except ImportError:
    IS_ANDROID = False

# Global logger callback (can be set by calling code)
_logger_callback = None

def set_logger_callback(callback):
    """Set a callback function for logging messages."""
    global _logger_callback
    _logger_callback = callback

def _log(message):
    """Log a message using the callback or print."""
    if _logger_callback:
        _logger_callback(message)
    else:
        print(message)

# Get ffmpeg path for Android
def get_ffmpeg_path():
    """Get the path to ffmpeg binary, handling Android specially."""
    if IS_ANDROID:
        _log("Android detected - ffmpeg compiled as native libraries, not standalone binary")
        _log("yt-dlp on Android requires ffmpeg executable, which we don't have")
        _log("Solution: Download audio without post-processing (will be in original format)")
        return None
    else:
        # On desktop, assume ffmpeg is in PATH
        return None


def clean_vtt_to_text(vtt_content):
    """
    Convert VTT subtitle content to clean plain text.

    Args:
        vtt_content: Raw VTT file content as string

    Returns:
        Clean text with duplicates and metadata removed
    """
    # Remove all VTT timing tags like <00:00:00.480> and <c>
    content = re.sub(r'<[^>]+>', ' ', vtt_content)

    # Split into lines
    lines = content.split('\n')

    # Extract only actual text content
    text_lines = []
    seen_lines = set()  # Track duplicates

    for line in lines:
        line = line.strip()

        # Skip empty lines, WEBVTT header, timestamps, metadata, sound effects
        if (not line or
            line.startswith('WEBVTT') or
            '-->' in line or
            line.isdigit() or
            line.startswith('Kind:') or
            line.startswith('Language:') or
            line.startswith('NOTE') or
            line.startswith('[') and line.endswith(']')):  # Skip [Music], [Applause], etc
            continue

        # Only add unique non-empty lines to avoid duplicates
        if line and line not in seen_lines:
            text_lines.append(line)
            seen_lines.add(line)

    # Clean up extra spaces and format as proper text
    full_text = ' '.join(text_lines)
    # Replace multiple spaces with single space
    full_text = re.sub(r'\s+', ' ', full_text)
    # Add period at end if missing
    if full_text and not full_text.endswith(('.', '!', '?')):
        full_text += '.'

    return full_text.strip()


def extract_video_id(url):
    """Extract video ID from YouTube URL."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def download_transcript(video_url, output_dir=None):
    """Download transcript from YouTube video using yt-dlp."""
    try:
        # Use config default if not specified
        if output_dir is None:
            output_dir = config.TRANSCRIPTS_DIR

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Extract video ID
        video_id = extract_video_id(video_url)
        if not video_id:
            print(f"Error: Could not extract video ID from URL: {video_url}")
            return None

        print(f"Downloading transcript for video: {video_id}")

        # Use yt-dlp to download subtitles with video title as filename
        output_file = os.path.join(output_dir, '%(title)s')

        ydl_opts = {
            'skip_download': True,  # Don't download video
            'writesubtitles': True,  # Download subtitles
            'writeautomaticsub': True,  # Include auto-generated subs
            'subtitleslangs': [config.SUBTITLE_LANGUAGE],
            'subtitlesformat': config.SUBTITLE_FORMAT,
            'outtmpl': output_file,
            'quiet': config.YT_DLP_QUIET,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            # Get the actual title for the filename
            title = info.get('title', video_id)

        # yt-dlp saves as .vtt with title, find the file
        # Look for recently created .vtt file
        vtt_files = [f for f in os.listdir(output_dir) if f.endswith('.en.vtt')]
        if not vtt_files:
            print("No subtitles available for this video")
            return None

        # Get most recent vtt file
        vtt_files_with_time = [(f, os.path.getmtime(os.path.join(output_dir, f))) for f in vtt_files]
        vtt_files_with_time.sort(key=lambda x: x[1], reverse=True)
        vtt_filename = vtt_files_with_time[0][0]
        vtt_file = os.path.join(output_dir, vtt_filename)

        # Create txt filename from vtt filename
        txt_file = vtt_file.replace('.en.vtt', '_transcript.txt')

        if os.path.exists(vtt_file):
            # Read VTT file
            with open(vtt_file, 'r', encoding='utf-8') as f:
                vtt_content = f.read()

            # Convert VTT to clean text using helper function
            clean_text = clean_vtt_to_text(vtt_content)

            # Write clean text to file
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(clean_text)

            # Remove VTT file
            os.remove(vtt_file)

            # Update file timestamp to current time (resets age for cleanup purposes)
            os.utime(txt_file, None)

            print(f"Transcript saved to: {txt_file}")
            return txt_file
        else:
            print("No subtitles available for this video")
            return None

    except Exception as e:
        print(f"Error downloading transcript: {e}")
        return None


def download_audio(video_url, output_dir=None, audio_quality=None):
    """Download audio from YouTube video as MP3."""
    try:
        # Use config default if not specified
        if output_dir is None:
            output_dir = config.DOWNLOADS_DIR
        if audio_quality is None:
            audio_quality = config.AUDIO_QUALITY

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Debug: Check if directory is writable
        _log(f"Output directory: {output_dir}")
        _log(f"Directory exists: {os.path.exists(output_dir)}")
        _log(f"Directory is writable: {os.access(output_dir, os.W_OK)}")

        _log(f"Downloading audio from: {video_url} (quality: {audio_quality} kbps)")

        # On Android, we can't convert to MP3 without ffmpeg executable
        # Instead, download best audio format directly (usually m4a/opus/webm)
        if IS_ANDROID:
            _log("Android: Downloading audio in native format (m4a/opus/webm)")

            # Progress hook for debugging
            def progress_hook(d):
                if d['status'] == 'downloading':
                    _log(f"Downloading: {d.get('_percent_str', 'N/A')} | {d.get('_speed_str', 'N/A')}")
                elif d['status'] == 'finished':
                    _log(f"Download finished, file: {d.get('filename', 'unknown')}")
                elif d['status'] == 'error':
                    _log(f"Download error: {d.get('error', 'unknown')}")

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(output_dir, f'%(title)s_audio.%(ext)s'),
                'quiet': True,  # Must be True on Android to avoid stdout/stderr issues
                'no_warnings': True,
                'noprogress': True,  # Disable progress bar that causes stdout issues
                'progress_hooks': [progress_hook],
            }
        else:
            # On desktop, use ffmpeg to convert to MP3
            _log("Desktop: Converting audio to MP3")
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': config.AUDIO_FORMAT,
                    'preferredquality': audio_quality,
                }],
                'outtmpl': os.path.join(output_dir, f'%(title)s_audio_{audio_quality}kbps.%(ext)s'),
                'quiet': config.YT_DLP_QUIET,
                'no_warnings': config.YT_DLP_NO_WARNINGS,
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'video')

            # Build the filename based on platform
            if IS_ANDROID:
                # On Android, file extension varies (m4a, opus, webm)
                # Search for the downloaded file
                audio_files = [f for f in os.listdir(output_dir)
                              if f.startswith(title) and '_audio.' in f]
                if audio_files:
                    audio_filename = os.path.join(output_dir, audio_files[0])
                else:
                    # Fallback: find most recent audio file
                    audio_files = [f for f in os.listdir(output_dir)
                                  if '_audio.' in f or f.endswith(('.m4a', '.opus', '.webm'))]
                    if audio_files:
                        audio_files_with_time = [(f, os.path.getmtime(os.path.join(output_dir, f)))
                                                for f in audio_files]
                        audio_files_with_time.sort(key=lambda x: x[1], reverse=True)
                        audio_filename = os.path.join(output_dir, audio_files_with_time[0][0])
                    else:
                        _log("Error: Could not find downloaded audio file")
                        return None
            else:
                # On desktop, expect MP3
                audio_filename = os.path.join(output_dir, f'{title}_audio_{audio_quality}kbps.mp3')

                # Verify file exists
                if not os.path.exists(audio_filename):
                    _log(f"Warning: Expected file not found, searching for created file...")
                    # Fallback: find the most recent mp3 with the quality marker
                    mp3_files = [f for f in os.listdir(output_dir)
                                if f.endswith(f'_audio_{audio_quality}kbps.mp3')]
                    if mp3_files:
                        mp3_files_with_time = [(f, os.path.getmtime(os.path.join(output_dir, f)))
                                              for f in mp3_files]
                        mp3_files_with_time.sort(key=lambda x: x[1], reverse=True)
                        audio_filename = os.path.join(output_dir, mp3_files_with_time[0][0])

        # Update file timestamp to current time (resets age for cleanup purposes)
        if os.path.exists(audio_filename):
            os.utime(audio_filename, None)

            # Trigger media scan on Android so file shows up immediately
            if IS_ANDROID:
                try:
                    from android.storage import app_storage_path
                    from jnius import autoclass
                    MediaScannerConnection = autoclass('android.media.MediaScannerConnection')
                    context = autoclass('org.kivy.android.PythonActivity').mActivity
                    MediaScannerConnection.scanFile(context, [audio_filename], None, None)
                    _log("Media scan triggered for audio file")
                except Exception as e:
                    _log(f"Note: Could not trigger media scan: {e}")

            _log(f"✓ Audio saved to: {os.path.basename(audio_filename)}")
            return audio_filename
        else:
            _log(f"✗ Error: Audio file not found after download")
            return None

    except Exception as e:
        _log(f"Error downloading audio: {e}")
        _log("\nTroubleshooting tips:")
        _log("1. Update yt-dlp: pip install --upgrade yt-dlp")
        _log("2. Some videos may be restricted or unavailable")
        _log("3. Try using --audio-only flag if transcript works")
        return None


def download_video(video_url, output_dir=None, video_quality=None):
    """Download video from YouTube as MP4 with audio."""
    try:
        # Use config default if not specified
        if output_dir is None:
            output_dir = config.DOWNLOADS_DIR
        if video_quality is None:
            video_quality = config.VIDEO_QUALITY

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        _log(f"Downloading video from: {video_url} (quality: {video_quality}p)")

        # On Android, download without ffmpeg post-processing
        if IS_ANDROID:
            _log("Android: Downloading video in native format (mp4/webm)")
            _log("Note: For best seeking support, prefer pre-merged MP4 formats")
            ydl_opts = {
                # Prefer pre-merged MP4 formats which have better seeking support
                # mp4 containers are more likely to have moov atom at the beginning
                'format': f'best[height<={video_quality}][ext=mp4]/best[height<={video_quality}]',
                'outtmpl': os.path.join(output_dir, f'%(title)s_video_{video_quality}p.%(ext)s'),
                'quiet': True,  # Must be True on Android to avoid stdout/stderr issues
                'no_warnings': True,
                'noprogress': True,  # Disable progress bar that causes stdout issues
            }
        else:
            # On desktop, use ffmpeg for merging and conversion
            _log("Desktop: Merging and converting video with ffmpeg")
            ydl_opts = {
                # Download best video up to specified quality + best audio, merge them
                'format': f'bestvideo[height<={video_quality}]+bestaudio/best',
                'outtmpl': os.path.join(output_dir, f'%(title)s_video_{video_quality}p.%(ext)s'),
                'quiet': config.YT_DLP_QUIET,
                'no_warnings': config.YT_DLP_NO_WARNINGS,
                'merge_output_format': config.VIDEO_FORMAT,  # Merge to MP4
                'postprocessors': [{
                    'key': 'FFmpegVideoRemuxer',
                    'preferedformat': config.VIDEO_FORMAT,
                }, {
                    'key': 'FFmpegMetadata',
                }],
                # Force re-encode audio to AAC for better MP4 compatibility
                'postprocessor_args': {
                    'ffmpeg': ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k']
                },
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'video')
            # Build the actual filename that was created
            mp4_filename = os.path.join(output_dir, f'{title}_video_{video_quality}p.{config.VIDEO_FORMAT}')

        # Verify file exists
        if not os.path.exists(mp4_filename):
            print(f"Warning: Expected file not found, searching for created file...")
            # Fallback: find the most recent mp4 with the quality marker
            mp4_files = [f for f in os.listdir(output_dir) if f.endswith(f'_video_{video_quality}p.{config.VIDEO_FORMAT}')]
            if mp4_files:
                mp4_files_with_time = [(f, os.path.getmtime(os.path.join(output_dir, f))) for f in mp4_files]
                mp4_files_with_time.sort(key=lambda x: x[1], reverse=True)
                mp4_filename = os.path.join(output_dir, mp4_files_with_time[0][0])

        # Update file timestamp to current time (resets age for cleanup purposes)
        if os.path.exists(mp4_filename):
            os.utime(mp4_filename, None)

            # Trigger media scan on Android so file shows up immediately
            if IS_ANDROID:
                try:
                    from android.storage import app_storage_path
                    from jnius import autoclass
                    MediaScannerConnection = autoclass('android.media.MediaScannerConnection')
                    context = autoclass('org.kivy.android.PythonActivity').mActivity
                    MediaScannerConnection.scanFile(context, [mp4_filename], None, None)
                    _log("Media scan triggered for video file")
                except Exception as e:
                    _log(f"Note: Could not trigger media scan: {e}")

            _log(f"Video saved to: {mp4_filename}")
            return mp4_filename
        else:
            return None

    except Exception as e:
        _log(f"Error downloading video: {e}")
        _log("\nTroubleshooting tips:")
        _log("1. Update yt-dlp: pip install --upgrade yt-dlp")
        _log("2. Some videos may be restricted or unavailable")
        _log("3. Make sure FFmpeg is installed for video merging")
        return None


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python youtube_downloader.py <youtube_url> [options]")
        print("\nOptions:")
        print("  --transcript-only    Download only the transcript")
        print("  --audio-only         Download only the audio (MP3)")
        print("  --video-only         Download only the video (MP4)")
        print("\nExample:")
        print("  python youtube_downloader.py https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        print("  python youtube_downloader.py https://www.youtube.com/watch?v=dQw4w9WgXcQ --video-only")
        sys.exit(1)

    video_url = sys.argv[1]

    # Parse options
    transcript_only = '--transcript-only' in sys.argv
    audio_only = '--audio-only' in sys.argv
    video_only = '--video-only' in sys.argv

    # If no specific option is provided, download transcript and audio (original behavior)
    download_default = not transcript_only and not audio_only and not video_only

    print(f"Processing video: {video_url}\n")

    # Download transcript
    if transcript_only or download_default:
        transcript_file = download_transcript(video_url)
        if transcript_file:
            print(f"✓ Transcript downloaded successfully\n")
        else:
            print(f"✗ Failed to download transcript\n")

    # Download audio
    if audio_only or download_default:
        audio_file = download_audio(video_url)
        if audio_file:
            print(f"✓ Audio downloaded successfully\n")
        else:
            print(f"✗ Failed to download audio\n")

    # Download video
    if video_only:
        video_file = download_video(video_url)
        if video_file:
            print(f"✓ Video downloaded successfully\n")
        else:
            print(f"✗ Failed to download video\n")

    print("Done!")


if __name__ == "__main__":
    main()
