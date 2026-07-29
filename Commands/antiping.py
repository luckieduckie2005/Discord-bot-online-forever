import datetime
import discord
from discord.ext import commands
from discord import app_commands

# ==========================================================
# CONFIG
# ==========================================================

OWNER_ID = 1530207060271169638

ROLE_MODERATOR = 1530175947850911764
ROLE_ADMINISTRATOR = 1530178027710058496

ROLE_SUPPORT = 1530173860261920883
ROLE_VERIFIED = 1530171415288877117

TIMEOUT_MINUTES = 5


class AntiPing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Create variable once
        if not hasattr(bot, "antiping_enabled"):
            bot.antiping_enabled = False

    # ======================================================
    # /antiping
    # ======================================================

    @app_commands.command(
        name="antiping",
        description="protect antiping members"
    )
    @app_commands.choices(
        state=[
            app_commands.Choice(name="Enable", value="enable"),
            app_commands.Choice(name="Disable", value="disable"),
        ]
    )
    async def antiping(
        self,
        interaction: discord.Interaction,
        state: app_commands.Choice[str]
    ):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need Administrator permission.",
                ephemeral=True
            )
            return

        self.bot.antiping_enabled = state.value == "enable"

        embed = discord.Embed(
            title="🛡️ AntiPing",
            description=f"AntiPing has been **{'Enabled' if self.bot.antiping_enabled else 'Disabled'}**.",
            color=discord.Color.green() if self.bot.antiping_enabled else discord.Color.red()
        )

        await interaction.response.send_message(embed=embed)

    # ======================================================
    # LISTENER
    # ======================================================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if not self.bot.antiping_enabled:
            return

        if message.author.bot:
            return

        if message.guild is None:
            return

        if not isinstance(message.author, discord.Member):
            return

        author = message.author

        author_roles = {r.id for r in author.roles}

        # Only Support or Verified can trigger punishment
        if (
            ROLE_SUPPORT not in author_roles
            and ROLE_VERIFIED not in author_roles
        ):
            return

        violation = False

        # Check every mentioned member
        for member in message.mentions:

            member_roles = {r.id for r in member.roles}

            if (
                member.id == OWNER_ID
                or ROLE_MODERATOR in member_roles
                or ROLE_ADMINISTRATOR in member_roles
            ):
                violation = True
                break

        # Check role mentions (@Moderator / @Administrator)
        if not violation:
            for role in message.role_mentions:
                if role.id in (
                    ROLE_MODERATOR,
                    ROLE_ADMINISTRATOR,
                ):
                    violation = True
                    break

        if not violation:
            return

        # Delete message
        try:
            await message.delete()
        except Exception:
            pass

        # Timeout
        try:
            await author.timeout(
                discord.utils.utcnow() + datetime.timedelta(minutes=TIMEOUT_MINUTES),
                reason="AntiPing"
            )

            embed = discord.Embed(
                title="🚫 AntiPing",
                description=(
                    f"{author.mention}\n\n"
                    "You are not allowed to ping staff members.\n\n"
                    f"Timeout: **{TIMEOUT_MINUTES} minutes**."
                ),
                color=discord.Color.red()
            )

            await message.channel.send(
                embed=embed,
                delete_after=10
            )

        except discord.Forbidden:
            await message.channel.send(
                "❌ I cannot timeout that member.\n"
                "Make sure I have **Moderate Members** permission and my role is above theirs.",
                delete_after=10
            )

        except Exception as e:
            print(f"[AntiPing] {e}")


async def setup(bot):
    await bot.add_cog(AntiPing(bot))