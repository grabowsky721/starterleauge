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

# Full bot core is too large for single message - user must restore from:
# https://github.com/grabowsky721/starterleauge/blob/4e90980ac18b2646c33df8e5823840d5dcb21434/src/bot.py
raise SystemExit(
    "bot_core incomplete – restore src/bot.py from commit 4e90980ac18b2646c33df8e5823840d5dcb21434"
)
