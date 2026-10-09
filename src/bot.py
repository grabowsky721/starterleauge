import asyncio
import json
import os
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

from src.client import StarterLeagueClient
from src import embeds

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
TZ = ZoneInfo("Europe/Warsaw")

DATA_DIR = Path("data")
CONFIG_PATH = DATA_DIR / "config.json"
STATE_PATH = DATA_DIR / "state.json"

DATA_DIR.mkdir(exist_ok=True)


def load_json(path: Path, default: dict) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class PindolzBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.api = StarterLeagueClient()
        self.config = load_json(CONFIG_PATH, {"main_channel_id": None, "live_channel_id": None})
        self.state = load_json(
            STATE_PATH,
            {
                "seen_history_ids": [],
                "seen_upcoming_ids": [],
                "live_matches": {},  # match_id -> {message_id, last_updated, last_score}
            },
        )

    async def setup_hook(self):
        await self.tree.sync()
        self.daily_check.start()
        self.live_check.start()

    def is_owner(self, user: discord.User | discord.Member) -> bool:
        return user.id == OWNER_ID

    def save_config(self):
        save_json(CONFIG_PATH, self.config)

    def save_state(self):
        save_json(STATE_PATH, self.state)

    async def get_channel_safe(self, channel_id: int | None):
        if not channel_id:
            return None
        return self.get_channel(channel_id) or await self.fetch_channel(channel_id)

    # ---------- DAILY CHECK (2x dziennie) ----------
    @tasks.loop(time=[time(9, 0, tzinfo=TZ), time(20, 0, tzinfo=TZ)])
    async def daily_check(self):
        await self._run_daily_check()

    @daily_check.before_loop
    async def before_daily(self):
        await self.wait_until_ready()

    async def _run_daily_check(self):
        channel = await self.get_channel_safe(self.config.get("main_channel_id"))
        if not channel:
            return

        try:
            history = self.api.get_pindolz_history()
            upcoming = self.api.get_pindolz_upcoming()
        except Exception as e:
            print(f"[daily] API error: {e}")
            return

        seen_h = set(self.state.get("seen_history_ids") or [])
        seen_u = set(self.state.get("seen_upcoming_ids") or [])

        new_results = [m for m in history if m.get("id") not in seen_h]
        new_upcoming = [m for m in upcoming if m.get("id") not in seen_u]

        if new_results:
            emb = embeds.history_embed(new_results, limit=5)
            emb.title = "Nowe wyniki PINDOLZ"
            await channel.send(embed=emb)
            for m in new_results:
                seen_h.add(m["id"])

        if new_upcoming:
            emb = embeds.upcoming_embed(new_upcoming)
            emb.title = "Nowe zaplanowane mecze PINDOLZ"
            await channel.send(embed=emb)
            for m in new_upcoming:
                seen_u.add(m["id"])

        # trzymaj tylko ostatnie ~50 id
        self.state["seen_history_ids"] = list(seen_h)[-50:]
        self.state["seen_upcoming_ids"] = list(seen_u)[-50:]
        self.save_state()

    # ---------- LIVE CHECK ----------
    @tasks.loop(seconds=75)
    async def live_check(self):
        await self._run_live_check()

    @live_check.before_loop
    async def before_live(self):
        await self.wait_until_ready()

    async def _run_live_check(self):
        channel = await self.get_channel_safe(self.config.get("live_channel_id"))
        if not channel:
            return

        try:
            lives = self.api.get_pindolz_live()
        except Exception as e:
            print(f"[live] API error: {e}")
            return

        current_ids = {m["id"] for m in lives}
        known = self.state.get("live_matches") or {}

        # nowe mecze (start)
        for m in lives:
            mid = str(m["id"])
            if mid not in known:
                emb = embeds.match_started_embed(m)
                msg = await channel.send(embed=emb)
                # od razu druga wiadomość z aktualnym stanem
                live_emb = embeds.live_embed(m)
                live_msg = await channel.send(embed=live_emb)
                known[mid] = {
                    "message_id": live_msg.id,
                    "last_updated": m.get("updatedAt"),
                    "score_key": self._score_key(m),
                }

            else:
                # aktualizacja wyniku
                info = known[mid]
                new_key = self._score_key(m)
                if new_key != info.get("score_key") or m.get("updatedAt") != info.get("last_updated"):
                    try:
                        msg = await channel.fetch_message(info["message_id"])
                        await msg.edit(embed=embeds.live_embed(m))
                    except Exception:
                        # jak nie da się edytować – wyślij nową
                        msg = await channel.send(embed=embeds.live_embed(m))
                        info["message_id"] = msg.id
                    info["last_updated"] = m.get("updatedAt")
                    info["score_key"] = new_key

        # zakończone mecze (zniknęły z live)
        finished_ids = [mid for mid in list(known.keys()) if int(mid) not in current_ids]
        if finished_ids:
            try:
                history = self.api.get_pindolz_history()
                history_by_id = {m["id"]: m for m in history}
            except Exception:
                history_by_id = {}

            for mid in finished_ids:
                match = history_by_id.get(int(mid))
                if match:
                    await channel.send(embed=embeds.match_ended_embed(match))
                del known[mid]

        self.state["live_matches"] = known
        self.save_state()

    @staticmethod
    def _score_key(match: dict) -> str:
        current = match.get("currentMap") or {}
        score = current.get("score") or {}
        series = match.get("seriesScore") or {}
        return f"{score.get('team1')}-{score.get('team2')}|{series.get('team1')}-{series.get('team2')}|{current.get('name')}"


bot = PindolzBot()


# ---------- KOMENDY ----------

@bot.tree.command(name="pindolz", description="Najbliższe i ostatnie mecze PINDOLZ")
async def cmd_pindolz(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        upcoming = bot.api.get_pindolz_upcoming()
        history = bot.api.get_pindolz_history()
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return

    await interaction.followup.send(embeds=[embeds.upcoming_embed(upcoming), embeds.history_embed(history)])


@bot.tree.command(name="live", description="Czy PINDOLZ gra teraz?")
async def cmd_live(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        lives = bot.api.get_pindolz_live()
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return

    if not lives:
        await interaction.followup.send("Aktualnie PINDOLZ nie gra.")
        return

    await interaction.followup.send(embeds=[embeds.live_embed(m) for m in lives])


@bot.tree.command(name="wyniki", description="Ostatnie wyniki PINDOLZ")
async def cmd_wyniki(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        history = bot.api.get_pindolz_history()
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    await interaction.followup.send(embed=embeds.history_embed(history))


@bot.tree.command(name="nadchodzace", description="Nadchodzące mecze PINDOLZ")
async def cmd_nadchodzace(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        upcoming = bot.api.get_pindolz_upcoming()
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    await interaction.followup.send(embed=embeds.upcoming_embed(upcoming))


@bot.tree.command(name="setup", description="Ustaw kanał główny (tylko właściciel)")
@app_commands.describe(kanal="Kanał na wyniki i nadchodzące mecze")
async def cmd_setup(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not bot.is_owner(interaction.user):
        await interaction.response.send_message("Tylko właściciel może to użyć.", ephemeral=True)
        return

    bot.config["main_channel_id"] = kanal.id
    bot.save_config()
    await interaction.response.send_message(
        f"Kanał główny ustawiony na {kanal.mention}", ephemeral=True
    )


@bot.tree.command(name="setup-live", description="Ustaw kanał live (tylko właściciel)")
@app_commands.describe(kanal="Kanał na powiadomienia live")
async def cmd_setup_live(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not bot.is_owner(interaction.user):
        await interaction.response.send_message("Tylko właściciel może to użyć.", ephemeral=True)
        return

    bot.config["live_channel_id"] = kanal.id
    bot.save_config()
    await interaction.response.send_message(
        f"Kanał live ustawiony na {kanal.mention}", ephemeral=True
    )


@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    print("Bot gotowy.")


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("Brak DISCORD_BOT_TOKEN")
    bot.run(TOKEN)
