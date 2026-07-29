"""
Ping command – works as both /ping (slash) and !ping (prefix).
"""

import discord
from discord import app_commands
from discord.ext import commands


class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Check bot latency")
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"Pong! Latency: **{latency}ms**")


async def setup(bot):
    await bot.add_cog(Ping(bot))
