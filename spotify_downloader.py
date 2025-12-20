#!/usr/bin/env python3
"""
Spotify Music Downloader
Downloads music from YouTube Music using Spotify metadata
Supports: Tracks, Albums, and Playlists
"""

import os
import re
import sys
import time
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
from tqdm import tqdm

# Load environment variables
load_dotenv()

class SpotifyDownloader:
    def __init__(self):
        """Initialize the downloader with Spotify credentials"""
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        
        # Also check os.environ directly for Docker environment
        if not self.client_id:
            self.client_id = os.environ.get('SPOTIFY_CLIENT_ID')
        if not self.client_secret:
            self.client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            if __name__ == "__main__":
                print("Error: Spotify credentials not found in .env file or environment variables")
                sys.exit(1)
        
        # Initialize Spotify client
        if self.client_id and self.client_secret:
            client_credentials_manager = SpotifyClientCredentials(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            self.sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        
        # Create downloads directory
        self.downloads_dir = Path("downloads")
        self.downloads_dir.mkdir(exist_ok=True)

        # --- COOKIE SETUP (FIX FOR RENDER) ---
        self.cookie_file = None
        cookie_content = os.getenv('YOUTUBE_COOKIES')
        
        # If cookies are provided via Env Var (Best for Render)
        if cookie_content:
            try:
                # Write cookies to a local file
                with open('cookies.txt', 'w') as f:
                    f.write(cookie_content)
                self.cookie_file = 'cookies.txt'
                print("✅ YouTube Cookies loaded from Environment Variable.")
            except Exception as e:
                print(f"⚠️ Error writing cookie file: {e}")
        # If local file exists (Best for local testing)
        elif os.path.exists('cookies.txt'):
             self.cookie_file = 'cookies.txt'
             print("✅ YouTube Cookies loaded from local file.")

    def extract_spotify_info(self, url):
        """Extract type and ID from Spotify URL"""
        track_pattern = r'track/([a-zA-Z0-9]{22})'
        album_pattern = r'album/([a-zA-Z0-9]{22})'
        playlist_pattern = r'playlist/([a-zA-Z0-9]{22})'
        
        track_match = re.search(track_pattern, url)
        album_match = re.search(album_pattern, url)
        playlist_match = re.search(playlist_pattern, url)
        
        if track_match:
            return ('track', track_match.group(1))
        elif album_match:
            return ('album', album_match.group(1))
        elif playlist_match:
            return ('playlist', playlist_match.group(1))
        
        return (None, None)
    
    def get_track_metadata(self, track_id):
        """Get track metadata from Spotify"""
        try:
            track = self.sp.track(track_id)
            
            metadata = {
                'id': track['id'],
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
    
    def get_album_tracks(self, album_id):
        """Get all tracks from an album"""
        try:
            album = self.sp.album(album_id)
            tracks = []
            
            print(f"\n📀 Album: {album['name']}")
            print(f"👤 Artist: {', '.join([artist['name'] for artist in album['artists']])}")
            print(f"📊 Total tracks: {album['total_tracks']}\n")
            
            for track in album['tracks']['items']:
                metadata = {
                    'id': track['id'],
                    'title': track['name'],
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'album': album['name'],
                    'release_date': album['release_date'],
                    'track_number': track['track_number'],
                    'album_art_url': album['images'][0]['url'] if album['images'] else None,
                    'duration_ms': track['duration_ms']
                }
                tracks.append(metadata)
            
            return tracks
        except Exception as e:
            print(f"Error getting album tracks: {e}")
            return None
    
    def get_playlist_tracks(self, playlist_id):
        """Get all tracks from a playlist"""
        try:
            playlist = self.sp.playlist(playlist_id)
            tracks = []
            
            print(f"\n🎵 Playlist: {playlist['name']}")
            print(f"👤 Owner: {playlist['owner']['display_name']}")
            print(f"📊 Total tracks: {playlist['tracks']['total']}\n")
            
            results = playlist['tracks']
            while results:
                for item in results['items']:
                    if item['track'] is None:
                        continue
                    
                    track = item['track']
                    metadata = {
                        'id': track['id'],
                        'title': track['name'],
                        'artist': ', '.join([artist['name'] for artist in track['artists']]),
                        'album': track['album']['name'],
                        'release_date': track['album']['release_date'],
                        'track_number': track['track_number'],
                        'album_art_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                        'duration_ms': track['duration_ms']
                    }
                    tracks.append(metadata)
                
                if results['next']:
                    results = self.sp.next(results)
                else:
                    results = None
            
            return tracks
        except Exception as e:
            print(f"Error getting playlist tracks: {e}")
            return None
    
    def search_youtube_music(self, title, artist, duration_ms):
        """Search for the best audio match on YouTube Music"""
        search_query = f"{title} {artist} audio"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'format': 'bestaudio/best',
            'default_search': 'ytsearch5',
        }

        # Inject cookies if available
        if self.cookie_file:
            ydl_opts['cookiefile'] = self.cookie_file
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(
                    f"ytsearch5:{search_query}",
                    download=False
                )
                
                if not info or 'entries' not in info:
                    return None
                
                entries = info['entries']
                best_match = None
                best_diff = float('inf')
                
                for entry in entries:
                    if not entry or 'duration' not in entry:
                        continue
                    
                    entry_duration = entry['duration'] * 1000
                    duration_diff = abs(entry_duration - duration_ms)
                    
                    if duration_diff < 10000 and duration_diff < best_diff:
                        best_diff = duration_diff
                        best_match = entry
                
                return best_match
                
        except Exception as e:
            print(f"Search error: {e}")
            return None
    
    def download_audio(self, video_url, output_path):
        """Download audio from YouTube and convert to MP3 with progress bar"""
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '256',
            }],
            'outtmpl': str(output_path),
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'prefer_insecure': False,
            'keepvideo': False,
            'progress_hooks': [self._download_progress_hook],
        }

        # Inject cookies if available
        if self.cookie_file:
            ydl_opts['cookiefile'] = self.cookie_file
        
        try:
            self.download_pbar = None
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            if self.download_pbar:
                self.download_pbar.close()
            return True
        except Exception as e:
            if self.download_pbar:
                self.download_pbar.close()
            print(f"Download error: {e}")
            return False
    
    def _download_progress_hook(self, d):
        """Progress hook for yt-dlp downloads"""
        if d['status'] == 'downloading':
            if not hasattr(self, 'download_pbar') or self.download_pbar is None:
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                self.download_pbar = tqdm(
                    total=total,
                    unit='B',
                    unit_scale=True,
                    desc='  Downloading',
                    bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
                )
            
            downloaded = d.get('downloaded_bytes', 0)
            if self.download_pbar.total != downloaded:
                self.download_pbar.update(downloaded - self.download_pbar.n)
        
        elif d['status'] == 'finished':
            if self.download_pbar:
                self.download_pbar.close()
                self.download_pbar = None
    
    def download_album_art(self, url, save_path):
        """Download album art"""
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            return False
    
    def inject_metadata(self, mp3_path, metadata, album_art_path):
        """Inject metadata and album art into MP3 file"""
        try:
            audio = MP3(mp3_path, ID3=ID3)
            
            try:
                audio.add_tags()
            except:
                pass
            
            audio['TIT2'] = TIT2(encoding=3, text=metadata['title'])
            audio['TPE1'] = TPE1(encoding=3, text=metadata['artist'])
            audio['TALB'] = TALB(encoding=3, text=metadata['album'])
            audio['TDRC'] = TDRC(encoding=3, text=metadata['release_date'])
            audio['TRCK'] = TRCK(encoding=3, text=str(metadata['track_number']))
            
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
            return False
    
    def sanitize_filename(self, filename):
        """Sanitize filename for safe file system usage"""
        invalid_chars = r'[<>:"/\\|?*]'
        filename = re.sub(invalid_chars, '', filename)
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    def download_single_track(self, metadata, progress_bar=None):
        """Download a single track"""
        try:
            if progress_bar:
                progress_bar.set_description(f"🎵 {metadata['title'][:40]}")
            
            # Search on YouTube Music
            video_info = self.search_youtube_music(
                metadata['title'], 
                metadata['artist'], 
                metadata['duration_ms']
            )
            
            if not video_info:
                if progress_bar:
                    progress_bar.write(f"  ❌ Not found: {metadata['title']}")
                return False
            
            # Prepare filenames
            safe_title = self.sanitize_filename(f"{metadata['title']} - {metadata['artist']}")
            output_template = self.downloads_dir / safe_title
            final_mp3_path = self.downloads_dir / f"{safe_title}.mp3"
            album_art_path = self.downloads_dir / f"{safe_title}_cover.jpg"
            
            if final_mp3_path.exists():
                if progress_bar:
                    progress_bar.write(f"  ⏭️  Skipped: {metadata['title']} (already exists)")
                return True
            
            if metadata['album_art_url']:
                self.download_album_art(metadata['album_art_url'], album_art_path)
            
            # Download and convert audio
            success = self.download_audio(video_info['webpage_url'], output_template)
            
            if not success or not final_mp3_path.exists():
                if progress_bar:
                    progress_bar.write(f"  ❌ Failed: {metadata['title']}")
                return False
            
            # Inject metadata
            self.inject_metadata(final_mp3_path, metadata, album_art_path)
            
            if album_art_path.exists():
                album_art_path.unlink()
            
            if progress_bar:
                progress_bar.write(f"  ✅ Downloaded: {metadata['title']}")
            
            return True
            
        except Exception as e:
            if progress_bar:
                progress_bar.write(f"  ❌ Error: {metadata['title']} - {str(e)}")
            return False
    
    def download_track(self, spotify_url):
        print(f"\n{'='*60}")
        print(f"Processing Spotify URL: {spotify_url}")
        print(f"{'='*60}\n")
        
        content_type, content_id = self.extract_spotify_info(spotify_url)
        
        if content_type != 'track':
            print("Invalid Spotify track URL")
            return False
        
        metadata = self.get_track_metadata(content_id)
        if not metadata:
            print("Failed to get track metadata")
            return False
        
        print(f"🎵 Track: {metadata['title']}")
        print(f"👤 Artist: {metadata['artist']}")
        print(f"💿 Album: {metadata['album']}\n")
        
        success = self.download_single_track(metadata)
        
        if success:
            print(f"\n✅ Successfully downloaded!\n")
        else:
            print(f"\n❌ Download failed\n")
        
        return success
    
    def download_album(self, spotify_url):
        print(f"\n{'='*60}")
        print(f"Processing Spotify Album URL: {spotify_url}")
        print(f"{'='*60}")
        
        content_type, content_id = self.extract_spotify_info(spotify_url)
        
        if content_type != 'album':
            print("Invalid Spotify album URL")
            return False
        
        tracks = self.get_album_tracks(content_id)
        if not tracks:
            print("Failed to get album tracks")
            return False
        
        successful = 0
        failed = 0
        
        with tqdm(total=len(tracks), desc="Overall Progress", unit="track") as pbar:
            for metadata in tracks:
                success = self.download_single_track(metadata, pbar)
                if success:
                    successful += 1
                else:
                    failed += 1
                pbar.update(1)
                time.sleep(0.5)
        
        print(f"\n{'='*60}")
        print(f"✅ Successfully downloaded: {successful}/{len(tracks)}")
        if failed > 0:
            print(f"❌ Failed: {failed}/{len(tracks)}")
        print(f"{'='*60}\n")
        
        return True
    
    def download_playlist(self, spotify_url):
        print(f"\n{'='*60}")
        print(f"Processing Spotify Playlist URL: {spotify_url}")
        print(f"{'='*60}")
        
        content_type, content_id = self.extract_spotify_info(spotify_url)
        
        if content_type != 'playlist':
            print("Invalid Spotify playlist URL")
            return False
        
        tracks = self.get_playlist_tracks(content_id)
        if not tracks:
            print("Failed to get playlist tracks")
            return False
        
        successful = 0
        failed = 0
        
        with tqdm(total=len(tracks), desc="Overall Progress", unit="track") as pbar:
            for metadata in tracks:
                success = self.download_single_track(metadata, pbar)
                if success:
                    successful += 1
                else:
                    failed += 1
                pbar.update(1)
                time.sleep(0.5)
        
        print(f"\n{'='*60}")
        print(f"✅ Successfully downloaded: {successful}/{len(tracks)}")
        if failed > 0:
            print(f"❌ Failed: {failed}/{len(tracks)}")
        print(f"{'='*60}\n")
        
        return True
    
    def download_from_url(self, spotify_url):
        content_type, content_id = self.extract_spotify_info(spotify_url)
        
        if not content_type:
            print("❌ Invalid Spotify URL")
            return False
        
        if content_type == 'track':
            return self.download_track(spotify_url)
        elif content_type == 'album':
            return self.download_album(spotify_url)
        elif content_type == 'playlist':
            return self.download_playlist(spotify_url)
        
        return False


def main():
    print("=" * 60)
    print("🎵  Spotify Music Downloader")
    print("=" * 60)
    print("Supports: Tracks, Albums, and Playlists")
    print("=" * 60)
    
    downloader = SpotifyDownloader()
    
    while True:
        print("\nEnter Spotify URL (track/album/playlist) or 'quit' to exit:")
        try:
            url = input("> ").strip()
        except EOFError:
            break
        
        if url.lower() in ['quit', 'exit', 'q']:
            break
        
        if not url:
            continue
        
        if 'spotify.com/' not in url:
            print("❌ Please enter a valid Spotify URL")
            continue
        
        try:
            downloader.download_from_url(url)
        except KeyboardInterrupt:
            print("\n\n⚠️  Download interrupted by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n👋 Goodbye!")


if __name__ == "__main__":
    main()