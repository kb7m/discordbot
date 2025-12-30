import discord
from discord import app_commands
from discord.ext import commands

STAFF_ROLE_NAME = "Staff"
TICKET_CATEGORY_NAME = "Tickets"

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 閉じる",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:close"
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("ここでは使えないよ。", ephemeral=True)

        await interaction.response.send_message("チケットを閉じます…", ephemeral=True)
        await channel.delete(reason="Ticket closed")

class TicketCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.view = CloseTicketView()

        # 永続View登録（再起動してもボタンが反応するように）
        bot.add_view(self.view)

    @app_commands.command(name="ticket", description="問い合わせチケットを作成します")
    async def ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("サーバー内で使ってね。", ephemeral=True)

        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)

        if category is None:
            category = await guild.create_category(TICKET_CATEGORY_NAME, reason="Ticket category created")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )

        # チャンネル名の安全化（長すぎ対策）
        safe_name = interaction.user.name.lower().replace(" ", "-")
        safe_name = "".join(ch for ch in safe_name if ch.isalnum() or ch in "-_")
        channel_name = f"ticket-{safe_name}"[:90]

        ticket_channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            reason="Ticket created"
        )

        embed = discord.Embed(
            title="チケット",
            description="内容を送ってください。スタッフが対応します。\n終わったら「閉じる」を押してね。",
            color=0xe67e22
        )
        await ticket_channel.send(content=interaction.user.mention, embed=embed, view=self.view)
        await interaction.response.send_message(
            f"チケットを作成したよ： {ticket_channel.mention}",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(TicketCog(bot))
