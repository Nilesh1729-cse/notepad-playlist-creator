import streamlit as st
from datetime import datetime
from pathlib import Path
import time

from config import Config, BASE_DIR
from parser import parse_songs_from_text, get_creation_timestamp, format_playlist_meta
from spotify_service import SpotifyService
from apple_music_service import AppleMusicService

# Page Configuration
st.set_page_config(
    page_title="Notepad Playlist Creator",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1DB954;
        margin-bottom: 0px;
    }
    .sub-title {
        color: #A0A0A0;
        font-size: 1.05rem;
        margin-bottom: 20px;
    }
    .timestamp-box {
        background-color: #1a1a1a;
        border-left: 4px solid #1DB954;
        padding: 12px 18px;
        border-radius: 6px;
        margin-bottom: 20px;
    }
    .track-card {
        background-color: #242424;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Services
spotify_service = SpotifyService()
apple_service = AppleMusicService()

# --- SIDEBAR: Settings & Credentials ---
with st.sidebar:
    st.image("https://storage.googleapis.com/pr-newsroom-wp/1/2023/05/Spotify_Primary_Logo_RGB_Green.png", width=140)
    st.title("⚙️ App Settings")

    st.markdown("### 🔑 Spotify API Configuration")
    if spotify_service.is_configured():
        st.success("✅ Spotify credentials are active!")
    else:
        st.warning("⚠️ Spotify API credentials needed.")

    with st.expander("Setup / Update Spotify Keys", expanded=not spotify_service.is_configured()):
        st.markdown("""
        **How to get free Spotify keys:**
        1. Visit [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
        2. Click **Create App**
        3. Set Redirect URI to:  
           `http://127.0.0.1:8888/callback`
        4. Copy Client ID and Secret below:
        """)
        new_cid = st.text_input("Client ID", value=Config.SPOTIPY_CLIENT_ID if spotify_service.is_configured() else "", type="default")
        new_sec = st.text_input("Client Secret", value=Config.SPOTIPY_CLIENT_SECRET if spotify_service.is_configured() else "", type="password")
        new_uri = st.text_input("Redirect URI", value=Config.SPOTIPY_REDIRECT_URI)

        if st.button("💾 Save Credentials", use_container_width=True):
            if new_cid.strip() and new_sec.strip():
                Config.save_spotify_credentials(new_cid.strip(), new_sec.strip(), new_uri.strip())
                st.success("Credentials saved to .env! Refreshing...")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Please provide both Client ID and Client Secret.")

    st.divider()
    st.markdown("### 🍎 Apple Music")
    st.info(
        "Apple Music exports generate standard `.m3u8` and iTunes text format files "
        "with creation timestamps that can be imported directly into Apple Music on Windows, Mac, or iPhone."
    )

# --- MAIN CONTENT ---
st.markdown('<div class="main-title">🎵 Notepad to Spotify & Apple Music</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Paste songs from Notepad to instantly create a playlist tagged with the exact creation date & time.</div>', unsafe_allow_html=True)

# Fetch and display current timestamp
ts_now = get_creation_timestamp()
st.markdown(f"""
<div class="timestamp-box">
    <b>🕒 Current Timestamp:</b> {ts_now['formatted_full']}<br>
    <span style="color: #999; font-size: 0.9rem;">This date and time will be embedded in your playlist name and metadata automatically upon creation.</span>
</div>
""", unsafe_allow_html=True)

col_input, col_meta = st.columns([2, 1])

with col_meta:
    st.subheader("Playlist Settings")
    custom_title = st.text_input("Playlist Name (optional)", placeholder=f"Notepad Playlist - {ts_now['title_timestamp']}")
    is_public = st.checkbox("Public Playlist on Spotify", value=True)

    st.markdown("#### Quick Actions")
    load_sample = st.button("💡 Load Sample Songs", use_container_width=True)
    
    uploaded_file = st.file_uploader("📂 Or Upload a .txt Notepad File", type=["txt"])

with col_input:
    st.subheader("📝 Notepad (Paste Songs Here)")

    default_text = ""
    if load_sample:
        default_text = (
            "Blinding Lights - The Weeknd\n"
            "Stay - The Kid LAROI & Justin Bieber\n"
            "Shape of You - Ed Sheeran\n"
            "Levitating - Dua Lipa\n"
            "As It Was - Harry Styles\n"
            "Bohemian Rhapsody - Queen\n"
            "Hotel California - Eagles"
        )
    elif uploaded_file is not None:
        try:
            default_text = uploaded_file.read().decode("utf-8")
        except Exception:
            default_text = uploaded_file.read().decode("latin-1")

    song_input = st.text_area(
        label="Song list",
        value=default_text,
        height=320,
        placeholder="Paste songs one per line, e.g.:\n1. The Weeknd - Blinding Lights\n2. Shape of You by Ed Sheeran\n3. Bohemian Rhapsody",
        label_visibility="collapsed"
    )

# Parsed summary
parsed_songs = parse_songs_from_text(song_input)

if song_input.strip():
    st.caption(f"Found **{len(parsed_songs)}** valid song(s) in the notepad text.")

# Action Buttons
btn_col1, btn_col2 = st.columns(2)

with btn_col1:
    create_spotify = st.button("🟢 Create Spotify Playlist", type="primary", use_container_width=True, disabled=not bool(parsed_songs))

with btn_col2:
    create_apple = st.button("🍎 Export for Apple Music", use_container_width=True, disabled=not bool(parsed_songs))

# --- CREATE SPOTIFY PLAYLIST HANDLER ---
if create_spotify:
    if not spotify_service.is_configured():
        st.error("⚠️ Spotify API credentials are not set! Please expand the sidebar to enter your Client ID and Client Secret.")
    else:
        with st.status("🎵 Creating Spotify playlist...", expanded=True) as status:
            st.write(f"Capturing creation timestamp: **{ts_now['formatted_full']}**...")
            
            prog_bar = st.progress(0)
            status_text = st.empty()

            def progress_callback(idx, total, song, match):
                prog_bar.progress(idx / total)
                q = song.get("query", "")
                if match:
                    status_text.text(f"[{idx}/{total}] ✅ Found: {match['name']} - {match['artist']}")
                else:
                    status_text.text(f"[{idx}/{total}] ⚠️ Not found: {q}")

            try:
                result = spotify_service.create_playlist_from_songs(
                    songs=parsed_songs,
                    playlist_name=custom_title if custom_title.strip() else None,
                    is_public=is_public,
                    on_progress=progress_callback
                )
                status.update(label="🎉 Playlist created successfully!", state="complete", expanded=False)
                
                # Success Display
                st.balloons()
                st.success(f"🎉 **Playlist Created:** [{result['playlist_name']}]({result['playlist_url']})")
                st.markdown(f"**📅 Date & Time Created:** `{result['created_at']}`")
                st.markdown(f"**📊 Tracks Added:** `{result['matched_count']} / {result['total_submitted']}` tracks")
                
                st.link_button("🚀 Open in Spotify", result["playlist_url"], type="primary")

                # Track Breakdown
                if result["matched_tracks"]:
                    st.subheader("Matched Tracks")
                    for t in result["matched_tracks"]:
                        col_img, col_info = st.columns([1, 8])
                        with col_img:
                            if t.get("image_url"):
                                st.image(t["image_url"], width=64)
                        with col_info:
                            st.markdown(f"**[{t['matched_title']}]({t['spotify_url']})**  \n*{t['matched_artist']}* — `{t['album']}`")

                if result["unmatched_songs"]:
                    st.warning(f"Could not find matches for {len(result['unmatched_songs'])} song(s):")
                    for u in result["unmatched_songs"]:
                        st.write(f"• {u.get('raw', '')}")

            except Exception as e:
                status.update(label="❌ Spotify API Policy Restriction", state="error")
                err_str = str(e)
                if "Active premium subscription required" in err_str or "PermissionError" in type(e).__name__:
                    st.error("⚠️ **Spotify Premium Required for Developer Apps**: Spotify's API requires the owner of the Developer App to have an active Spotify Premium subscription.")
                    st.info("💡 **Free Alternatives:**\n- Use **Spotlistr** below (100% free tool that creates Spotify playlists for Free accounts with no keys needed).\n- Or use **Export for Apple Music** below.")
                    st.link_button("🌐 Open Spotlistr (Create on Free Spotify)", "https://www.spotlistr.com/search/textbox", type="primary")
                else:
                    st.error(f"Error: {e}")

# --- EXPORT APPLE MUSIC HANDLER ---
if create_apple:
    try:
        res = apple_service.export_all_formats(song_input, playlist_name=custom_title if custom_title.strip() else None)
        
        st.success(f"🍎 **Apple Music Playlist Exported:** {res['playlist_name']}")
        st.markdown(f"**📅 Timestamp:** `{res['created_at']}`")
        st.markdown(f"**📊 Total Songs:** `{res['total_songs']}`")

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            m3u8_content = Path(res["m3u8_path"]).read_text(encoding="utf-8")
            st.download_button(
                label="📥 Download .M3U8 Playlist",
                data=m3u8_content,
                file_name=Path(res["m3u8_path"]).name,
                mime="audio/x-mpegurl",
                use_container_width=True
            )
        with col_dl2:
            txt_content = Path(res["txt_path"]).read_text(encoding="utf-8")
            st.download_button(
                label="📥 Download Apple Music / iTunes TXT Import",
                data=txt_content,
                file_name=Path(res["txt_path"]).name,
                mime="text/plain",
                use_container_width=True
            )

        st.info("💡 **How to import:** In Apple Music or iTunes on Windows/Mac, go to **File > Library > Import Playlist...** and select either the `.m3u8` or `.txt` file.")
    except Exception as e:
        st.error(f"Error exporting for Apple Music: {e}")
