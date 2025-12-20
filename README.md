# Spotify Music Downloader & Telegram Bot

A Python bot that downloads music from YouTube Music using Spotify metadata and converts it to high-quality MP3 files with embedded album art and metadata.

## Deployment on Render.com

This bot is configured to run on Render.com using Docker (required for FFmpeg support).

### Prerequisites
1. A [GitHub](https://github.com/) account with this code pushed to a repository.
2. A [Render](https://render.com/) account.
3. Your API Tokens (Spotify Client ID/Secret and Telegram Bot Token).

### Steps to Deploy

1. **Push your code to GitHub**
   Ensure `Dockerfile`, `start.sh`, `telegram_bot.py`, `spotify_downloader.py`, and `requirements.txt` are in your repo.

2. **Create a new Web Service on Render**
   - Go to your Render Dashboard.
   - Click **New +** -> **Web Service**.
   - Connect your GitHub repository.

3. **Configure the Service**
   - **Name:** `spotify-bot` (or whatever you like)
   - **Runtime:** Select **Docker** (This is important! Do not select Python).
   - **Region:** Choose one close to you (e.g., Frankfurt or Oregon).
   - **Instance Type:** "Free" (note: Free tier spins down after inactivity) or "Starter" ($7/mo, recommended for 24/7 uptime).

4. **Add Environment Variables**
   Scroll down to the "Environment Variables" section and add the following keys:
   
   | Key | Value |
   | --- | --- |
   | `SPOTIFY_CLIENT_ID` | Your Spotify Client ID |
   | `SPOTIFY_CLIENT_SECRET` | Your Spotify Client Secret |
   | `TELEGRAM_BOT_TOKEN` | Your Telegram Bot Token |

5. **Deploy**
   - Click **Create Web Service**.
   - Render will start building the Docker image. This might take 2-3 minutes as it installs FFmpeg.
   - Once built, you should see "Bot started!" in the logs.

### Important Note on Free Tier
Render's **Free Tier** puts web services to sleep after 15 minutes of inactivity. Since a Telegram bot needs to be awake to receive messages:
- **Recommended:** Use the **Starter** plan ($7/mo) which never sleeps.
- **Free Tier Workaround:** You can use a service like UptimeRobot to ping your Render URL (e.g., `https://your-bot.onrender.com`) every 5 minutes to keep it awake, but this is not officially supported by Render.

## Features

- Extract metadata from Spotify tracks (title, artist, album, album art)
- Search YouTube Music for the best audio match
- Download and convert audio to 256kbps MP3 using FFmpeg
- Inject Spotify metadata and album art into MP3 files
- **Telegram Bot Integration**: Use the bot to download music directly from Telegram

## Local Installation

1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Install FFmpeg on your system
4. Create `.env` with your API tokens
5. Run `python telegram_bot.py`