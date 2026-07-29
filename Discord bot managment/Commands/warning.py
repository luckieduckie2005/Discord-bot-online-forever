import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

# =========================
# Permissions
# =========================

OWNER_ID = 1530207060271169638

ROLE_MODERATOR = 1530175947850911764
ROLE_ADMINISTRATOR = 1530178027710058496

# =========================
# Warning Cog
# =========================

class Warning(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warning_file = "warnings.json"

        if not os.path.exists(self.warning_file):
            with open(self.warning_file, "w") as f:
                json.dump({}, f, indent=4)

    def load_warnings(self):
        with open(self.warning_file, "r") as f:
            return json.load(f)

    def save_warnings(self, data):
        with open(self.warning_file, "w") as f:
            json.dump(data, f, indent=4)

    @app_commands.command(
        name="warning",
        description="Warn a server member."
    )
    @app_commands.describe(
        member="Member to warn",
        reason="Reason for the warning"
    )
    async def warning(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
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
                    "❌ You don't have permission to use this command.",
                    ephemeral=True
                )
                return

        # -------------------------
        # Invalid Targets
        # -------------------------

        if member.bot:
            await interaction.response.send_message(
                "❌ You cannot warn bots.",
                ephemeral=True
            )
            return

        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ You cannot warn yourself.",
                ephemeral=True
            )
            return

        if member.id == OWNER_ID:
            await interaction.response.send_message(
                "❌ You cannot warn the owner.",
                ephemeral=True
            )
            return

        if any(role.id == ROLE_ADMINISTRATOR for role in member.roles):
            await interaction.response.send_message(
                "❌ You cannot warn an administrator.",
                ephemeral=True
            )
            return

        if any(role.id == ROLE_MODERATOR for role in member.roles):
            await interaction.response.send_message(
                "❌ You cannot warn a moderator.",
                ephemeral=True
            )
            return

        # -------------------------
        # Save Warning
        # -------------------------

        data = self.load_warnings()

        user_id = str(member.id)

        if user_id not in data:
            data[user_id] = []

        warning = {
            "reason": reason,
            "moderator": str(interaction.user),
            "moderator_id": interaction.user.id,
            "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        }

        data[user_id].append(warning)

        self.save_warnings(data)

        total = len(data[user_id])

        # -------------------------
        # DM User
        # -------------------------

        try:
            dm = discord.Embed(
                title="⚠️ You Have Been Warned",
                color=discord.Color.orange()
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

            dm.add_field(
                name="Total Warnings",
                value=str(total),
                inline=False
            )

            await member.send(embed=dm)

        except Exception:
            pass

        # -------------------------
        # Success Embed
        # -------------------------

        embed = discord.Embed(
            title="⚠️ Member Warned",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="Member",
            value=f"{member.mention}\n`{member.id}`",
            inline=False
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

        embed.add_field(
            name="Total Warnings",
            value=str(total),
            inline=True
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        await interaction.response.send_message(embed=embed)

# =========================
# Load Cog
# =========================

async def setup(bot):
    await bot.add_cog(Warning(bot))