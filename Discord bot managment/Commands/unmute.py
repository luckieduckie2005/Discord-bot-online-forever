import discord
from discord.ext import commands
from discord import app_commands

# =========================
# Permissions
# =========================

OWNER_ID = 1530207060271169638

ROLE_MODERATOR = 1530175947850911764
ROLE_ADMINISTRATOR = 1530178027710058496

# =========================
# Unmute Cog
# =========================

class Unmute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="unmute",
        description="Remove a member's timeout."
    )
    @app_commands.describe(
        member="Member to unmute",
        reason="Reason for removing the timeout"
    )
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided"
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
                "❌ You cannot unmute bots ❌",
                ephemeral=True
            )
            return

        if not member.is_timed_out():
            await interaction.response.send_message(
                "❌ That member is not muted ❌",
                ephemeral=True
            )
            return

        # -------------------------
        # Remove Timeout
        # -------------------------

        try:
            await member.timeout(
                None,
                reason=f"{reason} | By: {interaction.user}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to unmute that member ❌",
                ephemeral=True
            )
            return

        # -------------------------
        # DM Member
        # -------------------------

        try:
            dm = discord.Embed(
                title="🔊 You Have Been Unmuted",
                color=discord.Color.green()
            )

            dm.add_field(
                name="Server",
                value=interaction.guild.name,
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
            title="🔊 Member Unmuted",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(
            name="Member",
            value=f"{member.mention}\n`{member.id}`",
            inline=False
        )

        embed.add_field(
            name="Moderator",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="Reason",
            value=reason,
            inline=False
        )

        await interaction.response.send_message(embed=embed)

# =========================
# Load Cog
# =========================

async def setup(bot):
    await bot.add_cog(Unmute(bot))