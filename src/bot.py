import asyncio
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

from src import db, embeds
from src.client import StarterLeagueClient, PINDOLZ_TEAM_ID

load_dotenv()


def load_version() -> str:
    candidates = [
        Path(__file__).resolve().parent.parent / "VERSION",
        Path("VERSION"),
        Path("/home/container/VERSION"),
    ]
    for p in candidates:
        try:
            if p.is_file():
                return p.read_text(encoding="utf-8").strip() or "unknown"
        except Exception:
            continue
    return "unknown"


BOT_VERSION = load_version()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TZ = ZoneInfo("Europe/Warsaw")

TABLE_UPDATE_TIMES = [
    time(8, 0, tzinfo=TZ),
    time(18, 0, tzinfo=TZ),
    time(20, 0, tzinfo=TZ),
    time(21, 30, tzinfo=TZ),
    time(23, 0, tzinfo=TZ),
]
LIVE_INTERVAL_IDLE = 10
LIVE_INTERVAL_ACTIVE = 5
START_DELAY_LIVE = 15
START_DELAY_PREMATCH = 30
START_DELAY_TABLE = 45
START_DELAY_DAILY = 60
START_DELAY_WEEKLY = 75
START_DELAY_CLEANUP = 90

STATUS_PHRASES = [
    "🚩 Zawsze do przodu",
    "💪 PINDOLZ nie odpuszcza",
    "🔥 GG WP",
    "🎯 Celujemy w top 1",
    "⚡ Gramy o zwycięstwo",
    "🚩 Do boju, PINDOLZ!",
    "😎 Spokojnie, mamy to",
    "🏆 Po puchar!",
    "🧠 Taktyka ponad wszystko",
    "🚀 Lecimy po wygraną",
    "🤝 Razem silniejsi",
    "👀 Śledzę PINDOLZ · /pomoc",
]


class RefreshTabelaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Odśwież", style=discord.ButtonStyle.secondary, custom_id="pindolz_refresh_tabela")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            table = await asyncio.to_thread(bot.api.get_division6_table)
            emb = embeds.standings_embed(table, changes=bot._rank_changes(table))
            await interaction.message.edit(embed=emb, view=self)
            await interaction.followup.send("Odświeżono.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Błąd: {e}", ephemeral=True)


class RefreshWynikiView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Odśwież", style=discord.ButtonStyle.secondary, custom_id="pindolz_refresh_wyniki")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            history = await asyncio.to_thread(bot.api.get_pindolz_history)
            emb = embeds.history_embed(history)
            await interaction.message.edit(embed=emb, view=self)
            await interaction.followup.send("Odświeżono.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Błąd: {e}", ephemeral=True)


def refresh_view(kind: str) -> discord.ui.View:
    return RefreshTabelaView() if kind == "tabela" else RefreshWynikiView()


class LiveChannelView(discord.ui.View):
    def __init__(self, guild_id: int, channel_id: int):
        super().__init__(timeout=None)
        url = f"https://discord.com/channels/{guild_id}/{channel_id}"
        self.add_item(discord.ui.Button(label="Kanał LIVE", style=discord.ButtonStyle.link, url=url))


FEATURES = {
    "prematch": ("Przypomnienia", "⏰ Przypomnienie 1 h i 30 min przed meczem na kanale głównym"),
    "reactions": ("Reakcje", "🎉 Reakcje 🎉/😢 pod wynikiem"),
    "status": ("Status", "🟢 Status bota (odliczanie, seria, LIVE)"),
    "live": ("LIVE", "🔴 Relacja LIVE na kanale LIVE"),
    "thread": ("Wątek LIVE", "🧵 Wątek z przebiegiem meczu pod kartą LIVE"),
    "polls": ("Ankiety", "🗳️ Ankieta „Kto może grać?”"),
    "rank": ("Awans/spadek", "📈 Powiadomienie o zmianie miejsca w tabeli"),
    "alerts": ("Alerty API", "🚨 Wiadomość prywatna o awarii API"),
}


def feature_on(name: str) -> bool:
    return db.get_config(f"feat_{name}") != "0"


def settings_embed() -> discord.Embed:
    lines = [f"{'✅' if feature_on(k) else '❌'} {desc}" for k, (_, desc) in FEATURES.items()]
    emb = embeds._base("⚙️ Ustawienia bota", embeds.C_INFO, "\n".join(lines))
    emb.set_footer(text="Kliknij przycisk, aby włączyć lub wyłączyć funkcję")
    return emb


class FeatureButton(discord.ui.Button):
    def __init__(self, key: str):
        on = feature_on(key)
        super().__init__(
            label=f"{'✅' if on else '❌'} {FEATURES[key][0]}",
            style=discord.ButtonStyle.success if on else discord.ButtonStyle.danger,
        )
        self.key = key

    async def callback(self, interaction: discord.Interaction):
        if not bot.is_owner(interaction):
            await interaction.response.send_message("Tylko właściciel serwera może to zmienić.", ephemeral=True)
            return
        db.set_config(f"feat_{self.key}", "0" if feature_on(self.key) else "1")
        await interaction.response.edit_message(embed=settings_embed(), view=SettingsView())


class SettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)
        for key in FEATURES:
            self.add_item(FeatureButton(key))


class RemindButton(discord.ui.DynamicItem[discord.ui.Button], template=r"pindolz_remind:(?P<mid>\d+)"):
    def __init__(self, mid: int):
        super().__init__(
            discord.ui.Button(label="Przypomnij mi", emoji="🔔", style=discord.ButtonStyle.primary, custom_id=f"pindolz_remind:{mid}")
        )
        self.mid = mid

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match, /):
        return cls(int(match["mid"]))

    async def callback(self, interaction: discord.Interaction):
        await bot.toggle_reminder(interaction, self.mid)


def remind_view(mid: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(RemindButton(mid))
    return view


POLL_BUTTONS = {
    "yes": ("Mogę", "✅", discord.ButtonStyle.success),
    "no": ("Nie mogę", "❌", discord.ButtonStyle.danger),
    "maybe": ("Może", "❔", discord.ButtonStyle.secondary),
}


class PollButton(discord.ui.DynamicItem[discord.ui.Button], template=r"pindolz_poll:(?P<mid>\d+):(?P<vote>yes|no|maybe)"):
    def __init__(self, mid: int, vote: str):
        label, emoji, style = POLL_BUTTONS[vote]
        super().__init__(discord.ui.Button(label=label, emoji=emoji, style=style, custom_id=f"pindolz_poll:{mid}:{vote}"))
        self.mid = mid
        self.vote = vote

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match, /):
        return cls(int(match["mid"]), match["vote"])

    async def callback(self, interaction: discord.Interaction):
        await bot.handle_poll_vote(interaction, self.mid, self.vote)


def poll_view(mid: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for vote in POLL_BUTTONS:
        view.add_item(PollButton(mid, vote))
    return view


# NOTE: Rest of bot restored from local full copy - see repository history if incomplete
print("Bot partial restore - please check")
