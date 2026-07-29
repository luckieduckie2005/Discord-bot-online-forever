"""
Discord Bot Manager – GUI
- Token box with Auto-Save
- Run / Stop / Refresh / Refresh Files
- System tray: minimize or close → tray icon
- Tray menu: Show, Run, Stop, Refresh, Exit
- Optional: Start with Windows (survives PC restart)
- Join my Discord button
"""

import json
import os
import sys
import threading
import webbrowser
from pathlib import Path
from datetime import datetime

try:
    import customtkinter as ctk
except ImportError:
    print("customtkinter is required. Run:  pip install customtkinter")
    sys.exit(1)

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("pystray and Pillow are required. Run:  pip install pystray Pillow")
    sys.exit(1)

from bot_core import BotManager, BASE_DIR, COMMANDS_DIR, AUTOMOD_DIR

CONFIG_PATH = BASE_DIR / "config.json"
ICON_PATH = BASE_DIR / "tray_icon.png"

# ── Change this to your Discord invite link ──────────────────────────
DISCORD_INVITE = "https://discord.gg/BvYW5DMWNs"


def load_config() -> dict:
    defaults = {
        "token": "",
        "auto_save": True,
        "prefix": "!",
        "start_with_windows": False,
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            defaults.update(data)
        except Exception:
            pass
    return defaults


def save_config(data: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def create_tray_icon_image() -> Image.Image:
    """Generate a simple Discord-style tray icon (purple circle with bot face)."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Discord blurple circle
    draw.ellipse([4, 4, size - 5, size - 5], fill=(88, 101, 242, 255))
    # Simple robot eyes
    draw.ellipse([18, 22, 28, 32], fill=(255, 255, 255, 255))
    draw.ellipse([36, 22, 46, 32], fill=(255, 255, 255, 255))
    # Mouth
    draw.rounded_rectangle([22, 40, 42, 48], radius=4, fill=(255, 255, 255, 255))
    return img


def ensure_tray_icon() -> Image.Image:
    if ICON_PATH.exists():
        try:
            return Image.open(ICON_PATH)
        except Exception:
            pass
    img = create_tray_icon_image()
    try:
        img.save(ICON_PATH)
    except Exception:
        pass
    return img


# ── Windows autostart helpers ────────────────────────────────────────
def _startup_shortcut_path() -> Path | None:
    if sys.platform != "win32":
        return None
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return (
        Path(appdata)
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
        / "DiscordBotManager.lnk"
    )


def set_start_with_windows(enabled: bool) -> bool:
    """Create or remove a Startup folder shortcut (Windows only)."""
    if sys.platform != "win32":
        return False
    target = _startup_shortcut_path()
    if target is None:
        return False

    if not enabled:
        if target.exists():
            try:
                target.unlink()
            except Exception:
                return False
        return True

    # Create .lnk via PowerShell
    script = str(Path(__file__).resolve())
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    if not Path(pythonw).exists():
        pythonw = sys.executable
    workdir = str(BASE_DIR)

    ps = (
        f'$ws = New-Object -ComObject WScript.Shell; '
        f'$s = $ws.CreateShortcut("{target}"); '
        f'$s.TargetPath = "{pythonw}"; '
        f'$s.Arguments = \'"{script}"\'; '
        f'$s.WorkingDirectory = "{workdir}"; '
        f'$s.WindowStyle = 7; '
        f'$s.Description = "Discord Bot Manager"; '
        f"$s.Save()"
    )
    try:
        import subprocess
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            check=True,
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return target.exists()
    except Exception:
        return False


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Discord Bot Manager")
        self.geometry("1000x700")
        self.minsize(820, 580)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.config_data = load_config()
        self._tray_icon: pystray.Icon | None = None
        self._quitting = False
        self._hidden = False

        self.bot_mgr = BotManager(
            log_callback=self.log,
            on_ready_callback=self._on_bot_ready,
            on_stop_callback=self._on_bot_stop,
            prefix=self.config_data.get("prefix", "!"),
        )

        self._build_ui()
        self._load_token_to_ui()
        self.refresh_folder_lists()

        # Close → tray, minimize → tray
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.bind("<Unmap>", self._on_unmap)

        self._start_tray()

        self.log("[UI] Ready – close or minimize sends the app to the system tray.")
        if self.config_data.get("start_with_windows"):
            self.log("[UI] Start with Windows is ON – app will launch after reboot.")

    # ── UI construction ──────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        # ── Top bar: token + controls ────────────────────────────────
        top = ctk.CTkFrame(self, corner_radius=8)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 6))
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text="Bot Token", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, padx=(12, 8), pady=10, sticky="w"
        )

        self.token_box = ctk.CTkTextbox(
            top, height=36, wrap="none", font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.token_box.grid(row=0, column=1, sticky="ew", padx=4, pady=10)
        self.token_box.bind("<KeyRelease>", self._on_token_change)

        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=8, pady=8)

        self.auto_save_var = ctk.BooleanVar(value=self.config_data.get("auto_save", True))
        self.auto_save_btn = ctk.CTkSwitch(
            btn_frame,
            text="Auto-Save",
            variable=self.auto_save_var,
            command=self._toggle_auto_save,
            width=90,
        )
        self.auto_save_btn.pack(side="left", padx=4)

        self.save_btn = ctk.CTkButton(btn_frame, text="Save", width=70, command=self.save_token)
        self.save_btn.pack(side="left", padx=4)

        self.run_btn = ctk.CTkButton(
            btn_frame,
            text="▶ Run",
            width=80,
            fg_color="#1f9d55",
            hover_color="#178a47",
            command=self.toggle_run,
        )
        self.run_btn.pack(side="left", padx=4)

        self.refresh_btn = ctk.CTkButton(
            btn_frame, text="↻ Refresh", width=90, command=self.do_refresh
        )
        self.refresh_btn.pack(side="left", padx=4)

        self.refresh_files_btn = ctk.CTkButton(
            btn_frame,
            text="📂 Refresh Files",
            width=110,
            fg_color="#2c3e50",
            hover_color="#1a252f",
            command=self.do_refresh_files,
        )
        self.refresh_files_btn.pack(side="left", padx=4)

        # ── Join my Discord button ───────────────────────────────────
        self.discord_btn = ctk.CTkButton(
            btn_frame,
            text="Join my Discord",
            width=130,
            fg_color="#5865F2",          # Discord blurple
            hover_color="#4752C4",
            command=self.open_discord,
        )
        self.discord_btn.pack(side="left", padx=4)

        # ── Left panel: folders ──────────────────────────────────────
        left = ctk.CTkFrame(self, corner_radius=8)
        left.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=6)
        left.grid_rowconfigure(1, weight=1)
        left.grid_rowconfigure(3, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left, text="📁 Commands", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        self.cmd_list = ctk.CTkTextbox(
            left, height=140, font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.cmd_list.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.cmd_list.configure(state="disabled")

        ctk.CTkLabel(
            left, text="🛡️ Auto Moderators", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=2, column=0, sticky="w", padx=12, pady=(8, 4))
        self.mod_list = ctk.CTkTextbox(
            left, height=140, font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.mod_list.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.mod_list.configure(state="disabled")

        # Start with Windows toggle
        self.start_win_var = ctk.BooleanVar(
            value=self.config_data.get("start_with_windows", False)
        )
        self.start_win_switch = ctk.CTkSwitch(
            left,
            text="Start with Windows (survive reboot)",
            variable=self.start_win_var,
            command=self._toggle_start_with_windows,
        )
        self.start_win_switch.grid(row=4, column=0, sticky="w", padx=12, pady=(4, 4))
        if sys.platform != "win32":
            self.start_win_switch.configure(state="disabled")
            self.start_win_switch.configure(text="Start with Windows (Windows only)")

        hint = ctk.CTkLabel(
            left,
            text="Drop .py files into Commands/ or AutoModerators/\n"
            "Each file needs:  async def setup(bot)\n"
            "Close / minimize → system tray",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            justify="left",
        )
        hint.grid(row=5, column=0, sticky="w", padx=12, pady=(0, 12))

        # ── Right panel: console ─────────────────────────────────────
        right = ctk.CTkFrame(self, corner_radius=8)
        right.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=6)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(right, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        ctk.CTkLabel(
            header, text="📟 Console", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
        ctk.CTkButton(
            header, text="Clear", width=60, height=24, command=self.clear_console
        ).pack(side="right")

        self.console = ctk.CTkTextbox(
            right, font=ctk.CTkFont(family="Consolas", size=12), wrap="word"
        )
        self.console.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.console.configure(state="disabled")

        self.status = ctk.CTkLabel(
            self, text="Ready – tray icon active", anchor="w", font=ctk.CTkFont(size=12)
        )
        self.status.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 8))

    # ── System tray ──────────────────────────────────────────────────
    def _build_tray_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("Show Window", self._tray_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "▶ Run Bot",
                self._tray_run,
                enabled=lambda item: not self.bot_mgr.running,
            ),
            pystray.MenuItem(
                "⏹ Stop Bot",
                self._tray_stop,
                enabled=lambda item: self.bot_mgr.running,
            ),
            pystray.MenuItem("↻ Refresh", self._tray_refresh),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Exit", self._tray_exit),
        )

    def _start_tray(self):
        icon_img = ensure_tray_icon()

        def run_tray():
            self._tray_icon = pystray.Icon(
                "DiscordBotManager",
                icon_img,
                "Discord Bot Manager",
                self._build_tray_menu(),
            )
            self._tray_icon.run()

        t = threading.Thread(target=run_tray, daemon=True)
        t.start()

    def _update_tray_menu(self):
        if self._tray_icon:
            try:
                self._tray_icon.menu = self._build_tray_menu()
                self._tray_icon.update_menu()
            except Exception:
                pass

    def hide_to_tray(self):
        if self._quitting:
            return
        self.withdraw()
        self._hidden = True
        self.log("[UI] Hidden to system tray. Right-click the tray icon for options.")
        self.status.configure(text="Running in system tray")

    def show_from_tray(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        self._hidden = False
        self.status.configure(
            text="Bot online ✓" if self.bot_mgr.running else "Ready – tray icon active"
        )

    def _on_unmap(self, event):
        # Iconify (minimize) → send to tray instead of taskbar
        if event.widget is self and self.state() == "iconic" and not self._quitting:
            self.after(50, self.hide_to_tray)

    # Tray callbacks (run on tray thread → schedule on UI thread)
    def _tray_show(self, icon=None, item=None):
        self.after(0, self.show_from_tray)

    def _tray_run(self, icon=None, item=None):
        self.after(0, self._tray_do_run)

    def _tray_stop(self, icon=None, item=None):
        self.after(0, self._tray_do_stop)

    def _tray_refresh(self, icon=None, item=None):
        self.after(0, self.do_refresh)

    def _tray_exit(self, icon=None, item=None):
        self.after(0, self.quit_app)

    def _tray_do_run(self):
        if not self.bot_mgr.running:
            self.toggle_run()
            self._update_tray_menu()

    def _tray_do_stop(self):
        if self.bot_mgr.running:
            self.toggle_run()
            self._update_tray_menu()

    def quit_app(self):
        self._quitting = True
        self.log("[UI] Exiting…")
        if self.bot_mgr.running:
            self.bot_mgr.stop()
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
        self.destroy()

    # ── Helpers ──────────────────────────────────────────────────────
    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"

        def _append():
            try:
                self.console.configure(state="normal")
                self.console.insert("end", line)
                self.console.see("end")
                self.console.configure(state="disabled")
            except Exception:
                pass

        self.after(0, _append)

    def clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def _set_list(self, widget: ctk.CTkTextbox, files: list[str]):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        if files:
            widget.insert("end", "\n".join(f"  • {f}" for f in files))
        else:
            widget.insert("end", "  (empty)")
        widget.configure(state="disabled")

    def refresh_folder_lists(self):
        files = self.bot_mgr.list_folder_files()
        self._set_list(self.cmd_list, files["Commands"])
        self._set_list(self.mod_list, files["AutoModerators"])
        self.log(
            f"[UI] Folders scanned – Commands: {len(files['Commands'])}, "
            f"AutoMods: {len(files['AutoModerators'])}"
        )

    def _load_token_to_ui(self):
        token = self.config_data.get("token", "")
        self.token_box.delete("1.0", "end")
        if token:
            self.token_box.insert("1.0", token)
            self.log("[UI] Token loaded from config.json")

    def _get_token(self) -> str:
        return self.token_box.get("1.0", "end").strip()

    def _on_token_change(self, _event=None):
        if self.auto_save_var.get():
            self.save_token(silent=True)

    def _toggle_auto_save(self):
        self.config_data["auto_save"] = self.auto_save_var.get()
        save_config(self.config_data)
        state = "ON" if self.auto_save_var.get() else "OFF"
        self.log(f"[UI] Auto-Save → {state}")
        self.status.configure(text=f"Auto-Save {state}")

    def _toggle_start_with_windows(self):
        enabled = self.start_win_var.get()
        ok = set_start_with_windows(enabled)
        self.config_data["start_with_windows"] = enabled and ok
        save_config(self.config_data)
        if enabled and ok:
            self.log("[UI] Start with Windows → ON (will launch after PC restart)")
            self.status.configure(text="Start with Windows ON")
        elif enabled and not ok:
            self.start_win_var.set(False)
            self.config_data["start_with_windows"] = False
            save_config(self.config_data)
            self.log("[ERROR] Could not create startup shortcut (Windows only / permissions)")
            self.status.configure(text="Start with Windows failed")
        else:
            self.log("[UI] Start with Windows → OFF")
            self.status.configure(text="Start with Windows OFF")

    def save_token(self, silent: bool = False):
        token = self._get_token()
        self.config_data["token"] = token
        self.config_data["auto_save"] = self.auto_save_var.get()
        save_config(self.config_data)
        if not silent:
            self.log("[UI] Token saved to config.json")
            self.status.configure(text="Token saved")
        else:
            self.status.configure(text="Auto-saved")

    def open_discord(self):
        """Open the Discord invite link in the default browser."""
        try:
            webbrowser.open(DISCORD_INVITE)
            self.log(f"[UI] Opening Discord invite: {DISCORD_INVITE}")
            self.status.configure(text="Opened Discord invite")
        except Exception as e:
            self.log(f"[ERROR] Could not open Discord link: {e}")
            self.status.configure(text="Failed to open Discord")

    def toggle_run(self):
        if self.bot_mgr.running:
            self.bot_mgr.stop()
            self.run_btn.configure(
                text="▶ Run", fg_color="#1f9d55", hover_color="#178a47"
            )
            self.status.configure(text="Stopping…")
        else:
            token = self._get_token()
            if not token:
                self.log("[ERROR] Paste your Discord bot token first.")
                self.status.configure(text="No token")
                self.show_from_tray()
                return
            self.save_token(silent=True)
            self.bot_mgr.start(token)
            self.run_btn.configure(
                text="⏹ Stop", fg_color="#c0392b", hover_color="#a93226"
            )
            self.status.configure(text="Starting bot…")
        self._update_tray_menu()

    def do_refresh(self):
        """Rescan folders + hot-reload cogs if bot is running."""
        self.refresh_folder_lists()
        if self.bot_mgr.running:
            self.bot_mgr.refresh_folders()
        else:
            self.log("[UI] Folder lists updated (bot offline – start it to load scripts).")
        self.status.configure(text="Refreshed")

    def do_refresh_files(self):
        """Only rescan Commands/ and AutoModerators/ lists (no cog reload)."""
        self.refresh_folder_lists()
        self.log("[UI] File lists refreshed from disk.")
        self.status.configure(text="Files refreshed")

    def _on_bot_ready(self):
        def ui():
            self.status.configure(text="Bot online ✓")
            self._update_tray_menu()
        self.after(0, ui)

    def _on_bot_stop(self):
        def ui():
            self.run_btn.configure(
                text="▶ Run", fg_color="#1f9d55", hover_color="#178a47"
            )
            self.status.configure(text="Bot offline")
            self._update_tray_menu()
        self.after(0, ui)


if __name__ == "__main__":
    COMMANDS_DIR.mkdir(exist_ok=True)
    AUTOMOD_DIR.mkdir(exist_ok=True)

    app = App()
    app.mainloop()