import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

INTENTS = discord.Intents.default()
INTENTS.message_content = True  # スパム検知を入れるならON
INTENTS.members = True

class MyBot(commands.Bot):
    async def setup_hook(self):
        # Cog読み込み
        await self.load_extension("cogs.auth")
        await self.load_extension("cogs.ticket")

        # スラッシュコマンド同期（グローバル）
        await self.tree.sync()

bot = MyBot(command_prefix="!", intents=INTENTS)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")

bot.run(os.getenv("DISCORD_TOKEN"))
