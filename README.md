# Discord Bot Manager

A simple desktop GUI to run your Discord bot, manage token, and load **Commands** + **Auto Moderators** from folders.

## Features

- **Token box** – paste your bot token
- **Auto-Save** switch (ON/OFF) + manual **Save** → stores token in `config.json`
- **▶ Run / ⏹ Stop** – start or stop the bot
- **↻ Refresh** – rescan folders and hot-reload scripts while the bot is running
- **📂 Refresh Files** – rescan Commands/ & AutoModerators/ lists only
- **System tray** – minimize or close (X) hides to tray (bot keeps running)
- **Tray menu** – Show Window · Run Bot · Stop Bot · Refresh · Exit
- **Start with Windows** – optional; app launches after PC restart (Windows)
- **Commands/** – drop Python command files here (e.g. `ping.py`)
- **AutoModerators/** – drop auto-mod event scripts here (e.g. `antiping.py`)
- **Live Console** – shows load status, commands used, bot logs

## Setup

```bash
cd discord_bot_manager
pip install -r requirements.txt
python main.py
```

1. Create a bot at https://discord.com/developers/applications  
2. Enable **Message Content Intent** (and Members if needed)  
3. Copy the bot token into the Token box  
4. Turn **Auto-Save** ON (or click Save)  
5. Invite the bot to your server with proper permissions  
6. Click **▶ Run**

## Adding commands (slash `/` + prefix)

Commands use **hybrid** so they appear in Discord’s `/` menu **and** work with the prefix (`!`).

Create a file in `Commands/`, for example `Commands/say.py`:

```python
from discord import app_commands
from discord.ext import commands

class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="say", description="Make the bot say something")
    @app_commands.describe(text="What to say")
    async def say(self, ctx: commands.Context, text: str):
        await ctx.send(text)

async def setup(bot):
    await bot.add_cog(Say(bot))
```

Then click **↻ Refresh** (or restart the bot).  
Slash commands sync automatically on ready and on refresh — type `/` in Discord to see them.

## Adding auto-moderators

Create a file in `AutoModerators/`, for example `AutoModerators/badwords.py`:

```python
from discord.ext import commands

class BadWords(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.banned = {"badword1", "badword2"}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        content = (message.content or "").lower()
        if any(w in content for w in self.banned):
            await message.delete()
            await message.channel.send(f"{message.author.mention} Watch your language.", delete_after=5)

async def setup(bot):
    await bot.add_cog(BadWords(bot))
```

## Included examples

| Folder            | File          | What it does                          |
|-------------------|---------------|---------------------------------------|
| Commands          | ping.py       | `/ping` and `!ping` – latency         |
| Commands          | hello.py      | `/hello` and `!hello [name]`          |
| AutoModerators    | antiping.py   | Blocks @everyone / mass mentions      |
| AutoModerators    | antilink.py   | Blocks links for non-mods             |

Default prefix is `!` (changeable in `config.json`).

## Notes

- Token is saved locally in `config.json` – never share this file.
- Scripts must define `async def setup(bot)`.
- Hot-reload removes all cogs and reloads both folders.
- Requires Python 3.10+.
