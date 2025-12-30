import discord
from discord import app_commands
from discord.ext import commands

ROLE_NAME = "メンバー"  # 付与したいロール名

class AuthView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="✅ ルールに同意して参加",
        style=discord.ButtonStyle.success,
        custom_id="auth:agree"  # 永続Viewで必須（固定ID）
    )
    async def agree(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("サーバー内で使ってね。", ephemeral=True)

        role = discord.utils.get(guild.roles, name=ROLE_NAME)
        if role is None:
            return await interaction.response.send_message(f"ロール「{ROLE_NAME}」が見つからないよ。", ephemeral=True)

        member = interaction.user
        if not isinstance(member, discord.Member):
            member = await guild.fetch_member(interaction.user.id)

        if role in member.roles:
            return await interaction.response.send_message("すでに認証済み！", ephemeral=True)

        # Botのロールが「メンバー」ロールより上にないと失敗するので注意
        await member.add_roles(role, reason="Auth button")
        await interaction.response.send_message("認証完了！ようこそ！", ephemeral=True)

class AuthCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.view = AuthView()

        # 永続View登録（再起動してもボタンが反応するように）
        bot.add_view(self.view)

    @app_commands.command(name="setup_auth", description="認証ボタンをこのチャンネルに設置します")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_auth(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="認証",
            description="下のボタンを押してルールに同意すると参加できます。",
            color=0x2ecc71
        )
        await interaction.channel.send(embed=embed, view=self.view)
        await interaction.response.send_message("認証パネルを設置したよ。", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AuthCog(bot))
