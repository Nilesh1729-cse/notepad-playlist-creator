import re
from datetime import datetime
from typing import List, Dict, Any, Optional

def clean_song_line(line: str) -> Optional[str]:
    """Clean a single line from Notepad text."""
    line = line.strip()
    if not line:
        return None
    
    # Ignore comments
    if line.startswith("#") or line.startswith("//"):
        return None

    # Remove leading numbering: "1.", "01.", "1 -", "1)", "[1]"
    line = re.sub(r"^\s*\[?\d+\]?[\.\)\-\:\s]+\s*", "", line)

    # Remove leading bullets: "-", "*", "•", ">"
    line = re.sub(r"^[\-\*\•\>\–\—\+]\s*", "", line)

    # Strip surrounding quotes
    line = line.strip("\"' ")

    if not line:
        return None

    return line

def extract_artist_and_title(clean_line: str) -> Dict[str, Optional[str]]:
    """
    Attempt to extract artist and title from common patterns:
    - "Artist - Title"
    - "Title by Artist"
    """
    artist: Optional[str] = None
    title: Optional[str] = None

    # Pattern: "Title by Artist"
    by_match = re.search(r"^(.+?)\s+by\s+(.+)$", clean_line, re.IGNORECASE)
    if by_match:
        title = by_match.group(1).strip()
        artist = by_match.group(2).strip()
        return {"title": title, "artist": artist}

    # Pattern: "Artist - Title" or "Artist – Title" or "Artist — Title"
    dash_match = re.split(r"\s+[\-\–\—]\s+", clean_line, maxsplit=1)
    if len(dash_match) == 2:
        part1, part2 = dash_match[0].strip(), dash_match[1].strip()
        # In general, if one has common artist words or part1 is short, it could be Artist - Title
        # We will save both suggestions
        return {"title": part2, "artist": part1}

    return {"title": clean_line, "artist": None}

def parse_songs_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Parses song list from raw notepad text.
    Handles multiple delimiters (newlines, commas if newline not used, or numbered lists).
    """
    if not text:
        return []

    lines = text.splitlines()
    # If the user pasted all songs on a single line separated by commas or semicolons
    if len(lines) == 1 and ("," in text or ";" in text):
        delimiter = ";" if ";" in text else ","
        lines = text.split(delimiter)

    parsed_songs: List[Dict[str, Any]] = []
    seen_queries = set()

    for raw_line in lines:
        cleaned = clean_song_line(raw_line)
        if not cleaned:
            continue

        extracted = extract_artist_and_title(cleaned)
        
        # Deduplication check (optional - keep unique songs)
        query_key = cleaned.lower()
        if query_key in seen_queries:
            continue
        seen_queries.add(query_key)

        parsed_songs.append({
            "raw": raw_line.strip(),
            "query": cleaned,
            "title": extracted.get("title"),
            "artist": extracted.get("artist")
        })

    return parsed_songs

def get_creation_timestamp(dt: Optional[datetime] = None) -> Dict[str, str]:
    """
    Fetches and formats the exact date and time of playlist creation.
    """
    if dt is None:
        dt = datetime.now()

    return {
        "formatted_date": dt.strftime("%B %d, %Y"),
        "formatted_time": dt.strftime("%I:%M:%S %p"),
        "formatted_full": dt.strftime("%A, %B %d, %Y at %I:%M:%S %p"),
        "title_timestamp": dt.strftime("%Y-%m-%d %H:%M"),
        "iso": dt.isoformat(),
        "year": str(dt.year),
        "month": dt.strftime("%B"),
        "day": str(dt.day)
    }

def format_playlist_meta(prefix: str = "Notepad Playlist", song_count: int = 0, dt: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Constructs the playlist title, description, and timestamp metadata.
    """
    ts = get_creation_timestamp(dt)
    name = f"{prefix} - {ts['title_timestamp']}"
    description = (
        f"Created on {ts['formatted_full']} from Notepad. "
        f"Contains {song_count} track{'s' if song_count != 1 else ''}. "
        f"Generated automatically by Notepad Playlist Creator."
    )

    return {
        "name": name,
        "description": description,
        "timestamp_info": ts
    }
