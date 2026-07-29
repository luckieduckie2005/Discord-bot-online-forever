import datetime
import discord
from discord.ext import commands

# ==========================================================
# CONFIG
# ==========================================================

OWNER_ID = 1530207060271169638

ROLE_MODERATOR = 1530175947850911764
ROLE_ADMINISTRATOR = 1530178027710058496

ROLE_SUPPORT = 1530173860261920883
ROLE_VERIFIED = 1530171415288877117

TIMEOUT_MINUTES = 5

# Staff roles that are protected from being pinged
PROTECTED_ROLE_IDS = {
    ROLE_MODERATOR,
    ROLE_ADMINISTRATOR,
}


class AntiPing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots and DMs
        if message.author.bot or message.guild is None:
            return

        if not isinstance(message.author, discord.Member):
            return

        member = message.author

        # ============================================
        # Staff members are allowed to ping staff
        # Everyone else (including Support & Verified)
        # will be punished.
        # ============================================

        member_role_ids = {role.id for role in member.roles}

        if (
            member.id == OWNER_ID
            or ROLE_MODERATOR in member_role_ids
            or ROLE_ADMINISTRATOR in member_role_ids
            or member.guild_permissions.administrator
        ):
            return

        violation = False

        # --------------------------------------------
        # Pinging the protected Owner
        # --------------------------------------------
        for user in message.mentions:
            if user.id == OWNER_ID:
                violation = True
                break

        # --------------------------------------------
        # Pinging Moderator/Admin roles
        # --------------------------------------------
        if not violation:
            for role in message.role_mentions:
                if role.id in PROTECTED_ROLE_IDS:
                    violation = True
                    break

        # --------------------------------------------
        # @everyone / @here
        # --------------------------------------------
        if message.mention_everyone:
            violation = True

        if not violation:
            return

        # Delete message
        try:
            await message.delete()
        except Exception:
            pass

        # Timeout member
        try:
            until = discord.utils.utcnow() + datetime.timedelta(minutes=TIMEOUT_MINUTES)

            await member.timeout(
                until,
                reason="AntiPing - Pinged protected staff."
            )

            await message.channel.send(
                f"🚫 {member.mention} You are not allowed to ping the **Owner, Moderator, or Administrator**.\n"
                f"⏱️ You have been timed out for **{TIMEOUT_MINUTES} minutes**.",
                delete_after=10
            )

            print(f"[AntiPing] Timed out {member}")

        except discord.Forbidden:
            await message.channel.send(
                "❌ I couldn't timeout this member.\n"
                "Make sure my role is above theirs and I have the **Moderate Members** permission.",
                delete_after=10
            )

        except Exception as e:
            print(f"[AntiPing] Error: {e}")


async def setup(bot):
    await bot.add_cog(AntiPing(bot))
    print("✅ AntiPing Cog Loaded")