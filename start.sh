#!/bin/bash

# Start a dummy HTTP server in the background
# This listens on the port Render assigns ($PORT) so Render knows the app is "healthy"
PORT="${PORT:-10000}"
python3 -m http.server "$PORT" &

# Start the actual Telegram bot
python3 telegram_bot.py