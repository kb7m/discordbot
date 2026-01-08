import json
import os
import time
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

# ===== 設定 =====
SPAM_WINDOW_SEC = 6
SPAM_MAX_MSG = 5
LOG_CHANNEL_NAME = "mod-log"

DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "spam_roles.json"


def load_settings() -> dict[str, int]:
    """guild_id(str) -> role_id(int)"""
    if not DATA_FILE.exists():
        return {}
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            # valueはint化しておく
            out: dict[str, int] = {}
            for k, v in raw.items():
                try:
                    out[str(k)] = int(v)
                except Exception:
                    pass
            return out
    except Exception:
        return {}
    return {}


def save_settings(settings: dict[str, int]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._msg_times: dict[int, list[float]] = {}
        self.settings = load_settings()  # guild_id(str) -> role_id(int)

    async def _get_or_create_log_channel(self, guild: discord.Guild):
        if LOG_CHANNEL_NAME is None:
            return None
        ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        if ch:
            return ch
        if guild.me and guild.me.guild_permissions.manage_channels:
            return await guild.create_text_channel(LOG_CHANNEL_NAME)
        return None

    async def _log(self, guild: discord.Guild, text: str):
        ch = await self._get_or_create_log_channel(guild)
        if ch:
            await ch.send(text)

    def _get_spam_role(self, guild: discord.Guild) -> discord.Role | None:
        role_id = self.settings.get(str(guild.id))
        if not role_id:
            return None
        return guild.get_role(int(role_id))

    async def _apply_spam_role(self, guild: discord.Guild, member: discord.Member) -> discord.Role:
        role = self._get_spam_role(guild)
        if role is None:
            raise RuntimeError("スパムロールが未設定です（/spam_setup で設定してね）")
        await member.add_roles(role, reason="Spam detected")
        return role

    # ===== セットアップコマンド =====
    @app_commands.command(name="spam_setup", description="スパム検知時に付与するロールを設定します")
    @app_commands.checks.has_permissions(administrator=True)
    async def spam_setup(self, interaction: discord.Interaction, role: discord.Role):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("サーバー内で使ってね。", ephemeral=True)

        # Botがそのロールを付与できるか簡易チェック（階層）
        me = guild.me
        if me is not None and role >= me.top_role:
            return await interaction.response.send_message(
                "そのロールはBotのロールより上にあるため付与できないよ。\n"
                "サーバー設定で **Botのロールを上** に移動してね。",
                ephemeral=True
            )

        self.settings[str(guild.id)] = role.id
        save_settings(self.settings)

        await interaction.response.send_message(
            f"✅ このサーバーのスパム付与ロールを {role.mention} に設定したよ。",
            ephemeral=True
        )

    @app_commands.command(name="spam_status", description="このサーバーのスパム設定状況を表示します")
    @app_commands.checks.has_permissions(administrator=True)
    async def spam_status(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("サーバー内で使ってね。", ephemeral=True)

        role = self._get_spam_role(guild)
        if role is None:
            return await interaction.response.send_message("未設定です。`/spam_setup @ロール` で設定してね。", ephemeral=True)

        await interaction.response.send_message(f"現在のスパム付与ロール：{role.mention}", ephemeral=True)

    # ===== スパム検知 =====
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        member = message.author
        if not isinstance(member, discord.Member):
            return

        # 管理者は対象外
        if member.guild_permissions.administrator:
            return

        uid = member.id
        now = time.time()
        times = self._msg_times.get(uid, [])
        times.append(now)

        cutoff = now - SPAM_WINDOW_SEC
        times = [t for t in times if t >= cutoff]
        self._msg_times[uid] = times

        if len(times) >= SPAM_MAX_MSG:
            # 直近メッセージ削除（権限なければ無視）
            try:
                await message.delete()
            except Exception:
                pass

            try:
                role = await self._apply_spam_role(message.guild, member)
                await self._log(
                    message.guild,
                    f"🚫 **スパム検知 → ロール付与**\n"
                    f"ユーザー: {member.mention}\n"
                    f"付与ロール: {role.mention}\n"
                    f"判定: {SPAM_WINDOW_SEC}秒で{len(times)}メッセージ\n"
                    f"ch: {message.channel.mention}"
                )
            except Exception as e:
                await self._log(
                    message.guild,
                    f"⚠️ スパム検知したがロール付与に失敗: {member.mention}\n"
                    f"理由: `{type(e).__name__}: {e}`"
                )

            # 連続発火防止
            self._msg_times[uid] = []


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
