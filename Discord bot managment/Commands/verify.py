import discord
from discord.ext import commands
from discord import app_commands

# ============================================
# CONFIG
# ============================================

VERIFIED_ROLE_ID = 1530171415288877117  # Replace with your Verified role ID

# ============================================
# VERIFY VIEW
# ============================================

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Complete Security Check",
        emoji="🛡️",
        style=discord.ButtonStyle.success,
        custom_id="koohelper_verify"
    )
    async def verify_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        role = interaction.guild.get_role(VERIFIED_ROLE_ID)

        if role is None:
            await interaction.response.send_message(
                "❌ Verified role not found ❌",
                ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                "✅ You have already completed the security check ✅",
                ephemeral=True
            )
            return

        try:
            await interaction.user.add_roles(
                role,
                reason="Completed Security Check"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to assign the Verified role ❌",
                ephemeral=True
            )
            return

        success = discord.Embed(
            title="✅ Security Check Passed ",
            description=(
                f"Welcome to **{interaction.guild.name}**!\n\n"
                "Your identity has been verified successfully.\n\n"
                "You now have full access to the server."
            ),
            color=0x57F287
        )

        success.set_footer(text="Enjoy your stay!")

        await interaction.response.send_message(
            embed=success,
            ephemeral=True
        )

# ============================================
# VERIFY COMMAND
# ============================================

class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="verify",
        description="Create the premium verification panel."
    )
    async def verify(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="🛡️ Security Check Required 🛡️",
            description=(
                "## Welcome!\n\n"
                "To protect this community from spam, bots, and malicious accounts, "
                "every member must complete a quick security check.\n\n"
                "**What happens after verifying?**\n"
                "✅ Access all channels\n"
                "✅ Unlock community features\n"
                "✅ Receive the Verified role\n\n"
                "Click the button below to continue."
            ),
            color=0x5865F2
        )

        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        if interaction.guild.banner:
            embed.set_image(url=interaction.guild.banner.url)

        embed.set_footer(
            text=f"{interaction.guild.name} • Secure Verification"
        )

        await interaction.response.send_message(
            embed=embed,
            view=VerifyView()
        )

# ============================================
# LOAD COG
# ============================================

async def setup(bot):
    await bot.add_cog(Verify(bot))