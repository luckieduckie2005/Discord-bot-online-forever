"""
Hello command – works as both /hello and !hello.
"""

import discord
from discord import app_commands
from discord.ext import commands


class Hello(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="hello", description="Say hello to someone")
    @app_commands.describe(name="Who to greet (optional)")
    async def hello(self, ctx: commands.Context, name: str = None):
        if name:
            await ctx.send(f"Hello, {name}! 👋")
        else:
            await ctx.send(f"Hello, {ctx.author.display_name}! 👋")


async def setup(bot):
    await bot.add_cog(Hello(bot))
