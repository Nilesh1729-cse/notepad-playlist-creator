import os
import sys
import time
import webbrowser
import subprocess
from pathlib import Path
from typing import Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config import Config, BASE_DIR
from parser import parse_songs_from_text, get_creation_timestamp
from spotify_service import SpotifyService
from apple_music_service import AppleMusicService

INITIAL_NOTEPAD_CONTENT = """# ==========================================
# PASTE YOUR SONGS BELOW (ONE PER LINE)
# Then press Ctrl+S (Save) in Notepad!
# The playlist will be created automatically.
# ==========================================

Blinding Lights - The Weeknd
Stay - The Kid LAROI & Justin Bieber
Shape of You - Ed Sheeran
Levitating - Dua Lipa
As It Was - Harry Styles
"""

class NotepadHandler(FileSystemEventHandler):
    def __init__(self, target_file: Path, platform: str = "spotify", auto_open_browser: bool = True):
        super().__init__()
        self.target_file = target_file.resolve()
        self.platform = platform
        self.auto_open_browser = auto_open_browser
        self.last_processed_time = 0
        self.last_content_hash = ""
        self.spotify_service = SpotifyService()
        self.apple_service = AppleMusicService()

    def on_modified(self, event):
        if Path(event.src_path).resolve() != self.target_file:
            return

        current_time = time.time()
        # Debounce multiple file events within 2 seconds
        if current_time - self.last_processed_time < 2:
            return

        self.process_file()

    def process_file(self):
        try:
            if not self.target_file.exists():
                return

            # Read content with encoding fallback
            try:
                content = self.target_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = self.target_file.read_text(encoding="latin-1")

            # Check hash to avoid re-triggering on identical content
            content_hash = str(hash(content.strip()))
            if content_hash == self.last_content_hash or not content.strip():
                return

            songs = parse_songs_from_text(content)
            if not songs:
                print("\n[INFO] Notepad saved, but no valid song lines were detected.")
                return

            self.last_processed_time = time.time()
            self.last_content_hash = content_hash

            ts = get_creation_timestamp()
            print("\n" + "=" * 65)
            print(f"🎵 NOTEPAD CHANGE DETECTED!")
            print(f"📅 Playlist Creation Timestamp: {ts['formatted_full']}")
            print(f"📝 Found {len(songs)} song(s) in Notepad.")
            print("=" * 65)

            if self.platform.lower() == "spotify":
                self._handle_spotify(songs, ts)
            else:
                self._handle_apple_music(songs, ts)

        except Exception as e:
            print(f"\n❌ Error processing Notepad file: {e}")

    def _handle_spotify(self, songs, ts):
        if not self.spotify_service.is_configured():
            print("\n⚠️ Spotify API is not configured yet!")
            print("Please add your SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET to .env")
            print("or run 'python app_gui.py' to enter them in the setup screen.\n")
            return

        print("\nConnecting to Spotify and creating playlist...")
        
        def on_prog(idx, total, song, match):
            q = song.get("query", "")
            if match:
                print(f"  [{idx}/{total}] ✅ Found: '{q}' -> {match['name']} by {match['artist']}")
            else:
                print(f"  [{idx}/{total}] ⚠️ Not found: '{q}'")

        try:
            res = self.spotify_service.create_playlist_from_songs(
                songs=songs,
                on_progress=on_prog
            )

            print("\n" + "🎉" * 25)
            print(f"🎉 PLAYLIST CREATED SUCCESSFULLY!")
            print(f"📌 Name: {res['playlist_name']}")
            print(f"🕒 Timestamp: {res['created_at']}")
            print(f"📊 Added: {res['matched_count']}/{res['total_submitted']} tracks")
            print(f"🔗 URL: {res['playlist_url']}")
            print("🎉" * 25 + "\n")

            if self.auto_open_browser and res.get("playlist_url"):
                print("🌐 Opening playlist in your web browser...")
                webbrowser.open(res["playlist_url"])

        except PermissionError as pe:
            print("\n" + "!" * 65)
            print("⚠️ SPOTIFY PREMIUM REQUIREMENT DETECTED")
            print("!" * 65)
            print(f"{pe}\n")
            
            # Copy songs to clipboard for 1-click Spotlistr
            try:
                songs_text = "\n".join([s.get("query", s.get("raw", "")) for s in songs])
                subprocess.run(["clip"], input=songs_text.encode("utf-16"), check=True)
                print("📋 Good news: All your songs have been COPIED TO YOUR CLIPBOARD!")
                print("🌐 Opening Spotlistr (100% Free - No Spotify Premium needed)...")
                print("👉 Just press Ctrl+V to paste your songs and create the playlist!")
                webbrowser.open("https://www.spotlistr.com/search/textbox")
            except Exception:
                pass

        except Exception as e:
            if "Active premium subscription required" in str(e) or "403" in str(e):
                print("\n" + "!" * 65)
                print("⚠️ SPOTIFY ERROR: Premium subscription required for developer app owner.")
                print("!" * 65)
                try:
                    songs_text = "\n".join([s.get("query", s.get("raw", "")) for s in songs])
                    subprocess.run(["clip"], input=songs_text.encode("utf-16"), check=True)
                    print("📋 Your songs have been copied to your clipboard!")
                    print("🌐 Opening Spotlistr (Free Spotify playlist creator)...")
                    webbrowser.open("https://www.spotlistr.com/search/textbox")
                except Exception:
                    pass
            else:
                print(f"\n❌ Spotify error: {e}")

    def _handle_apple_music(self, songs, ts):
        print("\nGenerating Apple Music playlist files...")
        res = self.apple_service.export_all_formats("\n".join([s["raw"] for s in songs]))
        print("\n" + "🎉" * 25)
        print(f"🎉 APPLE MUSIC PLAYLIST EXPORTED!")
        print(f"📌 Name: {res['playlist_name']}")
        print(f"🕒 Timestamp: {res['created_at']}")
        print(f"📁 M3U8 File: {res['m3u8_path']}")
        print(f"📁 Apple Music Import TXT: {res['txt_path']}")
        print("🎉" * 25 + "\n")

def start_watcher(file_path: Optional[str] = None, platform: str = "spotify", open_notepad: bool = True):
    target = Path(file_path) if file_path else Path(Config.DEFAULT_NOTEPAD_FILE)
    target = target.resolve()

    # Ensure target file exists
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(INITIAL_NOTEPAD_CONTENT, encoding="utf-8")
        print(f"📄 Created new Notepad file: {target}")

    # Launch native Windows Notepad if requested
    if open_notepad and sys.platform == "win32":
        try:
            print(f"🚀 Opening Windows Notepad with '{target.name}'...")
            subprocess.Popen(["notepad.exe", str(target)])
        except Exception as e:
            print(f"Could not open notepad.exe: {e}")

    handler = NotepadHandler(target_file=target, platform=platform)
    observer = Observer()
    observer.schedule(handler, path=str(target.parent), recursive=False)
    observer.start()

    print("\n" + "#" * 65)
    print("👀 NOTEPAD PLAYLIST WATCHER IS RUNNING")
    print(f"📂 Watching File: {target}")
    print(f"🎯 Target Platform: {platform.upper()}")
    print("👉 HOW TO USE:")
    print("   1. Paste any list of songs into the Notepad window.")
    print("   2. Press Ctrl + S (Save).")
    print("   3. Your playlist will be created immediately with the exact timestamp!")
    print("   (Press Ctrl+C in this terminal to stop the watcher)")
    print("#" * 65 + "\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Live Notepad to Spotify/Apple Playlist Watcher")
    parser.add_argument("--file", "-f", default=None, help="Path to notepad .txt file to watch")
    parser.add_argument("--platform", "-p", default="spotify", choices=["spotify", "apple"], help="Target platform (spotify or apple)")
    parser.add_argument("--no-notepad", action="store_true", help="Do not automatically launch Windows Notepad")
    args = parser.parse_args()

    start_watcher(file_path=args.file, platform=args.platform, open_notepad=not args.no_notepad)
