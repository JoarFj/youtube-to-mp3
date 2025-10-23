import os
import sys
import yt_dlp
import re


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


def download_transcript(video_url, output_dir='transcripts'):
    """Download transcript from YouTube video using yt-dlp."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Extract video ID
        video_id = extract_video_id(video_url)
        if not video_id:
            print(f"Error: Could not extract video ID from URL: {video_url}")
            return None

        print(f"Downloading transcript for video: {video_id}")

        # Use yt-dlp to download subtitles
        output_file = os.path.join(output_dir, f"{video_id}_transcript")

        ydl_opts = {
            'skip_download': True,  # Don't download video
            'writesubtitles': True,  # Download subtitles
            'writeautomaticsub': True,  # Include auto-generated subs
            'subtitleslangs': ['en'],  # Prefer English
            'subtitlesformat': 'vtt',  # VTT format
            'outtmpl': output_file,
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)

        # yt-dlp saves as .vtt, convert to plain text
        vtt_file = f"{output_file}.en.vtt"
        txt_file = f"{output_file}.txt"

        if os.path.exists(vtt_file):
            # Read VTT and convert to plain text
            with open(vtt_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Remove all VTT timing tags like <00:00:00.480> and <c>
            content = re.sub(r'<[^>]+>', ' ', content)

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

            # Clean up extra spaces and write as proper sentences
            # Join with spaces, then clean up multiple spaces
            full_text = ' '.join(text_lines)
            # Replace multiple spaces with single space
            full_text = re.sub(r'\s+', ' ', full_text)
            # Add period at end if missing
            if full_text and not full_text.endswith(('.', '!', '?')):
                full_text += '.'

            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(full_text.strip())

            # Remove VTT file
            os.remove(vtt_file)

            print(f"Transcript saved to: {txt_file}")
            return txt_file
        else:
            print("No subtitles available for this video")
            return None

    except Exception as e:
        print(f"Error downloading transcript: {e}")
        return None


def download_audio(video_url, output_dir='downloads'):
    """Download audio from YouTube video as MP3."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        print(f"Downloading audio from: {video_url}")

        # Configure yt-dlp options with updated settings to avoid 403 errors
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            # Replace extension with mp3
            mp3_filename = os.path.splitext(filename)[0] + '.mp3'

        print(f"Audio saved to: {mp3_filename}")
        return mp3_filename

    except Exception as e:
        print(f"Error downloading audio: {e}")
        print("\nTroubleshooting tips:")
        print("1. Update yt-dlp: pip install --upgrade yt-dlp")
        print("2. Some videos may be restricted or unavailable")
        print("3. Try using --audio-only flag if transcript works")
        return None


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python youtube_downloader.py <youtube_url> [--transcript-only] [--audio-only]")
        print("\nOptions:")
        print("  --transcript-only    Download only the transcript")
        print("  --audio-only         Download only the audio")
        print("\nExample:")
        print("  python youtube_downloader.py https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        sys.exit(1)

    video_url = sys.argv[1]

    # Parse options
    transcript_only = '--transcript-only' in sys.argv
    audio_only = '--audio-only' in sys.argv

    # If no specific option is provided, download both
    download_both = not transcript_only and not audio_only

    print(f"Processing video: {video_url}\n")

    # Download transcript
    if transcript_only or download_both:
        transcript_file = download_transcript(video_url)
        if transcript_file:
            print(f"✓ Transcript downloaded successfully\n")
        else:
            print(f"✗ Failed to download transcript\n")

    # Download audio
    if audio_only or download_both:
        audio_file = download_audio(video_url)
        if audio_file:
            print(f"✓ Audio downloaded successfully\n")
        else:
            print(f"✗ Failed to download audio\n")

    print("Done!")


if __name__ == "__main__":
    main()
