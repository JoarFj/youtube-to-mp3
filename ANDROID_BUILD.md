# Building the Android App

This guide shows you how to build the YouTube Downloader app as a native Android APK using Kivy and Buildozer.

## Prerequisites

### On WSL/Linux (for building):

1. **Install system dependencies:**
```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
```

2. **Install Buildozer:**
```bash
pip install buildozer
```

3. **Install Cython (required for Kivy):**
```bash
pip install cython
```

4. **Install Kivy (for testing on desktop):**
```bash
pip install kivy[base]
```

## Testing on Desktop First

Before building for Android, test the app on your desktop:

```bash
python main.py
```

This will launch the Kivy app in a desktop window where you can test the UI and functionality.

## Building the APK

### First-time build:

```bash
buildozer android debug
```

This will:
- Download Android SDK, NDK, and other dependencies (takes a while the first time)
- Compile your Python code
- Package everything into an APK
- The APK will be in `bin/youtubedownloader-1.0.0-arm64-v8a-debug.apk`

### Subsequent builds:

After the first build, subsequent builds are much faster:

```bash
buildozer android debug
```

### Building for release:

For a production-ready APK:

```bash
buildozer android release
```

Note: Release builds need to be signed. See Buildozer documentation for signing instructions.

## Installing on Your Android Device

### Method 1: USB Transfer

1. Connect your phone via USB
2. Copy the APK from `bin/` folder to your phone
3. On your phone, navigate to the APK and tap to install
4. You may need to enable "Install from Unknown Sources" in Settings

### Method 2: Direct Install via ADB

```bash
buildozer android debug deploy run
```

This will build, install, and run the app on a connected Android device.

## App Permissions

The app requests these permissions:
- **INTERNET**: Required to download videos from YouTube
- **WRITE_EXTERNAL_STORAGE**: To save downloaded files
- **READ_EXTERNAL_STORAGE**: To access downloaded files

Files are saved to: `/sdcard/Download/YouTubeDownloader/`

## Troubleshooting

### Build fails with "Command failed"

Try cleaning the build:
```bash
buildozer android clean
buildozer android debug
```

### NDK/SDK download fails

Set a specific NDK version in `buildozer.spec`:
```
android.ndk = 25b
```

### "AAPT not found" error

Update buildozer:
```bash
pip install --upgrade buildozer
```

### App crashes on Android

Check logs:
```bash
buildozer android logcat
```

### yt-dlp fails on Android

Make sure ffmpeg is included. The buildozer.spec includes the `ffmpeg` p4a recipe, which bundles a real ffmpeg CLI binary into the APK (as `lib/<abi>/libffmpegbin.so`) that `youtube_downloader.py` locates at runtime and passes to yt-dlp via `ffmpeg_location`.

## File Structure

```
.
├── main.py                 # Kivy Android app (NEW)
├── youtube_downloader.py   # Core download logic (UNCHANGED)
├── config.py              # Configuration (UNCHANGED)
├── buildozer.spec         # Buildozer configuration (NEW)
├── app.py                 # FastAPI web app (for desktop use)
└── templates/             # Web UI templates (for desktop use)
```

## Development Tips

1. **Test on desktop first** using `python main.py`
2. **Use logcat** to debug Android issues: `buildozer android logcat`
3. **Clean builds** if you change dependencies: `buildozer android clean`
4. **Incremental builds** are much faster than the first build

## Customization

### Change App Icon

1. Create a 512x512 PNG icon
2. Save as `icon.png` in the project root
3. Uncomment this line in `buildozer.spec`:
   ```
   icon.filename = %(source.dir)s/icon.png
   ```

### Change App Name

Edit `buildozer.spec`:
```
title = Your App Name
```

### Change Package Name

Edit `buildozer.spec`:
```
package.name = yourappname
package.domain = com.yourname
```

## Requirements

The app includes these Python packages (automatically installed by Buildozer):
- `kivy` - UI framework
- `yt-dlp` - YouTube download functionality
- `certifi` - SSL certificates for HTTPS
- `ffmpeg` - Real ffmpeg CLI binary, bundled for audio/video merging and conversion on Android

## Known Limitations

1. **First download may be slow** as yt-dlp initializes
2. **Large video downloads** may take time depending on connection
3. **Storage location** is fixed to `/sdcard/Download/YouTubeDownloader/`
4. **Background downloads** may be interrupted if the app is closed
5. **Video seeking issues**: Some longer videos may not support rewinding/fast-forwarding on the default Android video player. This is due to MP4 moov atom positioning. Workarounds:
   - Use a different media player app (e.g., VLC for Android, MX Player) which handle various MP4 formats better
   - Try different video quality settings, which may result in different format structures
   - Audio files (MP3/M4A) do not have this issue

## Next Steps

After building:
1. Test the APK on your Android device
2. Check that files are saved correctly
3. Test different video qualities
4. Verify transcript downloads work

## Additional Resources

- [Buildozer Documentation](https://buildozer.readthedocs.io/)
- [Kivy Documentation](https://kivy.org/doc/stable/)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)
