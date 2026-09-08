import os
import sys
import threading
import webbrowser
import subprocess
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from config import Config, BASE_DIR
from parser import parse_songs_from_text, get_creation_timestamp, format_playlist_meta
from spotify_service import SpotifyService
from apple_music_service import AppleMusicService

class NotepadPlaylistGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Notepad to Spotify & Apple Music Playlist Creator")
        self.geometry("900x740")
        self.minsize(780, 600)

        # Services
        self.spotify_service = SpotifyService()
        self.apple_service = AppleMusicService()

        # State
        self.is_processing = False
        self.created_playlist_url = None

        self._init_styles()
        self._build_ui()
        self._start_clock()

    def _init_styles(self):
        self.style = ttk.Style(self)
        # Use clam or default
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Colors
        self.bg_color = "#121212"
        self.card_bg = "#1e1e1e"
        self.text_color = "#ffffff"
        self.accent_green = "#1DB954" # Spotify Green
        self.accent_apple = "#fc3c44" # Apple Music Pink/Red
        self.muted_text = "#b3b3b3"

        self.configure(bg=self.bg_color)

        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("Card.TFrame", background=self.card_bg)
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.text_color)
        self.style.configure("Sub.TLabel", font=("Segoe UI", 9), foreground=self.muted_text)
        self.style.configure("Clock.TLabel", font=("Segoe UI", 10, "bold"), foreground=self.accent_green)

        self.style.configure("Spotify.TButton", font=("Segoe UI", 11, "bold"), background=self.accent_green, foreground="#000000", borderwidth=0)
        self.style.map("Spotify.TButton", background=[("active", "#1ed760")])

        self.style.configure("Apple.TButton", font=("Segoe UI", 11, "bold"), background=self.accent_apple, foreground="#ffffff", borderwidth=0)
        self.style.map("Apple.TButton", background=[("active", "#ff535a")])

        self.style.configure("Secondary.TButton", font=("Segoe UI", 9), background="#2e2e2e", foreground="#ffffff")

    def _build_ui(self):
        main_container = ttk.Frame(self, padding="15")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Header Frame
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_lbl = ttk.Label(header_frame, text="🎵 Notepad Playlist Creator", style="Header.TLabel")
        title_lbl.pack(side=tk.LEFT)

        settings_btn = ttk.Button(header_frame, text="⚙️ Spotify API Settings", style="Secondary.TButton", command=self._open_settings)
        settings_btn.pack(side=tk.RIGHT, padx=5)

        open_np_btn = ttk.Button(header_frame, text="📄 Open in Windows Notepad", style="Secondary.TButton", command=self._open_in_windows_notepad)
        open_np_btn.pack(side=tk.RIGHT, padx=5)

        # Clock & Live Timestamp Banner
        clock_frame = ttk.Frame(main_container, style="Card.TFrame", padding="8")
        clock_frame.pack(fill=tk.X, pady=(0, 10))

        self.clock_lbl = ttk.Label(clock_frame, text="🕒 Current Time: ...", style="Clock.TLabel", background=self.card_bg)
        self.clock_lbl.pack(side=tk.LEFT)

        self.tagline_lbl = ttk.Label(clock_frame, text="• This timestamp will be automatically tagged to your playlist title & description", style="Sub.TLabel", background=self.card_bg)
        self.tagline_lbl.pack(side=tk.LEFT, padx=10)

        # Split pane / Main Content
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Left Column: Notepad Text Box
        left_col = ttk.Frame(content_frame)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        np_header = ttk.Frame(left_col)
        np_header.pack(fill=tk.X, pady=(0, 5))

        np_title = ttk.Label(np_header, text="📝 Paste Songs Here (One per line):", font=("Segoe UI", 10, "bold"))
        np_title.pack(side=tk.LEFT)

        paste_btn = ttk.Button(np_header, text="📋 Paste Clipboard", style="Secondary.TButton", command=self._paste_clipboard)
        paste_btn.pack(side=tk.RIGHT, padx=2)

        sample_btn = ttk.Button(np_header, text="💡 Load Sample Songs", style="Secondary.TButton", command=self._load_sample_songs)
        sample_btn.pack(side=tk.RIGHT, padx=2)

        clear_btn = ttk.Button(np_header, text="🧹 Clear", style="Secondary.TButton", command=self._clear_text)
        clear_btn.pack(side=tk.RIGHT, padx=2)

        # Text Area with Scrollbar (styled like notepad)
        text_frame = ttk.Frame(left_col)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.text_area = tk.Text(
            text_frame,
            wrap=tk.WORD,
            bg="#242424",
            fg="#ffffff",
            insertbackground="#ffffff",
            selectbackground="#404040",
            font=("Consolas", 11),
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.config(yscrollcommand=scrollbar.set)

        # Right Column: Controls & Output log
        right_col = ttk.Frame(content_frame, width=360)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(8, 0))
        right_col.pack_propagate(False)

        # Options Box
        options_box = ttk.LabelFrame(right_col, text="Playlist Settings", padding="10")
        options_box.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(options_box, text="Playlist Title (Optional override):").pack(anchor=tk.W)
        self.name_entry = ttk.Entry(options_box)
        self.name_entry.pack(fill=tk.X, pady=(2, 8))
        self.name_entry.insert(0, "Notepad Playlist (Auto-dated)")

        self.is_public_var = tk.BooleanVar(value=True)
        self.public_chk = ttk.Checkbutton(options_box, text="Public Playlist (Spotify)", variable=self.is_public_var)
        self.public_chk.pack(anchor=tk.W, pady=(0, 5))

        # Action Buttons
        actions_frame = ttk.Frame(right_col)
        actions_frame.pack(fill=tk.X, pady=(0, 10))

        self.spotify_btn = ttk.Button(
            actions_frame,
            text="🟢 Create Spotify Playlist",
            style="Spotify.TButton",
            command=self._on_create_spotify_click
        )
        self.spotify_btn.pack(fill=tk.X, pady=4, ipady=6)

        self.apple_btn = ttk.Button(
            actions_frame,
            text="🍎 Export for Apple Music",
            style="Apple.TButton",
            command=self._on_export_apple_click
        )
        self.apple_btn.pack(fill=tk.X, pady=4, ipady=6)

        # Progress bar
        self.prog_bar = ttk.Progressbar(right_col, mode="determinate")
        self.prog_bar.pack(fill=tk.X, pady=(0, 5))

        # Status & Results log
        ttk.Label(right_col, text="Activity Log & Matched Tracks:").pack(anchor=tk.W)
        log_frame = ttk.Frame(right_col)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_frame,
            wrap=tk.WORD,
            bg="#181818",
            fg="#cccccc",
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            state=tk.DISABLED
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)

        # Footer Frame with link
        footer_frame = ttk.Frame(main_container)
        footer_frame.pack(fill=tk.X, pady=(5, 0))

        self.status_lbl = ttk.Label(footer_frame, text="Ready. Paste songs and click Create.", style="Sub.TLabel")
        self.status_lbl.pack(side=tk.LEFT)

        self.open_url_btn = ttk.Button(
            footer_frame,
            text="🌐 Open Created Playlist in Browser",
            style="Secondary.TButton",
            state=tk.DISABLED,
            command=self._open_created_url
        )
        self.open_url_btn.pack(side=tk.RIGHT)

    def _start_clock(self):
        def update():
            now = datetime.now()
            self.clock_lbl.config(text=f"🕒 Current Time: {now.strftime('%A, %B %d, %Y - %I:%M:%S %p')}")
            self.after(1000, update)
        update()

    def _log(self, message: str, tag: str = None):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _paste_clipboard(self):
        try:
            clipboard_text = self.clipboard_get()
            self.text_area.insert(tk.INSERT, clipboard_text)
        except Exception as e:
            messagebox.showwarning("Clipboard", "Clipboard is empty or does not contain text.")

    def _clear_text(self):
        self.text_area.delete("1.0", tk.END)

    def _load_sample_songs(self):
        samples = (
            "Blinding Lights - The Weeknd\n"
            "Shape of You - Ed Sheeran\n"
            "Bohemian Rhapsody - Queen\n"
            "Stay by The Kid LAROI & Justin Bieber\n"
            "Levitating - Dua Lipa\n"
            "As It Was - Harry Styles\n"
            "Hotel California - Eagles"
        )
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert(tk.END, samples)

    def _open_in_windows_notepad(self):
        target = Path(Config.DEFAULT_NOTEPAD_FILE)
        if not target.exists():
            target.write_text(self.text_area.get("1.0", tk.END).strip() or "Paste songs here...\n", encoding="utf-8")
        try:
            subprocess.Popen(["notepad.exe", str(target)])
            self._log(f"📄 Opened '{target.name}' in Windows Notepad.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not launch Notepad: {e}")

    def _open_settings(self):
        win = tk.Toplevel(self)
        win.title("Spotify API Credentials")
        win.geometry("500x320")
        win.configure(bg=self.bg_color)
        win.transient(self)
        win.grab_set()

        frame = ttk.Frame(win, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="🔑 Configure Spotify API", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        ttk.Label(frame, text="Get these from your free Spotify Developer Dashboard:\nhttps://developer.spotify.com/dashboard", style="Sub.TLabel").pack(anchor=tk.W, pady=(0, 15))

        ttk.Label(frame, text="Client ID:").pack(anchor=tk.W)
        cid_entry = ttk.Entry(frame)
        cid_entry.pack(fill=tk.X, pady=(0, 10))
        cid_entry.insert(0, Config.SPOTIPY_CLIENT_ID)

        ttk.Label(frame, text="Client Secret:").pack(anchor=tk.W)
        sec_entry = ttk.Entry(frame, show="*")
        sec_entry.pack(fill=tk.X, pady=(0, 10))
        sec_entry.insert(0, Config.SPOTIPY_CLIENT_SECRET)

        ttk.Label(frame, text="Redirect URI (Default: http://127.0.0.1:8888/callback):").pack(anchor=tk.W)
        uri_entry = ttk.Entry(frame)
        uri_entry.pack(fill=tk.X, pady=(0, 15))
        uri_entry.insert(0, Config.SPOTIPY_REDIRECT_URI)

        def save_and_close():
            cid = cid_entry.get().strip()
            sec = sec_entry.get().strip()
            uri = uri_entry.get().strip() or "http://127.0.0.1:8888/callback"
            if not cid or not sec:
                messagebox.showerror("Validation", "Both Client ID and Client Secret are required.", parent=win)
                return
            Config.save_spotify_credentials(cid, sec, uri)
            self.spotify_service = SpotifyService()
            messagebox.showinfo("Saved", "Spotify credentials saved successfully!", parent=win)
            win.destroy()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Save Credentials", style="Spotify.TButton", command=save_and_close).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", style="Secondary.TButton", command=win.destroy).pack(side=tk.RIGHT)

    def _on_create_spotify_click(self):
        if self.is_processing:
            return

        raw_text = self.text_area.get("1.0", tk.END).strip()
        songs = parse_songs_from_text(raw_text)

        if not songs:
            messagebox.showwarning("Empty List", "Please paste or type at least one song.")
            return

        if not self.spotify_service.is_configured():
            res = messagebox.askyesno(
                "Spotify Setup Required",
                "Spotify credentials have not been configured yet.\n\nWould you like to enter your Spotify Client ID and Secret now?"
            )
            if res:
                self._open_settings()
            return

        self.is_processing = True
        self.spotify_btn.config(state=tk.DISABLED)
        self.apple_btn.config(state=tk.DISABLED)
        self.prog_bar["value"] = 0
        self.status_lbl.config(text="Creating Spotify playlist...")
        self._log("\n" + "=" * 40)
        self._log("🎵 Starting Spotify playlist creation...")

        custom_name = self.name_entry.get().strip()
        if "Auto-dated" in custom_name:
            custom_name = None

        thread = threading.Thread(
            target=self._run_spotify_creation,
            args=(songs, custom_name, self.is_public_var.get()),
            daemon=True
        )
        thread.start()

    def _run_spotify_creation(self, songs, custom_name, is_public):
        total = len(songs)

        def progress_cb(idx, tot, song, match):
            pct = int((idx / tot) * 100)
            self.prog_bar["value"] = pct
            q = song.get("query", "")
            if match:
                self._log(f"✅ [{idx}/{tot}] {match['name']} - {match['artist']}")
            else:
                self._log(f"⚠️ [{idx}/{tot}] Not found: '{q}'")

        try:
            res = self.spotify_service.create_playlist_from_songs(
                songs=songs,
                playlist_name=custom_name,
                is_public=is_public,
                on_progress=progress_cb
            )

            self.created_playlist_url = res.get("playlist_url")
            self._log("\n" + "🎉" * 20)
            self._log(f"🎉 PLAYLIST CREATED!")
            self._log(f"📌 Name: {res['playlist_name']}")
            self._log(f"🕒 Created At: {res['created_at']}")
            self._log(f"📊 Added: {res['matched_count']}/{res['total_submitted']} tracks")
            self._log(f"🔗 Link: {self.created_playlist_url}")
            self._log("🎉" * 20 + "\n")

            self.status_lbl.config(text=f"Done! Created at {res['timestamp_info']['formatted_time']}.")
            self.open_url_btn.config(state=tk.NORMAL)

            # Auto-open browser
            if self.created_playlist_url:
                webbrowser.open(self.created_playlist_url)

        except Exception as e:
            err_msg = str(e)
            self._log(f"\n❌ Spotify Error: {err_msg}")
            if "Active premium subscription required" in err_msg or "PermissionError" in type(e).__name__:
                # Copy songs to clipboard
                try:
                    songs_text = "\n".join([s.get("query", s.get("raw", "")) for s in songs])
                    self.clipboard_clear()
                    self.clipboard_append(songs_text)
                except Exception:
                    pass

                ask_open = messagebox.askyesno(
                    "Spotify Premium Required",
                    "Spotify requires the Developer App owner to have an active Spotify Premium subscription.\n\n"
                    "Good news: Your songs have been copied to your clipboard!\n\n"
                    "Would you like to open Spotlistr (100% Free tool) to create your playlist on Spotify without Premium?"
                )
                if ask_open:
                    webbrowser.open("https://www.spotlistr.com/search/textbox")
            else:
                messagebox.showerror("Spotify Error", err_msg)
            self.status_lbl.config(text="Failed to create playlist.")

        finally:
            self.is_processing = False
            self.spotify_btn.config(state=tk.NORMAL)
            self.apple_btn.config(state=tk.NORMAL)

    def _on_export_apple_click(self):
        raw_text = self.text_area.get("1.0", tk.END).strip()
        songs = parse_songs_from_text(raw_text)

        if not songs:
            messagebox.showwarning("Empty List", "Please paste or type at least one song.")
            return

        try:
            custom_name = self.name_entry.get().strip()
            if "Auto-dated" in custom_name:
                custom_name = None

            res = self.apple_service.export_all_formats(raw_text, playlist_name=custom_name)

            self._log("\n" + "=" * 40)
            self._log(f"🍎 Apple Music Export Ready!")
            self._log(f"📌 Name: {res['playlist_name']}")
            self._log(f"🕒 Timestamp: {res['created_at']}")
            self._log(f"📁 M3U8 File: {res['m3u8_path']}")
            self._log(f"📁 Apple Music TXT: {res['txt_path']}")
            self._log("=" * 40 + "\n")

            # Open folder in Windows File Explorer
            export_dir = str(Path(res['m3u8_path']).parent)
            if sys.platform == "win32":
                subprocess.Popen(["explorer.exe", export_dir])

            messagebox.showinfo(
                "Apple Music Export",
                f"Exported {res['total_songs']} songs with timestamp {res['created_at']}!\n\n"
                f"Files created in:\n{export_dir}\n\n"
                "To import into Apple Music/iTunes: File -> Library -> Import Playlist and select the generated file."
            )
            self.status_lbl.config(text=f"Exported for Apple Music at {res['timestamp_info']['formatted_time']}.")

        except Exception as e:
            messagebox.showerror("Apple Music Error", str(e))

    def _open_created_url(self):
        if self.created_playlist_url:
            webbrowser.open(self.created_playlist_url)

if __name__ == "__main__":
    app = NotepadPlaylistGUI()
    app.mainloop()
