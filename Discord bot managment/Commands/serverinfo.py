import discord
from discord.ext import commands
from discord import app_commands

class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="serverinfo",
        description="View information about the server."
    )
    async def serverinfo(self, interaction: discord.Interaction):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True
            )
            return

        owner = guild.owner
        if owner is None:
            owner = await self.bot.fetch_user(guild.owner_id)

        total_members = guild.member_count
        humans = len([m for m in guild.members if not m.bot])
        bots = len([m for m in guild.members if m.bot])

        created = discord.utils.format_dt(guild.created_at, style="F")

        embed = discord.Embed(
            title=f"{guild.name}",
            description="**Server Information**",
            color=discord.Color.blurple()
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(
            name="👑 Owner 👑",
            value=f"{owner.mention}\n`{owner.id}`",
            inline=False
        )

        embed.add_field(
            name="Server ID",
            value=f"`{guild.id}`",
            inline=True
        )

        embed.add_field(
            name="Created",
            value=created,
            inline=True
        )

        embed.add_field(
            name="Members",
            value=(
                f"**Total:** {total_members}\n"
                f"**Humans:** {humans}\n"
                f"**Bots:** {bots}"
            ),
            inline=False
        )

        if guild.banner:
            embed.set_image(url=guild.banner.url)

        embed.set_footer(
            text=f"Requested by {interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(ServerInfo(bot))