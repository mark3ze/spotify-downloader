# Spotify Music Downloader

A Python bot that downloads music from YouTube Music using Spotify metadata and converts it to high-quality MP3 files with embedded album art and metadata.

## Features

- Extract metadata from Spotify tracks (title, artist, album, album art)
- Search YouTube Music for the best audio match
- Download and convert audio to 256kbps MP3 using FFmpeg
- Inject Spotify metadata and album art into MP3 files
- Smart filename sanitization and duration matching
- **Telegram Bot Integration**: Use the bot to download music directly from Telegram

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

6. (Optional) Set up Telegram Bot:
   - Create a Telegram bot by messaging [@BotFather](https://t.me/BotFather) on Telegram
   - Use `/newbot` command to create your bot
   - Copy the bot token
   - Add it to your `.env` file:
     ```
     TELEGRAM_BOT_TOKEN=your_bot_token_here
     ```

## Usage

### Command Line Interface

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

### Telegram Bot

Start the Telegram bot:
```bash
python telegram_bot.py
```

The bot supports:
- **Single tracks**: Send a Spotify track URL to download immediately
- **Albums**: Send an album URL, confirm to download all tracks (max 50)
- **Playlists**: Send a playlist URL, confirm to download all tracks (max 50)

**Bot Commands:**
- `/start` - Show welcome message
- `/help` - Display help and usage instructions
- `/stats` - View your download statistics

**Example usage in Telegram:**
1. Paste any Spotify link (track/album/playlist)
2. For albums/playlists, confirm you want to download all tracks
3. Wait for the download to complete
4. Receive MP3 files with full metadata and album art

## Dependencies

- **spotipy**: Spotify API wrapper
- **yt-dlp**: YouTube video/audio downloader
- **mutagen**: Audio metadata manipulation
- **python-dotenv**: Environment variable management
- **requests**: HTTP library for downloading album art
- **python-telegram-bot**: Telegram Bot API wrapper (for bot functionality)

## License

This project is for educational purposes only. Please respect copyright laws and the terms of service of Spotify and YouTube.

## Deployment

### Running 24/7 on Cloud Servers

To run the Telegram bot continuously without keeping your laptop on:

#### Option 1: VPS (Recommended)
- **DigitalOcean**: $6/month droplet
- **Linode**: $5/month shared CPU  
- **Vultr**: $3.5/month basic instance

Setup commands:
```bash
# On your VPS
sudo apt update && sudo apt install python3-pip git ffmpeg
git clone https://github.com/mark3ze/spotify-downloader
cd spotify-downloader
pip3 install -r requirements.txt
# Create .env with your tokens
python3 telegram_bot.py
```

Use PM2 for process management:
```bash
npm install -g pm2
pm2 start python3 --name telegram-bot -- telegram_bot.py
pm2 startup  # Auto-start on boot
```

#### Option 2: PaaS Platforms
- **Render**: Free tier with background workers
- **Railway**: $5/month after free credits
- **Fly.io**: Free tier for small apps
- **PythonAnywhere**: Free tier for basic bots

#### Option 3: Home Server
- **Raspberry Pi**: ~$50 one-time, ~$2-3/month electricity
- **Old laptop**: Repurpose existing hardware

## Troubleshooting

### Command Line Issues
- **FFmpeg not found**: Make sure FFmpeg is installed and in your system's PATH
- **Spotify API errors**: Check that your credentials are correct and the app has the right permissions
- **No matching video found**: Try with different tracks, some may not be available on YouTube Music

### Telegram Bot Issues
- **Bot token not found**: Ensure `TELEGRAM_BOT_TOKEN` is set in your `.env` file
- **Bot doesn't respond**: Check that the bot token is valid and the bot is running
- **Large downloads fail**: Albums/playlists are limited to 50 tracks to prevent timeouts
- **File upload errors**: Telegram has file size limits (50MB for regular users)
