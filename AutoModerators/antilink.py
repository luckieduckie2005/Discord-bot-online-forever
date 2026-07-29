"""
Anti-link auto moderator (simple example).
Blocks messages containing http/https links for non-mods.
"""

import re
import discord
from discord.ext import commands

LINK_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)


class AntiLink(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.author.guild_permissions.manage_messages:
            return

        if LINK_PATTERN.search(message.content or ""):
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} Links are not allowed here.",
                    delete_after=6,
                )
            except discord.Forbidden:
                pass


async def setup(bot):
    await bot.add_cog(AntiLink(bot))
