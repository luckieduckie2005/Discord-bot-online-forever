"""
Discord bot core – loads Commands/ and AutoModerators/ as cogs.
Runs in a background thread so the GUI stays responsive.
"""

import os
import sys
import asyncio
import importlib.util
import traceback
from pathlib import Path
from typing import Callable, Optional

import discord
from discord.ext import commands


BASE_DIR = Path(__file__).resolve().parent
COMMANDS_DIR = BASE_DIR / "Commands"
AUTOMOD_DIR = BASE_DIR / "AutoModerators"


class BotManager:
    def __init__(
        self,
        log_callback: Callable[[str], None],
        on_ready_callback: Optional[Callable[[], None]] = None,
        on_stop_callback: Optional[Callable[[], None]] = None,
        prefix: str = "!",
    ):
        self.log = log_callback
        self.on_ready_cb = on_ready_callback
        self.on_stop_cb = on_stop_callback
        self.prefix = prefix
        self.bot: Optional[commands.Bot] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._task = None
        self.running = False
        self.loaded_commands: list[str] = []
        self.loaded_automods: list[str] = []

    def _create_bot(self) -> commands.Bot:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        bot = commands.Bot(command_prefix=self.prefix, intents=intents)

        @bot.event
        async def on_ready():
            self.log(f"[BOT] Logged in as {bot.user} (ID: {bot.user.id})")
            self.log(f"[BOT] Connected to {len(bot.guilds)} guild(s)")
            self.log(f"[BOT] Prefix: {self.prefix}  |  Slash: /commands")
            # Sync slash commands so they show in Discord's / menu
            try:
                synced = await bot.tree.sync()
                self.log(f"[SLASH] Synced {len(synced)} slash command(s): "
                         + ", ".join(f"/{c.name}" for c in synced))
            except Exception as e:
                self.log(f"[ERROR] Failed to sync slash commands: {e}")
            if self.on_ready_cb:
                self.on_ready_cb()

        @bot.event
        async def on_command(ctx):
            self.log(f"[CMD] {ctx.author} used {self.prefix}{ctx.command} in #{ctx.channel}")

        @bot.event
        async def on_command_error(ctx, error):
            if isinstance(error, commands.CommandNotFound):
                return
            self.log(f"[ERROR] Command error: {error}")

        @bot.tree.error
        async def on_app_command_error(interaction: discord.Interaction, error: Exception):
            self.log(f"[ERROR] Slash command error: {error}")
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(
                        f"Error: {error}", ephemeral=True
                    )
                except Exception:
                    pass

        return bot

    def _load_module_from_file(self, filepath: Path, module_name: str):
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load {filepath}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    async def _load_folder(self, folder: Path, label: str) -> list[str]:
        loaded = []
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
            self.log(f"[LOAD] Created missing folder: {folder.name}/")
            return loaded

        py_files = sorted(folder.glob("*.py"))
        if not py_files:
            self.log(f"[LOAD] No .py files in {folder.name}/")
            return loaded

        for path in py_files:
            name = path.stem
            module_name = f"dyn_{folder.name}_{name}"
            try:
                # Remove old module if reloading
                if module_name in sys.modules:
                    del sys.modules[module_name]

                module = self._load_module_from_file(path, module_name)
                if not hasattr(module, "setup"):
                    self.log(f"[WARN] {folder.name}/{path.name} has no setup() – skipped")
                    continue

                await module.setup(self.bot)
                loaded.append(path.name)
                self.log(f"[LOAD] ✓ {label}: {path.name}")
            except Exception as e:
                self.log(f"[ERROR] Failed to load {folder.name}/{path.name}: {e}")
                self.log(traceback.format_exc())
        return loaded

    async def load_all(self):
        self.loaded_commands = await self._load_folder(COMMANDS_DIR, "Command")
        self.loaded_automods = await self._load_folder(AUTOMOD_DIR, "AutoMod")
        self.log(
            f"[LOAD] Done – {len(self.loaded_commands)} command(s), "
            f"{len(self.loaded_automods)} auto-mod(s)"
        )

    async def _start_async(self, token: str):
        self.bot = self._create_bot()
        self.running = True
        try:
            await self.load_all()
            self.log("[BOT] Connecting…")
            await self.bot.start(token)
        except discord.LoginFailure:
            self.log("[ERROR] Invalid token – login failed.")
        except Exception as e:
            self.log(f"[ERROR] Bot crashed: {e}")
            self.log(traceback.format_exc())
        finally:
            self.running = False
            if self.bot and not self.bot.is_closed():
                await self.bot.close()
            self.log("[BOT] Stopped.")
            if self.on_stop_cb:
                self.on_stop_cb()

    def start(self, token: str):
        if self.running:
            self.log("[WARN] Bot is already running.")
            return

        def runner():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self._start_async(token))
            finally:
                try:
                    self._loop.close()
                except Exception:
                    pass
                self._loop = None

        import threading
        t = threading.Thread(target=runner, daemon=True)
        t.start()
        self.log("[BOT] Starting in background thread…")

    def stop(self):
        if not self.running or not self.bot or not self._loop:
            self.log("[WARN] Bot is not running.")
            return

        async def _close():
            await self.bot.close()

        try:
            fut = asyncio.run_coroutine_threadsafe(_close(), self._loop)
            fut.result(timeout=8)
        except Exception as e:
            self.log(f"[WARN] Stop error: {e}")
        self.running = False
        self.log("[BOT] Stop requested.")

    def refresh_folders(self):
        """Hot-reload Commands & AutoModerators while bot is running."""
        if not self.running or not self.bot or not self._loop:
            self.log("[WARN] Start the bot first to refresh (or just press Run).")
            return

        async def _reload():
            # Unload existing cogs that came from our folders
            to_remove = [
                name
                for name, cog in list(self.bot.cogs.items())
            ]
            for name in to_remove:
                await self.bot.remove_cog(name)
                self.log(f"[RELOAD] Unloaded cog: {name}")

            await self.load_all()
            # Re-sync slash commands after reload
            try:
                synced = await self.bot.tree.sync()
                self.log(f"[SLASH] Re-synced {len(synced)} slash command(s): "
                         + ", ".join(f"/{c.name}" for c in synced))
            except Exception as e:
                self.log(f"[ERROR] Slash re-sync failed: {e}")
            self.log("[RELOAD] Folders refreshed.")

        try:
            fut = asyncio.run_coroutine_threadsafe(_reload(), self._loop)
            fut.result(timeout=15)
        except Exception as e:
            self.log(f"[ERROR] Refresh failed: {e}")
            self.log(traceback.format_exc())

    def list_folder_files(self) -> dict:
        def scan(folder: Path) -> list[str]:
            if not folder.exists():
                return []
            return sorted(p.name for p in folder.glob("*.py"))

        return {
            "Commands": scan(COMMANDS_DIR),
            "AutoModerators": scan(AUTOMOD_DIR),
        }
