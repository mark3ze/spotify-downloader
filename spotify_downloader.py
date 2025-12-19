#!/usr/bin/env python3
"""
Spotify Music Downloader
Downloads music from YouTube Music using Spotify metadata
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, TRCK
from mutagen.easyid3 import EasyID3
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SpotifyDownloader:
    def __init__(self):
        """Initialize the downloader with Spotify credentials"""
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            print("Error: Spotify credentials not found in .env file")
            print("Please copy .env.example to .env and add your credentials")
            sys.exit(1)
        
        # Initialize Spotify client
        client_credentials_manager = SpotifyClientCredentials(
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        self.sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        
        # Create downloads directory
        self.downloads_dir = Path("downloads")
        self.downloads_dir.mkdir(exist_ok=True)
    
    def extract_spotify_id(self, url):
        """Extract track ID from Spotify URL"""
        pattern = r'track/([a-zA-Z0-9]{22})'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return None
    
    def get_track_metadata(self, track_id):
        """Get track metadata from Spotify"""
        try:
            track = self.sp.track(track_id)
            
            metadata = {
                'title': track['name'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'album': track['album']['name'],
                'release_date': track['album']['release_date'],
                'track_number': track['track_number'],
                'album_art_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'duration_ms': track['duration_ms']
            }
            
            return metadata
        except Exception as e:
            print(f"Error getting track metadata: {e}")
            return None
    
    def search_youtube_music(self, title, artist, duration_ms):
        """Search for the best audio match on YouTube Music"""
        search_query = f"{title} {artist} official audio"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'format': 'bestaudio/best',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(
                    f"ytsearch:{search_query}",
                    download=False
                )
                
                if not info or 'entries' not in info:
                    return None
                
                # Find the best match based on duration
                entries = info['entries']
                best_match = None
                best_diff = float('inf')
                closest_match = None
                closest_diff = float('inf')
                
                for entry in entries:
                    if not entry or 'duration' not in entry:
                        continue
                    
                    entry_duration = entry['duration'] * 1000  # Convert to ms
                    duration_diff = abs(entry_duration - duration_ms)
                    
                    # Track the closest match for debugging
                    if duration_diff < closest_diff:
                        closest_diff = duration_diff
                        closest_match = entry
                    
                    # Consider it a good match if duration is within 20 seconds
                    if duration_diff < 20000 and duration_diff < best_diff:
                        best_diff = duration_diff
                        best_match = entry
                
                # Debug logging: show closest match even if rejected
                if closest_match:
                    print(f"Closest match found: '{closest_match['title']}' with duration diff: {closest_diff/1000:.1f}s")
                
                # Fallthrough: if no match found within 20 seconds, take first result
                if not best_match and entries:
                    print("No match within 20s tolerance, using first search result as fallback")
                    best_match = entries[0]
                
                return best_match
                
        except Exception as e:
            print(f"Error searching YouTube Music: {e}")
            return None
    
    def download_audio(self, video_url, output_path):
        """Download audio from YouTube and convert to MP3"""
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '256',
            }],
            'outtmpl': str(output_path.with_suffix('')),
            'quiet': False,  # Enable output for debugging
            'no_warnings': False,
            'extractaudio': True,
            'audioformat': 'mp3',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            return True
        except Exception as e:
            print(f"Error downloading audio: {e}")
            return False
    
    def download_album_art(self, url, save_path):
        """Download album art"""
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            print(f"Error downloading album art: {e}")
            return False
    
    def inject_metadata(self, mp3_path, metadata, album_art_path):
        """Inject metadata and album art into MP3 file"""
        try:
            audio = MP3(mp3_path, ID3=ID3)
            
            # Add ID3 tag if it doesn't exist
            try:
                audio.add_tags()
            except:
                pass
            
            # Add metadata
            audio['TIT2'] = TIT2(encoding=3, text=metadata['title'])
            audio['TPE1'] = TPE1(encoding=3, text=metadata['artist'])
            audio['TALB'] = TALB(encoding=3, text=metadata['album'])
            audio['TDRC'] = TDRC(encoding=3, text=metadata['release_date'])
            audio['TRCK'] = TRCK(encoding=3, text=str(metadata['track_number']))
            
            # Add album art
            if album_art_path and os.path.exists(album_art_path):
                with open(album_art_path, 'rb') as albumart:
                    audio['APIC'] = APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,  # 3 means cover image
                        desc='Cover',
                        data=albumart.read()
                    )
            
            audio.save()
            return True
        except Exception as e:
            print(f"Error injecting metadata: {e}")
            return False
    
    def sanitize_filename(self, filename):
        """Sanitize filename for safe file system usage"""
        # Remove invalid characters
        invalid_chars = r'[<>:"/\\|?*]'
        filename = re.sub(invalid_chars, '', filename)
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    def download_track(self, spotify_url):
        """Main method to download a track from Spotify URL"""
        print(f"Processing Spotify URL: {spotify_url}")
        
        # Extract track ID
        track_id = self.extract_spotify_id(spotify_url)
        if not track_id:
            print("Invalid Spotify URL")
            return False
        
        print(f"Track ID: {track_id}")
        
        # Get metadata
        print("Getting track metadata...")
        metadata = self.get_track_metadata(track_id)
        if not metadata:
            print("Failed to get track metadata")
            return False
        
        print(f"Track: {metadata['title']} by {metadata['artist']}")
        
        # Search on YouTube Music
        print("Searching on YouTube Music...")
        video_info = self.search_youtube_music(
            metadata['title'], 
            metadata['artist'], 
            metadata['duration_ms']
        )
        
        if not video_info:
            print("No matching video found on YouTube Music")
            return False
        
        print(f"Found: {video_info['title']}")
        
        # Prepare filenames
        safe_title = self.sanitize_filename(f"{metadata['title']} - {metadata['artist']}")
        temp_audio_path = self.downloads_dir / safe_title
        final_mp3_path = self.downloads_dir / f"{safe_title}.mp3"
        album_art_path = self.downloads_dir / f"{safe_title}_cover.jpg"
        
        # Download album art
        if metadata['album_art_url']:
            print("Downloading album art...")
            self.download_album_art(metadata['album_art_url'], album_art_path)
        
        # Download and convert audio
        print("Downloading and converting audio...")
        success = self.download_audio(video_info['url'], temp_audio_path)
        
        if not success:
            print("Failed to download audio")
            return False
        
        # Find the actual MP3 file (yt-dlp creates it with the base name)
        actual_mp3_path = final_mp3_path
        
        if not actual_mp3_path.exists():
            print(f"MP3 file not found after conversion: {actual_mp3_path}")
            # List all files in downloads directory for debugging
            print("Files in downloads directory:")
            for file in self.downloads_dir.iterdir():
                print(f"  - {file.name}")
            return False
        
        # Inject metadata
        print("Injecting metadata...")
        success = self.inject_metadata(actual_mp3_path, metadata, album_art_path)
        
        if success:
            print(f"Successfully downloaded: {actual_mp3_path}")
            # Clean up temp album art
            if album_art_path.exists():
                album_art_path.unlink()
            return True
        else:
            print("Failed to inject metadata")
            return False


def main():
    """Command-line interface"""
    print("Spotify Music Downloader")
    print("=" * 30)
    
    downloader = SpotifyDownloader()
    
    while True:
        print("\nEnter a Spotify track URL (or 'quit' to exit):")
        url = input("> ").strip()
        
        if url.lower() in ['quit', 'exit', 'q']:
            break
        
        if not url:
            continue
        
        if 'spotify.com/track/' not in url:
            print("Please enter a valid Spotify track URL")
            continue
        
        downloader.download_track(url)
    
    print("\nGoodbye!")


if __name__ == "__main__":
    main()
