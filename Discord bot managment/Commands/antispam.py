import discord
from discord.ext import commands
from datetime import datetime, timedelta

# ==========================================
# CONFIG
# ==========================================

OWNER_ID = 1530207060271169638

ROLE_MODERATOR = 1530175947850911764
ROLE_ADMINISTRATOR = 1530178027710058496

# Spam Settings
MESSAGE_LIMIT = 5        # Messages
TIME_LIMIT = 5           # Seconds
TIMEOUT_MINUTES = 10     # Timeout Duration

# ==========================================
# ANTISPAM
# ==========================================

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_messages = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.guild is None:
            return

        if message.author.bot:
            return

        # Ignore Owner
        if message.author.id == OWNER_ID:
            return

        # Ignore Staff
        if any(role.id in [ROLE_MODERATOR, ROLE_ADMINISTRATOR] for role in message.author.roles):
            return

        now = datetime.utcnow()

        user_id = message.author.id

        if user_id not in self.user_messages:
            self.user_messages[user_id] = []

        self.user_messages[user_id].append(now)

        # Remove old messages
        self.user_messages[user_id] = [
            t for t in self.user_messages[user_id]
            if (now - t).total_seconds() <= TIME_LIMIT
        ]

        # Spam detected
        if len(self.user_messages[user_id]) >= MESSAGE_LIMIT:

            # Delete current message
            try:
                await message.delete()
            except:
                pass

            # Timeout user
            try:
                await message.author.timeout(
                    timedelta(minutes=TIMEOUT_MINUTES),
                    reason="Automatic Anti-Spam"
                )
            except:
                pass

            embed = discord.Embed(
                title="🚫 Anti-Spam Activated 🚫",
                description=(
                    f"{message.author.mention} has been automatically timed out.\n\n"
                    f"**Reason:** Spam Detected\n"
                    f"**Timeout:** {TIMEOUT_MINUTES} minutes"
                ),
                color=discord.Color.red()
            )

            warning = await message.channel.send(embed=embed)

            # Delete warning after 10 seconds
            await warning.delete(delay=10)

            # Reset counter
            self.user_messages[user_id] = []

# ==========================================
# LOAD COG
# ==========================================

async def setup(bot):
    await bot.add_cog(AntiSpam(bot))