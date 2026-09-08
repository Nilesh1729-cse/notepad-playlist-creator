import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory for the app
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
ENV_EXAMPLE = BASE_DIR / ".env.example"

# Load existing .env if present, otherwise try .env.example
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
elif ENV_EXAMPLE.exists():
    load_dotenv(ENV_EXAMPLE)
else:
    load_dotenv()

def get_setting(key: str, default: str = "") -> str:
    """Retrieve setting from Streamlit secrets (if in cloud) or environment/.env."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            val = str(st.secrets[key]).strip()
            if val:
                return val
    except Exception:
        pass
    return os.getenv(key, default).strip()

class Config:
    @classmethod
    def get_client_id(cls) -> str:
        return get_setting("SPOTIPY_CLIENT_ID", "")

    @classmethod
    def get_client_secret(cls) -> str:
        return get_setting("SPOTIPY_CLIENT_SECRET", "")

    @classmethod
    def get_redirect_uri(cls) -> str:
        return get_setting("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

    SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID", "")
    SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET", "")
    SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    DEFAULT_NOTEPAD_FILE = os.getenv("NOTEPAD_FILE_PATH", str(BASE_DIR / "songs_notepad.txt"))
    PLAYLIST_DEFAULT_PREFIX = os.getenv("PLAYLIST_DEFAULT_PREFIX", "Notepad Playlist")

    @classmethod
    def is_spotify_configured(cls) -> bool:
        """Check if Spotify API credentials are set."""
        client_id = cls.get_client_id()
        client_secret = cls.get_client_secret()
        return bool(client_id and client_secret and client_id != "your_spotify_client_id_here")

    @classmethod
    def save_spotify_credentials(cls, client_id: str, client_secret: str, redirect_uri: str = "http://127.0.0.1:8888/callback"):
        """Save Spotify credentials to .env file."""
        content = (
            f"# Spotify Developer API Credentials\n"
            f"SPOTIPY_CLIENT_ID={client_id.strip()}\n"
            f"SPOTIPY_CLIENT_SECRET={client_secret.strip()}\n"
            f"SPOTIPY_REDIRECT_URI={redirect_uri.strip()}\n\n"
            f"# Notepad file to watch\n"
            f"NOTEPAD_FILE_PATH={cls.DEFAULT_NOTEPAD_FILE}\n"
            f"PLAYLIST_DEFAULT_PREFIX=Notepad Playlist\n"
        )
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Update current environment
        os.environ["SPOTIPY_CLIENT_ID"] = client_id.strip()
        os.environ["SPOTIPY_CLIENT_SECRET"] = client_secret.strip()
        os.environ["SPOTIPY_REDIRECT_URI"] = redirect_uri.strip()
        cls.SPOTIPY_CLIENT_ID = client_id.strip()
        cls.SPOTIPY_CLIENT_SECRET = client_secret.strip()
        cls.SPOTIPY_REDIRECT_URI = redirect_uri.strip()
