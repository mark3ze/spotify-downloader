# Spotify Music Downloader

A Python bot that downloads music from YouTube Music using Spotify metadata and converts it to high-quality MP3 files with embedded album art and metadata.

## Features

- Extract metadata from Spotify tracks (title, artist, album, album art)
- Search YouTube Music for the best audio match
- Download and convert audio to 256kbps MP3 using FFmpeg
- Inject Spotify metadata and album art into MP3 files
- Smart filename sanitization and duration matching

## Requirements

- Python 3.7+
- FFmpeg (must be installed on your system)
- Spotify Developer Account

## Installation

1. Clone or download this repository
2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install FFmpeg:
   - **Ubuntu/Debian**: `sudo apt install ffmpeg`
   - **macOS**: `brew install ffmpeg`
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

5. Set up Spotify API credentials:
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Create a new app
   - Copy your Client ID and Client Secret
   - Create a `.env` file from the template:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and add your credentials:
     ```
     SPOTIFY_CLIENT_ID=your_client_id_here
     SPOTIFY_CLIENT_SECRET=your_client_secret_here
     ```

## Usage

Run the downloader:
```bash
python spotify_downloader.py
```

Then enter Spotify track URLs when prompted:
```
Enter a Spotify track URL (or 'quit' to exit):
> https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh
```

Downloaded files will be saved to the `downloads/` directory.

## Dependencies

- **spotipy**: Spotify API wrapper
- **yt-dlp**: YouTube video/audio downloader
- **mutagen**: Audio metadata manipulation
- **python-dotenv**: Environment variable management
- **requests**: HTTP library for downloading album art

## License

This project is for educational purposes only. Please respect copyright laws and the terms of service of Spotify and YouTube.

## Troubleshooting

- **FFmpeg not found**: Make sure FFmpeg is installed and in your system's PATH
- **Spotify API errors**: Check that your credentials are correct and the app has the right permissions
- **No matching video found**: Try with different tracks, some may not be available on YouTube Music
