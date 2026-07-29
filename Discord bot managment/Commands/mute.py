import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta

# =========================
# Permissions
# =========================

OWNER_ID = 1530207060271169638

ROLE_MODERATOR = 1530175947850911764
ROLE_ADMINISTRATOR = 1530178027710058496

# =========================
# Mute Cog
# =========================

class Mute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="mute",
        description="Timeout (mute) a member."
    )
    @app_commands.describe(
        member="Member to mute",
        minutes="Timeout duration in minutes",
        reason="Reason for the timeout"
    )
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str
    ):

        # -------------------------
        # Permission Check
        # -------------------------

        if interaction.user.id != OWNER_ID:

            allowed = False

            for role in interaction.user.roles:
                if role.id in [ROLE_MODERATOR, ROLE_ADMINISTRATOR]:
                    allowed = True
                    break

            if not allowed:
                await interaction.response.send_message(
                    "❌ You don't have permission to use this command ❌",
                    ephemeral=True
                )
                return

        # -------------------------
        # Invalid Targets
        # -------------------------

        if member.bot:
            await interaction.response.send_message(
                "❌ You cannot mute bots ❌",
                ephemeral=True
            )
            return

        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ You cannot mute yourself ❌",
                ephemeral=True
            )
            return

        if member.id == OWNER_ID:
            await interaction.response.send_message(
                "❌ You cannot mute the owner ❌",
                ephemeral=True
            )
            return

        if any(role.id == ROLE_ADMINISTRATOR for role in member.roles):
            await interaction.response.send_message(
                "❌ You cannot mute an administrator ❌",
                ephemeral=True
            )
            return

        if any(role.id == ROLE_MODERATOR for role in member.roles):
            await interaction.response.send_message(
                "❌ You cannot mute a moderator ❌",
                ephemeral=True
            )
            return

        # -------------------------
        # Check if already muted
        # -------------------------

        if member.is_timed_out():
            await interaction.response.send_message(
                "❌ That member is already muted ❌",
                ephemeral=True
            )
            return

        # -------------------------
        # Timeout Member
        # -------------------------

        try:
            await member.timeout(
                timedelta(minutes=minutes),
                reason=f"{reason} | By: {interaction.user}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to mute that member ❌ ",
                ephemeral=True
            )
            return

        # -------------------------
        # DM Member
        # -------------------------

        try:
            dm = discord.Embed(
                title="You Have Been Muted",
                color=discord.Color.red()
            )

            dm.add_field(
                name="Server",
                value=interaction.guild.name,
                inline=False
            )

            dm.add_field(
                name="Duration",
                value=f"{minutes} minute(s)",
                inline=False
            )

            dm.add_field(
                name="Reason",
                value=reason,
                inline=False
            )

            dm.add_field(
                name="Moderator",
                value=str(interaction.user),
                inline=False
            )

            await member.send(embed=dm)

        except Exception:
            pass

        # -------------------------
        # Success Embed
        # -------------------------

        embed = discord.Embed(
            title=" Member Muted",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(
            name="Member",
            value=f"{member.mention}\n`{member.id}`",
            inline=False
        )

        embed.add_field(
            name="Duration",
            value=f"{minutes} minute(s)",
            inline=True
        )

        embed.add_field(
            name="Reason",
            value=reason,
            inline=False
        )

        embed.add_field(
            name="Moderator",
            value=interaction.user.mention,
            inline=True
        )

        await interaction.response.send_message(embed=embed)

# =========================
# Load Cog
# =========================

async def setup(bot):
    await bot.add_cog(Mute(bot))