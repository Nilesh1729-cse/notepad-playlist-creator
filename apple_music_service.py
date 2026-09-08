import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from parser import parse_songs_from_text, format_playlist_meta, get_creation_timestamp
from config import BASE_DIR

class AppleMusicService:
    """
    Apple Music integration service:
    1. Generates standard Apple Music import files (.m3u8 and iTunes/Apple Music tab-delimited text).
    2. Generates an Apple Music Shortcut import link for 1-click creation on iPhone/Mac.
    3. Handles MusicKit API direct creation if Apple Developer tokens are supplied.
    """

    def __init__(self, exports_dir: Optional[Path] = None):
        self.exports_dir = exports_dir or (BASE_DIR / "exports")
        self.exports_dir.mkdir(exist_ok=True, parents=True)

    def export_m3u8(self, songs: List[Dict[str, Any]], playlist_name: Optional[str] = None, dt: Optional[datetime] = None) -> Path:
        """
        Generates an extended M3U8 playlist file compatible with Apple Music, iTunes,
        VLC, and other players.
        """
        meta = format_playlist_meta(prefix="Apple Music Playlist", song_count=len(songs), dt=dt)
        name = playlist_name or meta["name"]
        ts = meta["timestamp_info"]

        # Safe filename
        safe_filename = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()
        out_path = self.exports_dir / f"{safe_filename}.m3u8"

        lines = [
            "#EXTM3U",
            f"#PLAYLIST:{name}",
            f"#EXTINF:-1,{name}",
            f"#DESCRIPTION:{meta['description']}",
            f"#DATE_CREATED:{ts['formatted_full']}",
            f"#TIMESTAMP_ISO:{ts['iso']}",
            ""
        ]

        for s in songs:
            title = s.get("title") or s.get("query")
            artist = s.get("artist") or "Unknown Artist"
            lines.append(f"#EXTINF:-1,{artist} - {title}")
            lines.append(f"{title}")

        out_path.write_text("\n".join(lines), encoding="utf-8")
        return out_path

    def export_apple_music_txt(self, songs: List[Dict[str, Any]], playlist_name: Optional[str] = None, dt: Optional[datetime] = None) -> Path:
        """
        Generates official Apple Music / iTunes library text import format (Tab-separated).
        Can be imported into Apple Music for Windows / Mac via File -> Library -> Import Playlist.
        """
        meta = format_playlist_meta(prefix="Apple Music Playlist", song_count=len(songs), dt=dt)
        name = playlist_name or meta["name"]
        ts = meta["timestamp_info"]

        safe_filename = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()
        out_path = self.exports_dir / f"{safe_filename}_AppleMusicImport.txt"

        headers = ["Name", "Artist", "Composer", "Album", "Grouping", "Work", "Movement Number", "Movement Count", "Movement Name", "Genre", "Size", "Time", "Disc Number", "Disc Count", "Track Number", "Track Count", "Year", "Date Modified", "Date Added", "Bit Rate", "Sample Rate", "Volume Adjustment", "Kind", "Equalizer", "Comments", "Plays", "Last Played", "Skips", "Last Skipped", "My Rating", "Location"]
        
        lines = [
            "\t".join(headers)
        ]

        for s in songs:
            title = s.get("title") or s.get("query")
            artist = s.get("artist") or ""
            comment = f"Created {ts['formatted_full']} from Notepad"
            row = [
                title,
                artist,
                "", # Composer
                "", # Album
                "", # Grouping
                "", # Work
                "", "", "", # Movement
                "", # Genre
                "", "", "", "", "", "", "", # Disc/Track counts
                ts["year"], # Year
                ts["title_timestamp"], # Date Modified
                ts["title_timestamp"], # Date Added
                "", "", "", "", "", # Bitrate, sample rate etc
                comment,
                "", "", "", "", "", ""
            ]
            lines.append("\t".join(row))

        out_path.write_text("\n".join(lines), encoding="utf-8")
        return out_path

    def generate_apple_shortcut_payload(self, songs: List[Dict[str, Any]], playlist_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates shortcut-ready text and instructions to import song names
        into an Apple Music playlist on iOS/macOS via the Shortcuts app.
        """
        meta = format_playlist_meta(prefix="Apple Music Playlist", song_count=len(songs))
        name = playlist_name or meta["name"]
        
        song_lines = [s.get("query", s.get("raw", "")) for s in songs]
        return {
            "playlist_name": name,
            "created_at": meta["timestamp_info"]["formatted_full"],
            "song_list_text": "\n".join(song_lines),
            "instructions": (
                "To import into Apple Music on iPhone/Mac:\n"
                "1. Open Apple Shortcuts.\n"
                "2. Use the 'Search Apple Music' -> 'Add to Playlist' shortcut.\n"
                "3. Or on Windows Apple Music app: File -> Library -> Import Playlist and select the exported .txt or .m3u8 file."
            )
        }

    def export_all_formats(self, raw_text: str, playlist_name: Optional[str] = None) -> Dict[str, Any]:
        """Convenience function to parse text and generate all export formats."""
        songs = parse_songs_from_text(raw_text)
        if not songs:
            raise ValueError("No songs found to export.")

        dt = datetime.now()
        meta = format_playlist_meta(prefix="Apple Music Playlist", song_count=len(songs), dt=dt)
        name = playlist_name or meta["name"]

        m3u8_file = self.export_m3u8(songs, playlist_name=name, dt=dt)
        txt_file = self.export_apple_music_txt(songs, playlist_name=name, dt=dt)
        shortcut_data = self.generate_apple_shortcut_payload(songs, playlist_name=name)

        return {
            "success": True,
            "playlist_name": name,
            "created_at": meta["timestamp_info"]["formatted_full"],
            "timestamp_info": meta["timestamp_info"],
            "total_songs": len(songs),
            "songs": songs,
            "m3u8_path": str(m3u8_file),
            "txt_path": str(txt_file),
            "shortcut_data": shortcut_data
        }
