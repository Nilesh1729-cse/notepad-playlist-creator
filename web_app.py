import os
import time
from datetime import datetime
from pathlib import Path
import streamlit as st

from config import Config, BASE_DIR
from parser import parse_songs_from_text, get_creation_timestamp, format_playlist_meta
from spotify_service import SpotifyService, DEFAULT_SCOPE
from apple_music_service import AppleMusicService

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Notepad to Spotify & Apple Music",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for polished look
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
        margin-bottom: 18px;
    }
    .timestamp-box {
        background-color: #1a1a1a;
        border-left: 4px solid #1DB954;
        padding: 12px 18px;
        border-radius: 6px;
        margin-bottom: 20px;
    }
    .user-badge {
        background-color: #181818;
        border: 1px solid #282828;
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# CREDENTIALS & REDIRECT URI RESOLUTION
# -------------------------------------------------------------
def get_active_credentials():
    """Resolves active Spotify credentials from session custom keys, st.secrets, or config."""
    # 1. Check if user provided custom keys in this session
    custom = st.session_state.get("custom_spotify_keys")
    if custom and custom.get("client_id") and custom.get("client_secret"):
        return custom["client_id"], custom["client_secret"], custom.get("redirect_uri", Config.get_redirect_uri())

    # 2. Check Streamlit Cloud Secrets (st.secrets)
    try:
        if hasattr(st, "secrets"):
            cid = str(st.secrets.get("SPOTIPY_CLIENT_ID", "")).strip()
            sec = str(st.secrets.get("SPOTIPY_CLIENT_SECRET", "")).strip()
            uri = str(st.secrets.get("SPOTIPY_REDIRECT_URI", "")).strip()
            if cid and sec:
                return cid, sec, uri or "http://localhost:8501"
    except Exception:
        pass

    # 3. Fallback to Config / .env
    return Config.get_client_id(), Config.get_client_secret(), Config.get_redirect_uri()

raw_client_id, raw_client_secret, raw_redirect_uri = get_active_credentials()

# Trailing slash preference in session
if "use_trailing_slash" not in st.session_state:
    st.session_state["use_trailing_slash"] = False

# Compute active redirect URI
base_uri = raw_redirect_uri.strip().rstrip("/")
if st.session_state.get("override_redirect_uri"):
    active_redirect_uri = st.session_state["override_redirect_uri"].strip()
else:
    active_redirect_uri = (base_uri + "/") if st.session_state["use_trailing_slash"] else base_uri

client_id = raw_client_id
client_secret = raw_client_secret
redirect_uri = active_redirect_uri

# -------------------------------------------------------------
# MULTI-TENANT OAUTH SESSION MANAGEMENT
# -------------------------------------------------------------
# Check for OAuth errors from Spotify (e.g. user cancelled)
query_error = st.query_params.get("error")
if query_error:
    st.error(f"Spotify authentication returned an error: {query_error}")
    st.query_params.clear()

# Check for OAuth callback code from Spotify in URL query parameters
query_code = st.query_params.get("code")
if query_code:
    with st.spinner("Connecting to your Spotify account..."):
        try:
            token_data = SpotifyService.exchange_code_for_token(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                code=query_code
            )
            st.session_state["spotify_token"] = token_data

            # Fetch user profile immediately
            sp_temp = SpotifyService(auth_token=token_data["access_token"])
            profile = sp_temp.get_current_user_profile()
            st.session_state["user_profile"] = profile

            # Clear query params so refreshing the browser doesn't re-trigger
            st.query_params.clear()
            st.success("Connected successfully!")
            st.rerun()
        except Exception as e:
            err_text = str(e)
            if "The user is not registered for this application" in err_text or "not registered" in err_text.lower():
                st.error("⚠️ **Spotify Development Mode Access Restriction**")
                st.info(
                    "Spotify apps in **Development Mode** only allow users who have been added to the app's whitelist.\n\n"
                    "**How to get access in 30 seconds:**\n"
                    "1. Ask the app owner to add your Spotify email under **User Management** in their [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).\n"
                    "2. Or, expand **'Use Your Own Spotify Keys'** in the left sidebar to connect using your own Spotify Developer App."
                )
            else:
                st.error(f"Failed to authenticate with Spotify: {e}")
            st.query_params.clear()

# Token automatic refresh check
token_info = st.session_state.get("spotify_token")
if token_info:
    # Refresh if expiring within 60 seconds
    if time.time() >= token_info.get("expires_at", 0) - 60:
        try:
            new_token = SpotifyService.refresh_user_token(
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=token_info["refresh_token"]
            )
            st.session_state["spotify_token"] = new_token
            token_info = new_token
        except Exception as e:
            st.warning("Session expired. Please log in again.")
            st.session_state.pop("spotify_token", None)
            st.session_state.pop("user_profile", None)
            token_info = None

# Initialize Spotify client with this visitor's private session token
user_spotify_service = SpotifyService(auth_token=token_info["access_token"]) if token_info else None
apple_service = AppleMusicService()

# -------------------------------------------------------------
# SIDEBAR: ACCOUNT & SETTINGS
# -------------------------------------------------------------
with st.sidebar:
    st.image("https://storage.googleapis.com/pr-newsroom-wp/1/2023/05/Spotify_Primary_Logo_RGB_Green.png", width=130)
    st.title("🎵 Account & Settings")

    user_profile = st.session_state.get("user_profile")
    if token_info and user_profile:
        st.markdown('<div class="user-badge">', unsafe_allow_html=True)
        img_url = user_profile["images"][0]["url"] if user_profile.get("images") else None
        if img_url:
            st.image(img_url, width=54)
        st.markdown(f"**Logged in as:**  \n**{user_profile['display_name']}** (`{user_profile['id']}`)")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("🚪 Log Out of Spotify", use_container_width=True):
            st.session_state.pop("spotify_token", None)
            st.session_state.pop("user_profile", None)
            st.rerun()
    else:
        st.info("👋 **Not connected.** Log in below or in the main page to create Spotify playlists.")
        if client_id and client_secret:
            auth_url = SpotifyService.get_oauth_url(client_id=client_id, redirect_uri=redirect_uri)
            st.link_button("🟢 Log In with Spotify", auth_url, type="primary", use_container_width=True)

        # Redirect URI Diagnostic helper
        with st.expander("🛠️ Spotify Redirect URI Helper", expanded=True):
            st.markdown("**Your Active Redirect URI is:**")
            st.code(redirect_uri, language="text")

            # Toggle trailing slash
            slash_state = st.checkbox("Add trailing slash ( / ) to URI", value=st.session_state.get("use_trailing_slash", False))
            if slash_state != st.session_state.get("use_trailing_slash", False):
                st.session_state["use_trailing_slash"] = slash_state
                st.rerun()

            st.caption("💡 **Tip:** In Spotify Developer Dashboard > Settings > Redirect URIs, click **Add**, then scroll to the bottom and click **Save**.")

    st.divider()

    # Expandable: Custom Keys for any user (Multi-tenant fallback)
    with st.expander("🔑 Use Your Own Spotify Keys (Optional)"):
        st.caption(
            "If the default app hits Spotify's quota, or if you prefer using your own Spotify Developer App, "
            "you can enter your keys here. They remain strictly in your private session."
        )
        custom_cid = st.text_input("Custom Client ID", value=st.session_state.get("custom_spotify_keys", {}).get("client_id", ""))
        custom_sec = st.text_input("Custom Client Secret", type="password", value=st.session_state.get("custom_spotify_keys", {}).get("client_secret", ""))
        custom_uri = st.text_input("Custom Redirect URI", value=st.session_state.get("custom_spotify_keys", {}).get("redirect_uri", redirect_uri))

        col_save, col_reset = st.columns(2)
        with col_save:
            if st.button("Apply Keys", use_container_width=True):
                if custom_cid.strip() and custom_sec.strip():
                    st.session_state["custom_spotify_keys"] = {
                        "client_id": custom_cid.strip(),
                        "client_secret": custom_sec.strip(),
                        "redirect_uri": custom_uri.strip()
                    }
                    st.success("Custom keys applied to your session!")
                    st.rerun()
                else:
                    st.error("Enter both ID and Secret.")
        with col_reset:
            if st.button("Reset to Default", use_container_width=True):
                st.session_state.pop("custom_spotify_keys", None)
                st.rerun()

    st.divider()
    st.markdown("### 🍎 Apple Music & Free Tools")
    st.caption("No account connection or keys required for Apple Music exports or Spotlistr.")

# -------------------------------------------------------------
# MAIN CONTENT AREA
# -------------------------------------------------------------
st.markdown('<div class="main-title">🎵 Notepad to Spotify & Apple Music</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Paste songs from Notepad to instantly create a playlist tagged with the exact creation date & time.</div>', unsafe_allow_html=True)

# Live creation timestamp banner
ts_now = get_creation_timestamp()
st.markdown(f"""
<div class="timestamp-box">
    <b>🕒 Current Timestamp:</b> {ts_now['formatted_full']}<br>
    <span style="color: #999; font-size: 0.9rem;">This date and time will be automatically recorded into your playlist title and description upon creation.</span>
</div>
""", unsafe_allow_html=True)

# Main columns: Left for Notepad, Right for Settings
col_input, col_meta = st.columns([2, 1])

with col_meta:
    st.subheader("Playlist Settings")
    custom_title = st.text_input("Playlist Name (optional)", placeholder=f"Notepad Playlist - {ts_now['title_timestamp']}")
    is_public = st.checkbox("Make Playlist Public on Spotify", value=True)

    st.markdown("#### Quick Tools")
    load_sample = st.button("💡 Load Sample Songs", use_container_width=True)
    uploaded_file = st.file_uploader("📂 Upload a .txt Notepad File", type=["txt"])

with col_input:
    st.subheader("📝 Notepad (Paste Songs Here)")

    if "notepad_content" not in st.session_state:
        st.session_state["notepad_content"] = ""

    if load_sample:
        st.session_state["notepad_content"] = (
            "The Weeknd - Blinding Lights\n"
            "Queen - Bohemian Rhapsody\n"
            "Ed Sheeran - Shape of You\n"
            "The Kid LAROI & Justin Bieber - Stay\n"
            "Dua Lipa - Levitating\n"
            "Harry Styles - As It Was\n"
            "Eagles - Hotel California"
        )
        st.rerun()

    if uploaded_file is not None:
        try:
            st.session_state["notepad_content"] = uploaded_file.read().decode("utf-8")
        except Exception:
            st.session_state["notepad_content"] = uploaded_file.read().decode("latin-1")
        st.rerun()

    song_input = st.text_area(
        label="Song list",
        value=st.session_state["notepad_content"],
        height=300,
        placeholder="Paste songs one per line, e.g.:\n1. The Weeknd - Blinding Lights\n2. Shape of You by Ed Sheeran\n3. Bohemian Rhapsody - Queen",
        label_visibility="collapsed"
    )
    # Persist typed/pasted content
    st.session_state["notepad_content"] = song_input

# Parse songs
parsed_songs = parse_songs_from_text(song_input)

if song_input.strip():
    st.caption(f"Detected **{len(parsed_songs)}** unique song(s) ready to create.")

# -------------------------------------------------------------
# ACTION BUTTONS & HANDLERS
# -------------------------------------------------------------
btn_col1, btn_col2 = st.columns(2)

with btn_col1:
    if token_info:
        create_spotify = st.button(
            f"🟢 Create Spotify Playlist ({len(parsed_songs)} songs)",
            type="primary",
            use_container_width=True,
            disabled=not bool(parsed_songs)
        )
    else:
        create_spotify = False
        if client_id and client_secret:
            auth_url = SpotifyService.get_oauth_url(client_id=client_id, redirect_uri=redirect_uri)
            st.link_button(
                "🟢 Log In to Spotify to Create Playlist",
                auth_url,
                type="primary",
                use_container_width=True
            )
        else:
            st.warning("Spotify Client ID / Secret not set in secrets or environment.")

with btn_col2:
    create_apple = st.button(
        f"🍎 Export for Apple Music ({len(parsed_songs)} songs)",
        use_container_width=True,
        disabled=not bool(parsed_songs)
    )

# --- SPOTIFY PLAYLIST CREATION ---
if create_spotify and user_spotify_service:
    with st.status("🎵 Creating playlist on your Spotify account...", expanded=True) as status:
        st.write(f"Captured creation timestamp: **{ts_now['formatted_full']}**...")
        prog_bar = st.progress(0)
        status_text = st.empty()

        def progress_callback(idx, total, song, match):
            prog_bar.progress(idx / total)
            q = song.get("query", "")
            if match:
                status_text.text(f"[{idx}/{total}] ✅ Found: {match['name']} by {match['artist']}")
            else:
                status_text.text(f"[{idx}/{total}] ⚠️ Not found: {q}")

        try:
            result = user_spotify_service.create_playlist_from_songs(
                songs=parsed_songs,
                playlist_name=custom_title.strip() if custom_title.strip() else None,
                is_public=is_public,
                on_progress=progress_callback
            )
            status.update(label="🎉 Playlist created successfully!", state="complete", expanded=False)

            st.balloons()
            st.success(f"🎉 **Playlist Created:** [{result['playlist_name']}]({result['playlist_url']})")
            st.markdown(f"**📅 Timestamp:** `{result['created_at']}`")
            st.markdown(f"**📊 Tracks Added:** `{result['matched_count']} / {result['total_submitted']}`")

            st.link_button("🚀 Open in Spotify", result["playlist_url"], type="primary")

            # Track Breakdown
            if result["matched_tracks"]:
                st.subheader("Matched Tracks")
                for t in result["matched_tracks"]:
                    col_img, col_info = st.columns([1, 8])
                    with col_img:
                        if t.get("image_url"):
                            st.image(t["image_url"], width=60)
                    with col_info:
                        st.markdown(f"**[{t['matched_title']}]({t['spotify_url']})**  \n*{t['matched_artist']}* — `{t['album']}`")

            if result["unmatched_songs"]:
                st.warning(f"Could not find matches for {len(result['unmatched_songs'])} song(s):")
                for u in result["unmatched_songs"]:
                    st.write(f"• {u.get('raw', '')}")

        except Exception as e:
            status.update(label="❌ Failed to create playlist", state="error")
            err_str = str(e)
            if "Active premium subscription required" in err_str:
                st.error("⚠️ **Spotify Billing Sync Delay**: Spotify's API gateway still reports that your app owner account needs an active Premium subscription. If you just upgraded or activated Premium recently, Spotify's Developer backend takes between 30 minutes to a couple of hours to update your billing status.")
                st.info("💡 **In the meantime, you can use these free alternatives:**\n- Use **Spotlistr** below (100% free tool for Spotify accounts).\n- Or use **Export for Apple Music**.")
                st.link_button("🌐 Open Spotlistr (Create on Spotify)", "https://www.spotlistr.com/search/textbox", type="primary")
            else:
                st.error(f"❌ **Spotify API Error:** {err_str}")
                with st.expander("🔍 Show Detailed Error Diagnostics"):
                    import traceback
                    st.code(traceback.format_exc())

# --- APPLE MUSIC EXPORT ---
if create_apple:
    try:
        res = apple_service.export_all_formats(song_input, playlist_name=custom_title.strip() if custom_title.strip() else None)

        st.success(f"🍎 **Apple Music Playlist Ready:** {res['playlist_name']}")
        st.markdown(f"**📅 Creation Timestamp:** `{res['created_at']}`")
        st.markdown(f"**📊 Total Songs:** `{res['total_songs']}`")

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            m3u8_content = Path(res["m3u8_path"]).read_text(encoding="utf-8")
            st.download_button(
                label="📥 Download .M3U8 Playlist File",
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

        st.info("💡 **How to import:** In Apple Music or iTunes on Windows/Mac, go to **File > Library > Import Playlist...** and select either file.")
    except Exception as e:
        st.error(f"Error exporting for Apple Music: {e}")
