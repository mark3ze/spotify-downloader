#!/usr/bin/env python3
"""
Spotify Downloader Telegram Bot
Send Spotify URLs and get MP3 files
"""

import os
import asyncio
import logging
import sys
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction
from dotenv import load_dotenv
from spotify_downloader import SpotifyDownloader

# Load environment variables
load_dotenv()

# Configure logging (Modified for Cloud Deployment to output to stdout)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.downloader = SpotifyDownloader()
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        # Check environment variable if .env is missing (common in cloud)
        if not self.telegram_token:
            self.telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        
        if not self.telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file or environment variables")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message"""
        welcome_message = """
🎵 *Spotify Music Downloader Bot*

Send me a Spotify URL and I'll download it for you!

*Supported URLs:*
🎧 Single Tracks
💿 Full Albums
📝 Playlists

*Commands:*
/start - Show this message
/help - Show help
/stats - Show your download statistics

Just paste any Spotify link to get started! 🚀
        """
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send help message"""
        help_text = """
*How to use:*

1️⃣ Copy a Spotify link (track/album/playlist)
2️⃣ Paste it here
3️⃣ Wait for your music! 🎵

*Examples:*
• `https://open.spotify.com/track/...`
• `https://open.spotify.com/album/...`
• `https://open.spotify.com/playlist/...`

*Tips:*
• For playlists/albums, download may take a while
• You'll get each track as a separate file
• All files include metadata and album art
• Maximum 50 tracks per playlist/album

*Note:* This bot is for personal use only. Please respect copyright laws.
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user statistics"""
        user_data = context.user_data
        
        downloads = user_data.get('total_downloads', 0)
        failed = user_data.get('failed_downloads', 0)
        
        stats_text = f"""
📊 *Your Statistics*

✅ Successful downloads: {downloads}
❌ Failed downloads: {failed}
📈 Success rate: {(downloads/(downloads+failed)*100) if downloads+failed > 0 else 0:.1f}%
        """
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming Spotify URLs"""
        if not update.message or not update.message.text:
            return

        message_text = update.message.text.strip()
        
        # Check if it's a Spotify URL
        if 'spotify.com/' not in message_text:
            await update.message.reply_text(
                "❌ Please send a valid Spotify URL (track, album, or playlist)"
            )
            return
        
        # Determine content type
        content_type, content_id = self.downloader.extract_spotify_info(message_text)
        
        if not content_type:
            await update.message.reply_text(
                "❌ Invalid Spotify URL. Please send a track, album, or playlist link."
            )
            return
        
        # Ask for confirmation if it's an album or playlist
        if content_type in ['album', 'playlist']:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Yes, download all", callback_data=f"confirm_{content_type}_{content_id}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Get track count
            if content_type == 'album':
                tracks = self.downloader.get_album_tracks(content_id)
                count = len(tracks) if tracks else 0
                type_emoji = "💿"
            else:
                tracks = self.downloader.get_playlist_tracks(content_id)
                count = len(tracks) if tracks else 0
                type_emoji = "📝"
            
            if count > 50:
                await update.message.reply_text(
                    f"❌ This {content_type} has {count} tracks. Maximum allowed is 50.\n"
                    f"Please choose a smaller {content_type}."
                )
                return
            
            await update.message.reply_text(
                f"{type_emoji} This {content_type} contains *{count} tracks*.\n\n"
                f"Download all tracks?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Store URL in context for later
            context.user_data['pending_url'] = message_text
        else:
            # Download single track immediately
            await self.download_and_send(update, context, message_text, 'track')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("❌ Download cancelled.")
            return
        
        if query.data.startswith("confirm_"):
            parts = query.data.split("_")
            content_type = parts[1]
            
            spotify_url = context.user_data.get('pending_url')
            if not spotify_url:
                await query.edit_message_text("❌ Error: URL not found. Please try again.")
                return
            
            await query.edit_message_text(f"⏳ Starting download of {content_type}...")
            await self.download_and_send(update, context, spotify_url, content_type)
    
    async def download_and_send(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                spotify_url: str, content_type: str):
        """Download and send music files"""
        chat_id = update.effective_chat.id
        
        # Send typing action
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
        
        try:
            if content_type == 'track':
                await self.download_single_track(update, context, spotify_url)
            elif content_type == 'album':
                await self.download_album(update, context, spotify_url)
            elif content_type == 'playlist':
                await self.download_playlist(update, context, spotify_url)
        except Exception as e:
            logger.error(f"Error downloading: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Error during download: {str(e)}"
            )
    
    async def download_single_track(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   spotify_url: str):
        """Download and send a single track"""
        chat_id = update.effective_chat.id
        
        # Get track info
        content_type, content_id = self.downloader.extract_spotify_info(spotify_url)
        metadata = self.downloader.get_track_metadata(content_id)
        
        if not metadata:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Failed to get track information."
            )
            return
        
        status_msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"⏳ Downloading: *{metadata['title']}* by {metadata['artist']}",
            parse_mode='Markdown'
        )
        
        # Download
        success = self.downloader.download_single_track(metadata)
        
        if not success:
            await status_msg.edit_text("❌ Failed to download track (Audio not found or download error).")
            context.user_data['failed_downloads'] = context.user_data.get('failed_downloads', 0) + 1
            return
        
        # Find the downloaded file
        safe_title = self.downloader.sanitize_filename(f"{metadata['title']} - {metadata['artist']}")
        mp3_path = self.downloader.downloads_dir / f"{safe_title}.mp3"
        
        if not mp3_path.exists():
            await status_msg.edit_text("❌ Error: Downloaded file not found on disk.")
            return
        
        # Send the file
        await status_msg.edit_text("📤 Uploading...")
        
        try:
            with open(mp3_path, 'rb') as audio:
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=audio,
                    title=metadata['title'],
                    performer=metadata['artist'],
                    caption=f"🎵 {metadata['title']}\n👤 {metadata['artist']}\n💿 {metadata['album']}"
                )
            
            await status_msg.delete()
            
            # Update stats
            context.user_data['total_downloads'] = context.user_data.get('total_downloads', 0) + 1
            
            # Clean up file
            try:
                mp3_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete file {mp3_path}: {e}")
            
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            await status_msg.edit_text(f"❌ Error sending file: {str(e)}")
            # Clean up on error
            if mp3_path.exists():
                try: mp3_path.unlink() 
                except: pass
    
    async def download_album(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                            spotify_url: str):
        """Download and send all tracks from an album"""
        chat_id = update.effective_chat.id
        
        # Get album tracks
        content_type, content_id = self.downloader.extract_spotify_info(spotify_url)
        tracks = self.downloader.get_album_tracks(content_id)
        
        if not tracks:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Failed to get album tracks."
            )
            return
        
        status_msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"📀 Downloading album: *{tracks[0]['album']}*\n"
                 f"Total tracks: {len(tracks)}\n\n"
                 f"Progress: 0/{len(tracks)}",
            parse_mode='Markdown'
        )
        
        successful = 0
        failed = 0
        
        for idx, metadata in enumerate(tracks, 1):
            # Update progress
            try:
                await status_msg.edit_text(
                    f"📀 Downloading album: *{tracks[0]['album']}*\n"
                    f"Total tracks: {len(tracks)}\n\n"
                    f"Progress: {idx}/{len(tracks)}\n"
                    f"Current: {metadata['title'][:40]}...",
                    parse_mode='Markdown'
                )
            except:
                pass 
            
            # Download
            success = self.downloader.download_single_track(metadata)
            
            if success:
                safe_title = self.downloader.sanitize_filename(f"{metadata['title']} - {metadata['artist']}")
                mp3_path = self.downloader.downloads_dir / f"{safe_title}.mp3"
                
                if mp3_path.exists():
                    try:
                        with open(mp3_path, 'rb') as audio:
                            await context.bot.send_audio(
                                chat_id=chat_id,
                                audio=audio,
                                title=metadata['title'],
                                performer=metadata['artist'],
                                caption=f"🎵 {metadata['title']}\n💿 {metadata['album']}"
                            )
                        mp3_path.unlink()
                        successful += 1
                    except Exception as e:
                        logger.error(f"Error sending file: {e}")
                        failed += 1
                else:
                    failed += 1
            else:
                failed += 1
            
            await asyncio.sleep(2)  # Rate limiting
        
        try:
            await status_msg.edit_text(
                f"✅ *Album Download Complete!*\n\n"
                f"📀 Album: {tracks[0]['album']}\n"
                f"✅ Successful: {successful}/{len(tracks)}\n"
                f"❌ Failed: {failed}/{len(tracks)}",
                parse_mode='Markdown'
            )
        except:
            await context.bot.send_message(chat_id=chat_id, text="✅ Album Download Complete!")
        
        context.user_data['total_downloads'] = context.user_data.get('total_downloads', 0) + successful
        context.user_data['failed_downloads'] = context.user_data.get('failed_downloads', 0) + failed
    
    async def download_playlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               spotify_url: str):
        """Download and send all tracks from a playlist"""
        chat_id = update.effective_chat.id
        
        content_type, content_id = self.downloader.extract_spotify_info(spotify_url)
        tracks = self.downloader.get_playlist_tracks(content_id)
        
        if not tracks:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Failed to get playlist tracks."
            )
            return
        
        try:
            playlist = self.downloader.sp.playlist(content_id)
            playlist_name = playlist['name']
        except:
            playlist_name = "Spotify Playlist"
        
        status_msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"📝 Downloading playlist: *{playlist_name}*\n"
                 f"Total tracks: {len(tracks)}\n\n"
                 f"Progress: 0/{len(tracks)}",
            parse_mode='Markdown'
        )
        
        successful = 0
        failed = 0
        
        for idx, metadata in enumerate(tracks, 1):
            try:
                await status_msg.edit_text(
                    f"📝 Downloading playlist: *{playlist_name}*\n"
                    f"Total tracks: {len(tracks)}\n\n"
                    f"Progress: {idx}/{len(tracks)}\n"
                    f"Current: {metadata['title'][:40]}...",
                    parse_mode='Markdown'
                )
            except:
                pass
            
            success = self.downloader.download_single_track(metadata)
            
            if success:
                safe_title = self.downloader.sanitize_filename(f"{metadata['title']} - {metadata['artist']}")
                mp3_path = self.downloader.downloads_dir / f"{safe_title}.mp3"
                
                if mp3_path.exists():
                    try:
                        with open(mp3_path, 'rb') as audio:
                            await context.bot.send_audio(
                                chat_id=chat_id,
                                audio=audio,
                                title=metadata['title'],
                                performer=metadata['artist'],
                                caption=f"🎵 {metadata['title']}\n💿 {metadata['album']}"
                            )
                        mp3_path.unlink()
                        successful += 1
                    except Exception as e:
                        logger.error(f"Error sending file: {e}")
                        failed += 1
                else:
                    failed += 1
            else:
                failed += 1
            
            await asyncio.sleep(2)
        
        try:
            await status_msg.edit_text(
                f"✅ *Playlist Download Complete!*\n\n"
                f"📝 Playlist: {playlist_name}\n"
                f"✅ Successful: {successful}/{len(tracks)}\n"
                f"❌ Failed: {failed}/{len(tracks)}",
                parse_mode='Markdown'
            )
        except:
            await context.bot.send_message(chat_id=chat_id, text="✅ Playlist Download Complete!")
        
        context.user_data['total_downloads'] = context.user_data.get('total_downloads', 0) + successful
        context.user_data['failed_downloads'] = context.user_data.get('failed_downloads', 0) + failed
    
    def run(self):
        """Run the bot"""
        # Create application
        application = Application.builder().token(self.telegram_token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CallbackQueryHandler(self.button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Start the bot
        logger.info("Bot started! Polling for updates...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main function"""
    try:
        bot = TelegramBot()
        bot.run()
    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease check your Environment Variables")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")


if __name__ == "__main__":
    main()