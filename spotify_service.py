import os
import re
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError

from config import Config, BASE_DIR
from parser import parse_songs_from_text, format_playlist_meta, get_creation_timestamp

class SpotifyService:
    def __init__(self):
        self.scope = "playlist-modify-public playlist-modify-private user-read-private"
        self.cache_path = str(BASE_DIR / ".spotify_cache")
        self._sp: Optional[spotipy.Spotify] = None
        self._user_id: Optional[str] = None
        self._user_name: Optional[str] = None

    def is_configured(self) -> bool:
        return Config.is_spotify_configured()

    def get_auth_manager(self) -> SpotifyOAuth:
        return SpotifyOAuth(
            client_id=Config.SPOTIPY_CLIENT_ID,
            client_secret=Config.SPOTIPY_CLIENT_SECRET,
            redirect_uri=Config.SPOTIPY_REDIRECT_URI,
            scope=self.scope,
            cache_path=self.cache_path,
            open_browser=True
        )

    def authenticate(self) -> spotipy.Spotify:
        """Authenticate with Spotify using cached token or OAuth browser flow."""
        if not self.is_configured():
            raise ValueError(
                "Spotify credentials are not configured. Please set SPOTIPY_CLIENT_ID and "
                "SPOTIPY_CLIENT_SECRET in your .env file or through the app settings."
            )

        auth_manager = self.get_auth_manager()
        self._sp = spotipy.Spotify(auth_manager=auth_manager)

        # Test connection & fetch current user
        try:
            user = self._sp.current_user()
            self._user_id = user["id"]
            self._user_name = user.get("display_name") or user["id"]
            return self._sp
        except spotipy.SpotifyException as e:
            if "Active premium subscription required" in str(e) or e.http_status == 403:
                raise PermissionError(
                    "Spotify API Policy Restriction: Spotify requires the owner of the Developer App "
                    "to have an active Spotify Premium subscription to make API requests.\n\n"
                    "Solutions:\n"
                    "1. Use a Spotify account that has Premium (or a free trial) to create the app on developer.spotify.com.\n"
                    "2. Or use Free Mode / Spotlistr (no Premium needed, works with Free Spotify accounts).\n"
                    "3. Or use Apple Music export: 'python notepad_watcher.py --platform apple'."
                )
            raise e

    def get_client(self) -> spotipy.Spotify:
        if self._sp is None:
            return self.authenticate()
        return self._sp

    def get_current_user_profile(self) -> Dict[str, Any]:
        sp = self.get_client()
        user = sp.current_user()
        return {
            "id": user["id"],
            "display_name": user.get("display_name", user["id"]),
            "email": user.get("email", ""),
            "images": user.get("images", []),
            "url": user.get("external_urls", {}).get("spotify", "")
        }

    def clean_search_term(self, text: str) -> str:
        """Removes noise like (Official Video), [HD], feat., ft. for better search accuracy."""
        clean = re.sub(r"[\(\[\{].*?[\)\]\}]", "", text)
        clean = re.sub(r"\b(ft|feat|featuring|official|video|audio|lyrics|hd|remastered)\b", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def search_track(self, query: str, title: Optional[str] = None, artist: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Multi-tier search to find the best match for a song on Spotify.
        """
        sp = self.get_client()

        search_strategies = []

        # Strategy 1: specific track & artist filters if available
        if title and artist:
            clean_t = self.clean_search_term(title)
            clean_a = self.clean_search_term(artist)
            if clean_t and clean_a:
                # Try Title as track and Artist as artist
                search_strategies.append(f"track:{clean_t} artist:{clean_a}")
                # Also try reverse (in case user wrote Title - Artist instead of Artist - Title)
                search_strategies.append(f"track:{clean_a} artist:{clean_t}")

        # Strategy 2: literal query
        search_strategies.append(query)

        # Strategy 3: cleaned query without noise
        clean_q = self.clean_search_term(query)
        if clean_q and clean_q != query:
            search_strategies.append(clean_q)

        # Strategy 4: just title if we have one
        if title:
            clean_t = self.clean_search_term(title)
            if clean_t and clean_t not in search_strategies:
                search_strategies.append(clean_t)

        for q in search_strategies:
            try:
                results = sp.search(q=q, limit=1, type="track")
                tracks = results.get("tracks", {}).get("items", [])
                if tracks:
                    track = tracks[0]
                    artists = ", ".join([a["name"] for a in track.get("artists", [])])
                    album = track.get("album", {}).get("name", "Unknown Album")
                    images = track.get("album", {}).get("images", [])
                    image_url = images[0]["url"] if images else ""
                    
                    return {
                        "uri": track["uri"],
                        "name": track["name"],
                        "artist": artists,
                        "album": album,
                        "image_url": image_url,
                        "spotify_url": track.get("external_urls", {}).get("spotify", ""),
                        "preview_url": track.get("preview_url")
                    }
            except Exception:
                continue

        return None

    def create_playlist_from_songs(
        self,
        songs: List[Dict[str, Any]],
        playlist_name: Optional[str] = None,
        is_public: bool = True,
        on_progress: Optional[Callable[[int, int, Dict[str, Any], Optional[Dict[str, Any]]], None]] = None
    ) -> Dict[str, Any]:
        """
        Creates a Spotify playlist from a parsed song list.
        Captures the exact creation timestamp and embeds it in title and description.
        """
        if not songs:
            raise ValueError("No songs provided to create a playlist.")

        sp = self.get_client()
        user = sp.current_user()
        user_id = user["id"]

        # Fetch current date and time
        creation_meta = format_playlist_meta(
            prefix=Config.PLAYLIST_DEFAULT_PREFIX,
            song_count=len(songs)
        )

        final_title = playlist_name.strip() if (playlist_name and playlist_name.strip()) else creation_meta["name"]
        final_description = creation_meta["description"]

        # Create Spotify playlist
        playlist = sp.user_playlist_create(
            user=user_id,
            name=final_title,
            public=is_public,
            description=final_description
        )
        playlist_id = playlist["id"]
        playlist_url = playlist.get("external_urls", {}).get("spotify", "")

        matched_tracks: List[Dict[str, Any]] = []
        unmatched_songs: List[Dict[str, Any]] = []
        track_uris: List[str] = []

        total_songs = len(songs)
        for idx, song_info in enumerate(songs, start=1):
            query = song_info.get("query", song_info.get("raw", ""))
            title = song_info.get("title")
            artist = song_info.get("artist")

            match = self.search_track(query, title=title, artist=artist)

            if match:
                matched_tracks.append({
                    "original_query": query,
                    "matched_title": match["name"],
                    "matched_artist": match["artist"],
                    "album": match["album"],
                    "image_url": match["image_url"],
                    "spotify_url": match["spotify_url"],
                    "uri": match["uri"]
                })
                track_uris.append(match["uri"])
            else:
                unmatched_songs.append(song_info)

            if on_progress:
                on_progress(idx, total_songs, song_info, match)

        # Batch add tracks (Spotify allows up to 100 tracks per call)
        if track_uris:
            chunk_size = 100
            for i in range(0, len(track_uris), chunk_size):
                chunk = track_uris[i:i + chunk_size]
                sp.playlist_add_items(playlist_id, chunk)

        return {
            "success": True,
            "playlist_id": playlist_id,
            "playlist_name": final_title,
            "playlist_url": playlist_url,
            "created_at": creation_meta["timestamp_info"]["formatted_full"],
            "timestamp_info": creation_meta["timestamp_info"],
            "total_submitted": total_songs,
            "matched_count": len(matched_tracks),
            "unmatched_count": len(unmatched_songs),
            "matched_tracks": matched_tracks,
            "unmatched_songs": unmatched_songs
        }

    def create_playlist_from_raw_text(
        self,
        raw_text: str,
        playlist_name: Optional[str] = None,
        is_public: bool = True,
        on_progress: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Convenience method to take raw notepad text directly and create playlist."""
        songs = parse_songs_from_text(raw_text)
        return self.create_playlist_from_songs(songs, playlist_name=playlist_name, is_public=is_public, on_progress=on_progress)
