import unittest
from unittest.mock import MagicMock, patch
from spotify_service import SpotifyService

class TestSpotifyService(unittest.TestCase):
    @patch("spotify_service.Config.is_spotify_configured", return_value=True)
    def test_create_playlist_from_songs_mock(self, mock_cfg):
        service = SpotifyService()
        
        # Mock Spotipy client
        mock_sp = MagicMock()
        mock_sp.current_user.return_value = {"id": "test_user_123", "display_name": "Test User"}
        mock_sp.user_playlist_create.return_value = {
            "id": "pl_123",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/pl_123"}
        }

        # Mock search results
        def fake_search(q, limit, type):
            if "notfound" in q.lower():
                return {"tracks": {"items": []}}
            return {
                "tracks": {
                    "items": [{
                        "uri": f"spotify:track:{hash(q)}",
                        "name": f"Track for {q}",
                        "artists": [{"name": "Mock Artist"}],
                        "album": {"name": "Mock Album", "images": [{"url": "http://img.jpg"}]},
                        "external_urls": {"spotify": f"https://open.spotify.com/track/{hash(q)}"},
                        "preview_url": "http://preview.mp3"
                    }]
                }
            }
        mock_sp.search.side_effect = fake_search
        service._sp = mock_sp

        songs = [
            {"query": "The Weeknd - Blinding Lights", "title": "Blinding Lights", "artist": "The Weeknd"},
            {"query": "Nonexistent Song notfound", "title": "notfound", "artist": "none"}
        ]

        res = service.create_playlist_from_songs(songs)

        self.assertTrue(res["success"])
        self.assertEqual(res["playlist_id"], "pl_123")
        self.assertIn("Notepad Playlist", res["playlist_name"])
        self.assertIn("2026", res["created_at"])
        self.assertEqual(res["matched_count"], 1)
        self.assertEqual(res["unmatched_count"], 1)
        self.assertEqual(len(res["matched_tracks"]), 1)
        self.assertEqual(len(res["unmatched_songs"]), 1)
        
        # Verify spotipy calls
        mock_sp.user_playlist_create.assert_called_once()
        mock_sp.playlist_add_items.assert_called_once()

if __name__ == "__main__":
    unittest.main()
