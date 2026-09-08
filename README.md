# 🎵 Notepad to Spotify & Apple Music Playlist Creator

Paste a list of songs into Notepad (or the app interface) and instantly generate a playlist on **Spotify** or **Apple Music**. 

The app automatically fetches the exact **local date and time** when the playlist is created, embedding the timestamp directly in both the playlist title and description.

---

## ⚡ 3 Ways to Use It

### 1. 📄 Live Windows Notepad Watcher (Most direct)
Double-click `run_notepad_watcher.bat` (or run `python notepad_watcher.py`).
- This opens native **Windows Notepad** (`songs_notepad.txt`).
- Paste your songs into Notepad.
- Hit **Ctrl + S** (Save).
- The watcher immediately detects the save, fetches the current date & time, creates the playlist, and opens it directly in your browser!

### 2. 🖥️ Desktop GUI App
Double-click `run_gui.bat` (or run `python app_gui.py`).
- A clean, modern desktop Notepad interface.
- Live clock banner showing the exact timestamp that will be attached to the playlist.
- Paste clipboard, load sample songs, or edit songs.
- 1-Click buttons for **Spotify** and **Apple Music**.
- Built-in Spotify API credentials setup window.

### 3. 🌐 Web Dashboard (Streamlit)
Double-click `run_web.bat` (or run `streamlit run web_app.py`).
- Modern browser-based dashboard on `http://localhost:8501`.
- Live timestamp clock and metadata preview.
- Album cover art previews, track audio previews, and matched song status.
- Direct link to open the newly generated playlist.

---

## 🕒 Automatic Date & Time Tagging

Every playlist created captures the exact local system timestamp:
- **Playlist Name**: `Notepad Playlist - YYYY-MM-DD HH:MM` (e.g., `Notepad Playlist - 2026-09-07 23:45`)
- **Playlist Description**: `Created on Monday, September 07, 2026 at 11:45:12 PM from Notepad. Contains 15 tracks. Generated automatically by Notepad Playlist Creator.`
- **Apple Music Exports**: Embeds `#DATE_CREATED`, `#TIMESTAMP_ISO`, and timestamp headers directly into the `.m3u8` and tab-separated `.txt` import files.

---

## 🔑 2-Minute Spotify API Setup

To allow the app to create playlists in your personal Spotify account:
1. Log in to the free [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Click **Create App**:
   - **App Name**: `Notepad Playlist Creator`
   - **Redirect URI**: `http://127.0.0.1:8888/callback`
   - Check the terms and click **Save**.
3. Go to **Settings** on your new app and copy:
   - **Client ID**
   - **Client Secret**
4. Paste them into `.env` (or enter them directly in the app's Settings popup):
   ```env
   SPOTIPY_CLIENT_ID=your_client_id_here
   SPOTIPY_CLIENT_SECRET=your_client_secret_here
   SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
   ```
5. On first run, a browser tab will open asking you to log in to Spotify and grant playlist permissions. Once authorized, a token is cached locally so you won't need to log in again!

---

## 🍎 Apple Music Support

Apple Music playlists can be generated in 2 formats:
1. **`.m3u8` Playlist File**: Standard multimedia playlist file compatible with Apple Music, iTunes, VLC, etc.
2. **Apple Music / iTunes Library Import (`.txt`)**: 
   - In the Apple Music app or iTunes on Windows/Mac, go to:
     `File` ➔ `Library` ➔ `Import Playlist...`
   - Select the generated `.txt` or `.m3u8` file to instantly add all songs into a new playlist.

---

## 📋 Supported Song Formats

You can paste songs in almost any format into Notepad:
- **Title and Artist**: `The Weeknd - Blinding Lights` or `Blinding Lights - The Weeknd`
- **With "by"**: `Shape of You by Ed Sheeran`
- **Numbered lists**:
  ```text
  1. Bohemian Rhapsody - Queen
  2. Hotel California - Eagles
  3. Stay by The Kid LAROI
  ```
- **Bulleted lists**:
  ```text
  - Levitating - Dua Lipa
  * As It Was - Harry Styles
  ```
- **Plain titles**: `Yesterday`
