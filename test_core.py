import unittest
from datetime import datetime
from pathlib import Path
import shutil

from parser import clean_song_line, extract_artist_and_title, parse_songs_from_text, get_creation_timestamp, format_playlist_meta
from apple_music_service import AppleMusicService
from config import Config

class TestNotepadParser(unittest.TestCase):
    def test_clean_song_line(self):
        self.assertEqual(clean_song_line("1. Blinding Lights"), "Blinding Lights")
        self.assertEqual(clean_song_line("01. The Weeknd - Blinding Lights"), "The Weeknd - Blinding Lights")
        self.assertEqual(clean_song_line("- Bohemian Rhapsody"), "Bohemian Rhapsody")
        self.assertEqual(clean_song_line("• Hotel California"), "Hotel California")
        self.assertEqual(clean_song_line("[3] Shape of You"), "Shape of You")
        self.assertIsNone(clean_song_line("# A comment line"))
        self.assertIsNone(clean_song_line("   "))

    def test_extract_artist_and_title(self):
        res1 = extract_artist_and_title("The Weeknd - Blinding Lights")
        self.assertEqual(res1["artist"], "The Weeknd")
        self.assertEqual(res1["title"], "Blinding Lights")

        res2 = extract_artist_and_title("Stay by The Kid LAROI & Justin Bieber")
        self.assertEqual(res2["artist"], "The Kid LAROI & Justin Bieber")
        self.assertEqual(res2["title"], "Stay")

        res3 = extract_artist_and_title("Just A Track Name")
        self.assertEqual(res3["title"], "Just A Track Name")
        self.assertIsNone(res3["artist"])

    def test_parse_songs_from_text(self):
        sample = """
        # My Summer Playlist
        1. The Weeknd - Blinding Lights
        2. Stay by The Kid LAROI
        - Ed Sheeran - Shape of You
        • Levitating
        
        // Another comment
        Harry Styles - As It Was
        1. The Weeknd - Blinding Lights
        """
        songs = parse_songs_from_text(sample)
        self.assertEqual(len(songs), 5) # 5 unique songs, duplicate removed
        self.assertEqual(songs[0]["title"], "Blinding Lights")
        self.assertEqual(songs[0]["artist"], "The Weeknd")
        self.assertEqual(songs[1]["title"], "Stay")
        self.assertEqual(songs[1]["artist"], "The Kid LAROI")
        self.assertEqual(songs[2]["title"], "Shape of You")
        self.assertEqual(songs[2]["artist"], "Ed Sheeran")
        self.assertEqual(songs[3]["title"], "Levitating")
        self.assertEqual(songs[4]["title"], "As It Was")
        self.assertEqual(songs[4]["artist"], "Harry Styles")

    def test_creation_timestamp(self):
        fixed_dt = datetime(2026, 9, 7, 23, 40, 15)
        ts = get_creation_timestamp(fixed_dt)
        self.assertEqual(ts["formatted_date"], "September 07, 2026")
        self.assertEqual(ts["formatted_time"], "11:40:15 PM")
        self.assertIn("Monday, September 07, 2026", ts["formatted_full"])
        self.assertEqual(ts["title_timestamp"], "2026-09-07 23:40")

        meta = format_playlist_meta(prefix="Test Playlist", song_count=10, dt=fixed_dt)
        self.assertEqual(meta["name"], "Test Playlist - 2026-09-07 23:40")
        self.assertIn("Created on Monday, September 07, 2026", meta["description"])
        self.assertIn("Contains 10 tracks", meta["description"])

class TestAppleMusicService(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(__file__).resolve().parent / "test_exports"
        self.test_dir.mkdir(exist_ok=True)
        self.service = AppleMusicService(exports_dir=self.test_dir)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_export_all_formats(self):
        raw_text = "1. Artist A - Song A\n2. Song B by Artist B"
        res = self.service.export_all_formats(raw_text, playlist_name="Test Apple Playlist")
        self.assertTrue(res["success"])
        self.assertEqual(res["total_songs"], 2)
        
        m3u8_path = Path(res["m3u8_path"])
        txt_path = Path(res["txt_path"])
        self.assertTrue(m3u8_path.exists())
        self.assertTrue(txt_path.exists())

        m3u8_content = m3u8_path.read_text(encoding="utf-8")
        self.assertIn("#EXTM3U", m3u8_content)
        self.assertIn("#DATE_CREATED:", m3u8_content)
        self.assertIn("Artist A - Song A", m3u8_content)

        txt_content = txt_path.read_text(encoding="utf-8")
        self.assertIn("Name\tArtist\tComposer", txt_content)
        self.assertIn("Song A\tArtist A", txt_content)

if __name__ == "__main__":
    unittest.main()
