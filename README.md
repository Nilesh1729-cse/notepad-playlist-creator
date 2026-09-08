# 🎵 Notepad to Spotify & Apple Music Playlist Creator

> **Paste song names into Notepad and instantly generate a Spotify or Apple Music playlist tagged with the exact creation date and time.**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://notepad-playlist-creator-ckpdtdsr3v4dzf3ulifgjx.streamlit.app)

🔗 **Live Web App:** [https://notepad-playlist-creator-ckpdtdsr3v4dzf3ulifgjx.streamlit.app](https://notepad-playlist-creator-ckpdtdsr3v4dzf3ulifgjx.streamlit.app)

---

## 🚀 Key Features

- 📝 **Paste from Notepad:** Simply paste songs one per line (supports artist names, titles, numbered lists, and bullet points).
- 🕒 **Automatic Date & Time Tagging:** Every playlist is tagged with the exact creation timestamp (e.g. `Notepad Playlist - 2026-09-08 22:30`) in both the title and playlist description.
- 🟢 **Spotify Integration:** Directly matches tracks and creates playlists in your Spotify account.
- 🍎 **Apple Music Export:** Generates `.m3u8` playlist files and iTunes/Apple Music text library import files with timestamp headers.
- 👥 **Multi-User Cloud Support:** Isolated user sessions — multiple people can use the app without token collisions.

---

## ⚠️ Important Spotify Conditions & Limits

Please note the following official Spotify Developer platform requirements:

1. **Active Spotify Premium Required for App Owner:**  
   Spotify's API requires the account that creates and hosts the Developer App to have an active **Spotify Premium** subscription.
   
2. **Spotify Development Mode User Whitelist (Max Allowed Users):**  
   By default, new apps on Spotify operate in **Development Mode**, which strictly limits access to **a small whitelist of users (up to 5 to 25 users max)**.
   - For a friend to log in, the app owner must add their **Spotify Email** in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) under the **User Management** tab.
   - If an unlisted user tries to log in, Spotify blocks access with: *`The user is not registered for this application.`*

3. **How to Bypass the User Limit (Self-Serve Keys):**  
   Anyone can bypass the whitelist limit by clicking **"🔑 Use Your Own Spotify Keys"** in the sidebar and entering their own free Client ID and Secret (saved securely only in their private browser session).

4. **100% Free Alternatives (No Premium / No Setup Needed):**  
   - **Apple Music Export:** Click **Export for Apple Music** to immediately download `.m3u8` and `.txt` playlist files with full timestamps.
   - **Spotlistr Tool:** Click **Open Spotlistr** to import your song list into a free Spotify account with zero developer setup.

---

## 📋 Supported Song Formats

You can paste songs in almost any format:
```text
The Weeknd - Blinding Lights
Queen - Bohemian Rhapsody
Shape of You by Ed Sheeran
1. Stay - The Kid LAROI & Justin Bieber
- Levitating - Dua Lipa
• Hotel California - Eagles
```

---

## 💻 Running Locally

If you prefer running the application on your local machine:

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Credentials
Copy `.env.example` to `.env` and enter your Spotify keys:
```env
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

### 3. Choose Your Mode
- **Live Windows Notepad Watcher:**  
  Run `run_notepad_watcher.bat` (or `python notepad_watcher.py`). Open `songs_notepad.txt` in Windows Notepad, paste songs, and press **Ctrl+S** to auto-create!
- **Desktop GUI:**  
  Run `run_gui.bat` (or `python app_gui.py`).
- **Web Dashboard:**  
  Run `run_web.bat` (or `streamlit run web_app.py`).

---

## 📄 License
MIT License. Created with ❤️ for music lovers.
