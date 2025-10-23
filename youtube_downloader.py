import os
import sys
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
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
    """Download transcript from YouTube video."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Extract video ID
        video_id = extract_video_id(video_url)
        if not video_id:
            print(f"Error: Could not extract video ID from URL: {video_url}")
            return None

        print(f"Downloading transcript for video: {video_id}")

        # Try to get transcript (try multiple languages and auto-generated)
        transcript = None
        try:
            # First try to get manually created transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try to get English transcript first
            try:
                transcript = transcript_list.find_transcript(['en']).fetch()
            except:
                # If no English, try to get any manually created transcript
                try:
                    transcript = transcript_list.find_manually_created_transcript().fetch()
                except:
                    # Finally, try auto-generated transcripts
                    transcript = transcript_list.find_generated_transcript(['en']).fetch()
        except:
            # Fallback to simple get_transcript
            transcript = YouTubeTranscriptApi.get_transcript(video_id)

        if not transcript:
            print("No transcript available for this video")
            return None

        # Format transcript as plain text
        formatter = TextFormatter()
        text_formatted = formatter.format_transcript(transcript)

        # Save to file
        output_file = os.path.join(output_dir, f"{video_id}_transcript.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text_formatted)

        print(f"Transcript saved to: {output_file}")
        return output_file

    except Exception as e:
        print(f"Error downloading transcript: {e}")
        print("This video may not have captions/subtitles available")
        return None


def download_audio(video_url, output_dir='downloads'):
    """Download audio from YouTube video as MP3."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        print(f"Downloading audio from: {video_url}")

        # Configure yt-dlp options with updated settings to avoid 403 errors
        # Use mediaconnect client which is more reliable
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
            # Use mediaconnect client which doesn't require PO tokens
            'extractor_args': {'youtube': {'player_client': ['mediaconnect']}},
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
