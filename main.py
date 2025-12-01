"""
Kivy Android app for YouTube Transcript & Media Downloader
"""

import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform
import threading

import youtube_downloader
import config


class DownloaderApp(App):
    def build(self):
        self.title = 'YouTube Downloader'

        # Main layout
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Title
        title_label = Label(
            text='YouTube Downloader',
            size_hint=(1, 0.1),
            font_size='24sp',
            bold=True
        )
        main_layout.add_widget(title_label)

        # URL Input
        url_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.15), spacing=5)
        url_layout.add_widget(Label(text='YouTube URL:', size_hint=(1, 0.4), font_size='16sp'))
        self.url_input = TextInput(
            hint_text='https://www.youtube.com/watch?v=...',
            multiline=False,
            size_hint=(1, 0.6)
        )
        url_layout.add_widget(self.url_input)
        main_layout.add_widget(url_layout)

        # Download type checkboxes
        checkbox_layout = GridLayout(cols=2, size_hint=(1, 0.15), spacing=10)

        checkbox_layout.add_widget(Label(text='Transcript', font_size='14sp'))
        self.transcript_checkbox = CheckBox(active=True)
        checkbox_layout.add_widget(self.transcript_checkbox)

        checkbox_layout.add_widget(Label(text='Audio (MP3)', font_size='14sp'))
        self.audio_checkbox = CheckBox(active=True)
        checkbox_layout.add_widget(self.audio_checkbox)

        checkbox_layout.add_widget(Label(text='Video (MP4)', font_size='14sp'))
        self.video_checkbox = CheckBox(active=False)
        checkbox_layout.add_widget(self.video_checkbox)

        main_layout.add_widget(checkbox_layout)

        # Quality settings
        quality_layout = GridLayout(cols=2, size_hint=(1, 0.15), spacing=10)

        quality_layout.add_widget(Label(text='Audio Quality:', font_size='14sp'))
        self.audio_quality_spinner = Spinner(
            text='192 kbps',
            values=['128 kbps', '192 kbps', '256 kbps', '320 kbps'],
            size_hint=(1, 1)
        )
        quality_layout.add_widget(self.audio_quality_spinner)

        quality_layout.add_widget(Label(text='Video Quality:', font_size='14sp'))
        self.video_quality_spinner = Spinner(
            text='720p',
            values=['360p', '480p', '720p', '1080p'],
            size_hint=(1, 1)
        )
        quality_layout.add_widget(self.video_quality_spinner)

        main_layout.add_widget(quality_layout)

        # Buttons layout
        buttons_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.1), spacing=10)

        self.download_button = Button(
            text='Download',
            font_size='18sp',
            background_color=(0.2, 0.6, 1, 1)
        )
        self.download_button.bind(on_press=self.start_download)
        buttons_layout.add_widget(self.download_button)

        self.copy_logs_button = Button(
            text='Copy Logs',
            font_size='18sp',
            background_color=(0.2, 0.8, 0.2, 1)
        )
        self.copy_logs_button.bind(on_press=self.copy_logs)
        buttons_layout.add_widget(self.copy_logs_button)

        main_layout.add_widget(buttons_layout)

        # Status/Output display
        output_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.35), spacing=5)
        output_layout.add_widget(Label(text='Status:', size_hint=(1, 0.2), font_size='16sp'))

        # Scrollable output
        scroll = ScrollView(size_hint=(1, 0.8))
        self.output_label = Label(
            text='Ready to download...',
            size_hint_y=None,
            font_size='12sp',
            halign='left',
            valign='top'
        )
        self.output_label.bind(texture_size=self.output_label.setter('size'))
        scroll.add_widget(self.output_label)
        output_layout.add_widget(scroll)

        main_layout.add_widget(output_layout)

        # Storage path info on Android
        if platform == 'android':
            from android.storage import primary_external_storage_path
            storage_path = primary_external_storage_path()
            self.downloads_dir = os.path.join(storage_path, 'Download', 'YouTubeDownloader')
            self.transcripts_dir = os.path.join(storage_path, 'Download', 'YouTubeDownloader', 'transcripts')

            # Update status
            self.update_output(f'Files will be saved to:\n{self.downloads_dir}')
        else:
            # Use default directories for desktop testing
            self.downloads_dir = config.DOWNLOADS_DIR
            self.transcripts_dir = config.TRANSCRIPTS_DIR

        # Create directories
        os.makedirs(self.downloads_dir, exist_ok=True)
        os.makedirs(self.transcripts_dir, exist_ok=True)

        return main_layout

    def update_output(self, text, append=True):
        """Update the output label text."""
        def update(dt):
            if append:
                current = self.output_label.text
                self.output_label.text = f"{current}\n{text}"
            else:
                self.output_label.text = text

        Clock.schedule_once(update, 0)

    def copy_logs(self, instance):
        """Copy the logs to clipboard."""
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(self.output_label.text)
            # Show brief confirmation
            original_text = self.copy_logs_button.text
            self.copy_logs_button.text = 'Copied!'
            def reset_text(dt):
                self.copy_logs_button.text = original_text
            Clock.schedule_once(reset_text, 1.5)
        except Exception as e:
            self.update_output(f'Error copying to clipboard: {str(e)}')

    def start_download(self, instance):
        """Start the download process in a background thread."""
        url = self.url_input.text.strip()

        if not url:
            self.update_output('Error: Please enter a YouTube URL', append=False)
            return

        # Validate URL
        video_id = youtube_downloader.extract_video_id(url)
        if not video_id:
            self.update_output('Error: Invalid YouTube URL', append=False)
            return

        # Check if at least one option is selected
        if not (self.transcript_checkbox.active or self.audio_checkbox.active or self.video_checkbox.active):
            self.update_output('Error: Please select at least one download option', append=False)
            return

        # Disable button during download
        self.download_button.disabled = True
        self.download_button.text = 'Downloading...'

        # Clear output
        self.update_output(f'Starting download for: {video_id}\n', append=False)

        # Run download in background thread
        threading.Thread(target=self.download_process, args=(url,), daemon=True).start()

    def download_process(self, url):
        """Background download process."""
        try:
            # Set logger callback so we can see debug output from youtube_downloader
            youtube_downloader.set_logger_callback(self.update_output)

            # Debug: Show platform and storage info
            self.update_output(f'Platform: {platform}')
            self.update_output(f'Download dir: {self.downloads_dir}')

            download_types = []
            if self.transcript_checkbox.active:
                download_types.append('transcript')
            if self.audio_checkbox.active:
                download_types.append('audio')
            if self.video_checkbox.active:
                download_types.append('video')

            # Extract quality values (remove unit text)
            audio_quality = self.audio_quality_spinner.text.split()[0]  # "192 kbps" -> "192"
            video_quality = self.video_quality_spinner.text.replace('p', '')  # "720p" -> "720"

            # Download transcript
            if 'transcript' in download_types:
                self.update_output('Downloading transcript...')
                try:
                    transcript_file = youtube_downloader.download_transcript(url, output_dir=self.transcripts_dir)
                    if transcript_file:
                        self.update_output(f'✓ Transcript saved: {os.path.basename(transcript_file)}')
                    else:
                        self.update_output('✗ Transcript download failed (video may not have captions)')
                except Exception as e:
                    self.update_output(f'✗ Transcript error: {str(e)}')

            # Download audio
            if 'audio' in download_types:
                self.update_output(f'Downloading audio ({audio_quality} kbps)...')
                try:
                    audio_file = youtube_downloader.download_audio(
                        url,
                        output_dir=self.downloads_dir,
                        audio_quality=audio_quality
                    )
                    if audio_file:
                        self.update_output(f'✓ Audio saved: {os.path.basename(audio_file)}')
                    else:
                        self.update_output('✗ Audio download failed')
                except Exception as e:
                    self.update_output(f'✗ Audio error: {str(e)}')

            # Download video
            if 'video' in download_types:
                self.update_output(f'Downloading video ({video_quality}p)...')
                try:
                    video_file = youtube_downloader.download_video(
                        url,
                        output_dir=self.downloads_dir,
                        video_quality=video_quality
                    )
                    if video_file:
                        self.update_output(f'✓ Video saved: {os.path.basename(video_file)}')
                    else:
                        self.update_output('✗ Video download failed')
                except Exception as e:
                    self.update_output(f'✗ Video error: {str(e)}')

            self.update_output('\nDownload complete!')

        except Exception as e:
            self.update_output(f'Error: {str(e)}')

        finally:
            # Re-enable button
            def reset_button(dt):
                self.download_button.disabled = False
                self.download_button.text = 'Download'
            Clock.schedule_once(reset_button, 0)


if __name__ == '__main__':
    DownloaderApp().run()
