import asyncio
import json
import os
import random
import re
import requests
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
GITHUB_REPO = "grabowsky721/starterleauge"
GITHUB_BRANCH = "main"
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
# Soft-start (od ready): LIVE 20s → +15 prematch → +10 tabela → +15 daily → potem co 20s; weekly na końcu
START_DELAY_LIVE = 20
START_DELAY_PREMATCH = 35
START_DELAY_TABLE = 45
START_DELAY_DAILY = 60
START_DELAY_CLEANUP = 80
START_DELAY_STATUS = 100
START_DELAY_POLL = 120
START_DELAY_API = 140
START_DELAY_EVENT = 160
START_DELAY_COMMANDS = 180
START_DELAY_UPDATE = 200
START_DELAY_WEEKLY = 220

# Kolejność startu komend slash (po jednej, co COMMAND_START_GAP s)
COMMAND_START_GAP = 10
COMMAND_START_ORDER = [
    "pomoc",
    "setup",
    "setup-live",
    "setup-tabela",
    "setup-ankiety",
    "setup-all",
    "status",
    "wersja",
    "ankieta-role",
    "sklad",
    "polacz",
    "gracze",
    "tabela",
    "nadchodzace",
    "wyniki",
    "pindolz",
    "live",
    "ustawienia",
    "pokaz-embedy",
    "gif-dodaj",
    "gif-lista",
    "gif-usun",
]

# Losowe hasła w statusie bota – możesz je dowolnie zmieniać (max ~120 znaków każde)
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


# ---------- Włączanie / wyłączanie funkcji (/ustawienia) ----------
FEATURES = {
    "prematch": ("Przypomnienia", "⏰ Przypomnienie 30 min przed meczem na kanale głównym"),
    "prematch1h": ("Przypomnienie 1 h", "⏰ Przypomnienie 1 godzinę przed meczem na kanale głównym"),
    "events": ("Wydarzenia", "📆 Wydarzenie serwera Discord dla najbliższego meczu"),
    "gg": ("GG", "👏 Przycisk „GG” pod wynikiem"),
    "updates": ("Aktualizacje", "🆕 Powiadomienie o nowej wersji bota na GitHubie"),
    "gif": ("GIF", "🎞️ Losowy GIF po wygranej (lista: /gif-dodaj)"),
    "reactions": ("Reakcje", "🎉 Reakcje 🎉/😢 pod wynikiem"),
    "status": ("Status", "🟢 Status bota (odliczanie, seria, LIVE)"),
    "live": ("LIVE", "🔴 Relacja LIVE na kanale LIVE"),
    "thread": ("Wątek LIVE", "🧵 Wątek z przebiegiem meczu pod kartą LIVE"),
    "polls": ("Ankiety", "🗳️ Ankieta „Kto może grać?”"),
    "rank": ("Awans/spadek", "📈 Powiadomienie o zmianie miejsca w tabeli"),
    "alerts": ("Alerty API", "🚨 Wiadomość prywatna o awarii API"),
    "newmatch": ("Nowy mecz", "🆕 Ogłoszenie nowego meczu lub ustalonego terminu"),
    "delay": ("Opóźnienie", "⏳ Alert (DM do kapitana), gdy mecz nie ruszył 15 min po planie"),
    "report": ("Raport kapitana", "📋 Poniedziałkowy raport w DM do kapitana"),
}


def feature_on(name: str) -> bool:
    return db.get_config(f"feat_{name}") != "0"


def _player_nicks() -> dict[int, str]:
    """Powiązania: ID użytkownika Discord → nick gracza w lidze (/polacz)."""
    try:
        return {int(k): v for k, v in json.loads(db.get_config("player_links") or "{}").items()}
    except Exception:
        return {}


def _win_gifs() -> list[str]:
    try:
        return [str(x) for x in json.loads(db.get_config("win_gifs") or "[]")]
    except Exception:
        return []


def _index_list(key: str) -> list[int]:
    try:
        return [int(x) for x in json.loads(db.get_config(key) or "[]")]
    except Exception:
        return []


def _index_add(key: str, value: int, cap: int = 200) -> None:
    items = _index_list(key)
    if value not in items:
        items.append(int(value))
    db.set_config(key, json.dumps(items[-cap:]))


def _sched_list() -> list[dict]:
    try:
        return list(json.loads(db.get_config("sched_msgs") or "[]"))
    except Exception:
        return []


def _parse_when(data: str, godzina: str):
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?", (data or "").strip())
    t = re.fullmatch(r"(\d{1,2}):(\d{2})", (godzina or "").strip())
    if not m or not t:
        return None
    d, mo, hh, mm = int(m[1]), int(m[2]), int(t[1]), int(t[2])
    now = datetime.now(TZ)
    try:
        if m[3]:
            return datetime(int(m[3]), mo, d, hh, mm, tzinfo=TZ)
        dt = datetime(now.year, mo, d, hh, mm, tzinfo=TZ)
        if dt < now - timedelta(minutes=1):
            dt = datetime(now.year + 1, mo, d, hh, mm, tzinfo=TZ)
        return dt
    except ValueError:
        return None


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


# ---------- Przycisk „Przypomnij mi” ----------
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


# ---------- Przycisk „GG” pod wynikiem ----------
def _gg_users(mid: int) -> list[int]:
    try:
        return [int(x) for x in json.loads(db.get_config(f"gg_{mid}") or "[]")]
    except Exception:
        return []


class GGButton(discord.ui.DynamicItem[discord.ui.Button], template=r"pindolz_gg:(?P<mid>\d+)"):
    def __init__(self, mid: int, count: int = 0):
        label = "GG" + (f" · {count}" if count else "")
        super().__init__(
            discord.ui.Button(label=label, emoji="👏", style=discord.ButtonStyle.secondary, custom_id=f"pindolz_gg:{mid}")
        )
        self.mid = mid

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match, /):
        mid = int(match["mid"])
        return cls(mid, len(_gg_users(mid)))

    async def callback(self, interaction: discord.Interaction):
        users = _gg_users(self.mid)
        uid = interaction.user.id
        if uid in users:
            users.remove(uid)
        else:
            users.append(uid)
        db.set_config(f"gg_{self.mid}", json.dumps(users))
        await interaction.response.edit_message(view=gg_view(self.mid, force=True))


def gg_view(mid: int, force: bool = False) -> discord.ui.View | None:
    if not force and not feature_on("gg"):
        return None
    view = discord.ui.View(timeout=None)
    view.add_item(GGButton(mid, len(_gg_users(mid))))
    return view


# ---------- Przyciski ankiety dostępności ----------
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

# ---------- Potwierdzenie składu (DM) ----------
def _lineup_confirm_key(mid: int) -> str:
    return f"lineup_confirm_{mid}"


def _lineup_confirms(mid: int) -> dict[str, str]:
    try:
        return json.loads(db.get_config(_lineup_confirm_key(mid)) or "{}")
    except Exception:
        return {}


def _set_lineup_confirms(mid: int, data: dict[str, str]) -> None:
    db.set_config(_lineup_confirm_key(mid), json.dumps(data))


class SkladConfirmButton(discord.ui.DynamicItem[discord.ui.Button], template=r"pindolz_sklad:(?P<mid>\d+):(?P<ans>yes|no)"):
    def __init__(self, mid: int, ans: str):
        if ans == "yes":
            label, style, emoji = "Gram", discord.ButtonStyle.success, "✅"
        else:
            label, style, emoji = "Nie mogę", discord.ButtonStyle.danger, "❌"
        super().__init__(
            discord.ui.Button(label=label, emoji=emoji, style=style, custom_id=f"pindolz_sklad:{mid}:{ans}")
        )
        self.mid = mid
        self.ans = ans

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match, /):
        return cls(int(match["mid"]), match["ans"])

    async def callback(self, interaction: discord.Interaction):
        await bot.handle_sklad_confirm(interaction, self.mid, self.ans)


def sklad_confirm_view(mid: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(SkladConfirmButton(mid, "yes"))
    view.add_item(SkladConfirmButton(mid, "no"))
    return view




class PindolzBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.api = StarterLeagueClient()
        self.api.on_division = embeds.set_division
        self._upcoming_cache: tuple[datetime, list] | None = None
        self.started_at = datetime.now(TZ)
        self._announced = False
        self._live_errors = 0
        self._status_idx = 0
        self._status_current = None
        self._api_fail = 0
        self._api_alerted = False
        self._boot_msg = None
        db.init_db()

    async def setup_hook(self):
        self.add_view(RefreshTabelaView())
        self.add_view(RefreshWynikiView())
        try:
            self.add_dynamic_items(RemindButton, PollButton, GGButton, SkladConfirmButton)
        except Exception as e:
            print(f"[start] dynamic items: {e}")
        # Slash-komendy syncowane na końcu soft-startu (przed update_check)
        asyncio.create_task(self._soft_start_tasks())


    BOOT_LABELS = (
        ("live", "LIVE"),
        ("prematch", "Przypomnienia"),
        ("table", "Tabela"),
        ("daily", "Daily"),
        ("cleanup", "Cleanup"),
        ("status", "Status"),
        ("poll", "Ankiety"),
        ("api", "API watch"),
        ("event", "Eventy"),
        ("commands", "Komendy slash"),
        ("update", "Update GitHub"),
        ("weekly", "Weekly"),
    )

    def _boot_progress_embed(self, done: set[str], current: str | None = None) -> discord.Embed:
        lines = []
        for key, label in self.BOOT_LABELS:
            if key in done:
                lines.append(f"✅ {label}")
            elif key == current:
                lines.append(f"🔄 {label}…")
            else:
                lines.append(f"⏳ {label}")
        done_n = len(done)
        total = len(self.BOOT_LABELS)
        emb = embeds.restart_embed(
            BOT_VERSION,
            self._main_channel_id(),
            self._live_channel_id(),
            self._table_channel_id(),
        )
        emb.title = f"🚀 Start bota ({done_n}/{total})"
        emb.description = f"Wersja **`{BOT_VERSION}`** · soft-start w toku"
        if done_n >= total:
            emb.title = f"✅ Bot gotowy ({total}/{total})"
            emb.description = f"Wersja **`{BOT_VERSION}`** · wszystko załadowane"
            emb.color = embeds.C_WIN if hasattr(embeds, "C_WIN") else emb.color
        emb.add_field(name="Postęp ładowania", value="\n".join(lines), inline=False)
        return emb

    async def _boot_set_progress(self, done: set[str], current: str | None = None):
        msg = getattr(self, "_boot_msg", None)
        if not msg:
            return
        try:
            await msg.edit(embed=self._boot_progress_embed(done, current))
        except Exception as e:
            print(f"[boot-msg] {e}")


    async def _soft_start_tasks(self):
        await self.wait_until_ready()
        print("[start] soft-start według harmonogramu (~3 min 40 s)...")
        done: set[str] = set()

        async def step(key: str, delay_before: float, start_fn):
            await self._boot_set_progress(done, current=key)
            if delay_before > 0:
                await asyncio.sleep(delay_before)
            await self._boot_set_progress(done, current=key)
            start_fn()
            done.add(key)
            await self._boot_set_progress(done, current=None)
            print(f"[start] {key}")

        # delays are gaps between steps (first = START_DELAY_LIVE)
        await self._boot_set_progress(done, current="live")
        await asyncio.sleep(START_DELAY_LIVE)
        if not self.live_check.is_running():
            self.live_check.start()
        done.add("live")
        await self._boot_set_progress(done)
        print("[start] live_check")

        await self._boot_set_progress(done, current="prematch")
        await asyncio.sleep(START_DELAY_PREMATCH - START_DELAY_LIVE)
        if not self.prematch_check.is_running():
            self.prematch_check.start()
        done.add("prematch")
        await self._boot_set_progress(done)
        print("[start] prematch_check")

        await self._boot_set_progress(done, current="table")
        await asyncio.sleep(START_DELAY_TABLE - START_DELAY_PREMATCH)
        if not self.table_update.is_running():
            self.table_update.start()
        done.add("table")
        await self._boot_set_progress(done)
        print("[start] table_update")

        await self._boot_set_progress(done, current="daily")
        await asyncio.sleep(START_DELAY_DAILY - START_DELAY_TABLE)
        if not self.daily_check.is_running():
            self.daily_check.start()
        done.add("daily")
        await self._boot_set_progress(done)
        print("[start] daily_check")

        await self._boot_set_progress(done, current="cleanup")
        await asyncio.sleep(START_DELAY_CLEANUP - START_DELAY_DAILY)
        if not self.cleanup_task.is_running():
            self.cleanup_task.start()
        done.add("cleanup")
        await self._boot_set_progress(done)
        print("[start] cleanup_task")

        await self._boot_set_progress(done, current="status")
        await asyncio.sleep(START_DELAY_STATUS - START_DELAY_CLEANUP)
        if not self.status_loop.is_running():
            self.status_loop.start()
        done.add("status")
        await self._boot_set_progress(done)
        print("[start] status_loop")

        await self._boot_set_progress(done, current="poll")
        await asyncio.sleep(START_DELAY_POLL - START_DELAY_STATUS)
        if not self.poll_check.is_running():
            self.poll_check.start()
        done.add("poll")
        await self._boot_set_progress(done)
        print("[start] poll_check")

        await self._boot_set_progress(done, current="api")
        await asyncio.sleep(START_DELAY_API - START_DELAY_POLL)
        if not self.api_watch.is_running():
            self.api_watch.start()
        done.add("api")
        await self._boot_set_progress(done)
        print("[start] api_watch")

        await self._boot_set_progress(done, current="event")
        await asyncio.sleep(START_DELAY_EVENT - START_DELAY_API)
        if not self.event_check.is_running():
            self.event_check.start()
        done.add("event")
        await self._boot_set_progress(done)
        print("[start] event_check")

        await self._boot_set_progress(done, current="commands")
        await asyncio.sleep(START_DELAY_COMMANDS - START_DELAY_EVENT)
        cmd_done: list[str] = []
        total_cmds = len(COMMAND_START_ORDER)
        for name in COMMAND_START_ORDER:
            # aktualizuj wiadomość startową: komendy ładują się (n/22)
            try:
                msg = getattr(self, "_boot_msg", None)
                if msg:
                    emb = self._boot_progress_embed(done, current="commands")
                    idx = len(cmd_done) + 1
                    emb.title = f"🚀 Start bota · komendy {idx}/{total_cmds}"
                    emb.description = (
                        f"Wersja **`{BOT_VERSION}`** · **ładuję komendy** "
                        f"(`{idx}/{total_cmds}`) · teraz **`/{name}`**"
                    )
                    clines = []
                    for n in COMMAND_START_ORDER:
                        if n in cmd_done:
                            clines.append(f"✅ /{n}")
                        elif n == name:
                            clines.append(f"🔄 /{n}…")
                        else:
                            clines.append(f"⏳ /{n}")
                    mid = (len(clines) + 1) // 2
                    emb.add_field(
                        name=f"Komendy ({len(cmd_done)}/{total_cmds})",
                        value="\n".join(clines[:mid]),
                        inline=True,
                    )
                    emb.add_field(
                        name="\u200b",
                        value="\n".join(clines[mid:]),
                        inline=True,
                    )
                    await msg.edit(embed=emb)
            except Exception as e:
                print(f"[boot-cmd] {e}")
            await asyncio.sleep(COMMAND_START_GAP)
            cmd_done.append(name)
            print(f"[start] komenda /{name} ({len(cmd_done)}/{total_cmds})")
        try:
            for guild in self.guilds:
                try:
                    synced = await self.tree.sync(guild=guild)
                    print(f"[sync] {guild.name}: {len(synced)} komend")
                except Exception as e:
                    print(f"[sync] guild {guild.id}: {e}")
            synced = await self.tree.sync()
            print(f"[sync] global: {len(synced)} komend")
        except Exception as e:
            print(f"[sync] blad: {e}")
        done.add("commands")
        try:
            msg = getattr(self, "_boot_msg", None)
            if msg:
                emb = self._boot_progress_embed(done)
                total_cmds = len(COMMAND_START_ORDER)
                emb.title = f"🚀 Start bota · komendy {total_cmds}/{total_cmds}"
                emb.description = (
                    f"Wersja **`{BOT_VERSION}`** · **komendy załadowane** "
                    f"(`{total_cmds}/{total_cmds}`) · sync na Discord…"
                )
                clines = [f"✅ /{n}" for n in COMMAND_START_ORDER]
                mid = (len(clines) + 1) // 2
                emb.add_field(
                    name=f"Komendy ({total_cmds}/{total_cmds})",
                    value="\n".join(clines[:mid]),
                    inline=True,
                )
                emb.add_field(name="\u200b", value="\n".join(clines[mid:]), inline=True)
                await msg.edit(embed=emb)
        except Exception as e:
            print(f"[boot-cmd] {e}")
        print("[start] commands sync – wszystkie komendy")

        await self._boot_set_progress(done, current="update")
        await asyncio.sleep(START_DELAY_UPDATE - START_DELAY_COMMANDS)
        if not self.update_check.is_running():
            self.update_check.start()
        done.add("update")
        await self._boot_set_progress(done)
        print("[start] update_check")

        await self._boot_set_progress(done, current="weekly")
        await asyncio.sleep(START_DELAY_WEEKLY - START_DELAY_UPDATE)
        if not self.weekly_summary.is_running():
            self.weekly_summary.start()
        done.add("weekly")
        await self._boot_set_progress(done)
        print("[start] weekly_summary – soft-start zakończony")

        # dodatkowe zadania (nie wchodzą do paska postępu)
        for loop in (self.schedule_watch, self.delay_check, self.scheduled_messages, self.captain_report):
            if not loop.is_running():
                loop.start()
        print("[start] schedule_watch, delay_check, scheduled_messages, captain_report")



    async def handle_sklad_confirm(self, interaction: discord.Interaction, mid: int, ans: str):
        """Gracz potwierdza / odmawia udziału w składzie (z DM)."""
        uid = interaction.user.id
        data = _lineup_confirms(mid)
        ids_raw = db.get_config(f"lineup_{mid}") or "[]"
        try:
            roster = [int(x) for x in json.loads(ids_raw)]
        except Exception:
            roster = []
        if uid not in roster:
            await interaction.response.send_message(
                "Nie jesteś na liście składu tego meczu.", ephemeral=True
            )
            return
        data[str(uid)] = ans
        _set_lineup_confirms(mid, data)

        label = "Gram ✅" if ans == "yes" else "Nie mogę ❌"
        try:
            await interaction.response.edit_message(
                content=f"Zapisano: **{label}**\nDzięki! Kapitan dostanie podsumowanie.",
                embed=None,
                view=None,
            )
        except Exception:
            await interaction.response.send_message(f"Zapisano: **{label}**", ephemeral=True)

        # Podsumowanie
        yes, no, pending = [], [], []
        for pid in roster:
            st = data.get(str(pid))
            mention = f"<@{pid}>"
            if st == "yes":
                yes.append(mention)
            elif st == "no":
                no.append(mention)
            else:
                pending.append(mention)

        # DM do właściciela serwera (pierwszy guild bota z ownerem)
        owner = None
        guild = interaction.guild
        if guild and guild.owner:
            owner = guild.owner
        if owner is None:
            for g in self.guilds:
                if g.owner_id:
                    try:
                        owner = g.get_member(g.owner_id) or await g.fetch_member(g.owner_id)
                    except Exception:
                        owner = None
                    if owner:
                        break

        lines = [
            f"**Mecz ID `{mid}`** – odpowiedź od <@{uid}>: **{label}**",
            f"✅ Mogą grać ({len(yes)}): {', '.join(yes) or '—'}",
            f"❌ Nie mogą ({len(no)}): {', '.join(no) or '—'}",
            f"⏳ Brak odpowiedzi ({len(pending)}): {', '.join(pending) or '—'}",
        ]
        if not pending and yes and not no:
            lines.insert(0, "🎉 **Cały skład potwierdził dostępność!**")
        elif not pending:
            lines.insert(0, "📋 **Wszyscy z składu odpowiedzieli.**")

        text = "\n".join(lines)
        if owner:
            try:
                await owner.send(text)
            except Exception as e:
                print(f"[sklad-dm-owner] {e}")
        print(f"[sklad] confirm mid={mid} uid={uid} ans={ans}")


    def is_owner(self, interaction: discord.Interaction) -> bool:
        return bool(interaction.guild and interaction.user.id == interaction.guild.owner_id)

    async def get_channel_safe(self, channel_id: int | None):
        if not channel_id:
            return None
        try:
            return self.get_channel(channel_id) or await self.fetch_channel(channel_id)
        except Exception:
            return None

    def _main_channel_id(self) -> int | None:
        return db.get_config_int("main_channel_id")

    def _live_channel_id(self) -> int | None:
        return db.get_config_int("live_channel_id")

    def _table_channel_id(self) -> int | None:
        return db.get_config_int("table_channel_id")

    def _table_msg(self) -> tuple[int | None, int | None]:
        return db.get_config_int("msg_table_id"), db.get_config_int("msg_table_ch")

    @staticmethod
    def _score_key(match: dict) -> str:
        current = match.get("currentMap") or {}
        score = current.get("score") or {}
        series = match.get("seriesScore") or {}
        return f"{score.get('team1')}-{score.get('team2')}|{series.get('team1')}-{series.get('team2')}|{current.get('name')}"

    @staticmethod
    def _opponent(match: dict) -> str:
        t1 = match.get("team1") or {}
        t2 = match.get("team2") or {}
        if t1.get("id") == PINDOLZ_TEAM_ID:
            return t2.get("name") or "???"
        return t1.get("name") or "???"

    async def _edit_or_send(self, channel, embed, msg_id, ch_id, view=None):
        if msg_id and ch_id:
            try:
                ch = await self.get_channel_safe(ch_id) or channel
                msg = await ch.fetch_message(msg_id)
                await msg.edit(embed=embed, view=view)
                return msg.id, ch.id
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
        msg = await channel.send(embed=embed, view=view)
        return msg.id, channel.id

    @staticmethod
    def _ranks_json(table: list[dict]) -> str:
        ranks = {}
        for row in table:
            name = ((row.get("team") or {}).get("name") or "").upper()
            rank = row.get("rank")
            if name and isinstance(rank, int):
                ranks[name] = rank
        return json.dumps(ranks)

    def _rank_changes(self, table: list[dict]) -> dict[str, int]:
        try:
            prev = json.loads(db.get_config("table_prev_ranks") or "{}")
        except Exception:
            prev = {}
        changes = {}
        for row in table:
            name = ((row.get("team") or {}).get("name") or "").upper()
            rank = row.get("rank")
            old = prev.get(name)
            if name and isinstance(rank, int) and isinstance(old, int):
                changes[name] = old - rank
        return changes

    async def _react_result(self, ch_id, msg_id, match):
        if not feature_on("reactions"):
            return
        won = self.api.did_pindolz_win(match)
        if won is None or not ch_id or not msg_id:
            return
        try:
            ch = await self.get_channel_safe(ch_id)
            if not ch:
                return
            msg = await ch.fetch_message(msg_id)
            await msg.add_reaction("🎉" if won else "😢")
        except Exception as e:
            print(f"[react] {e}")

    @tasks.loop(time=TABLE_UPDATE_TIMES)
    async def table_update(self):
        await self._run_table_update()

    @table_update.before_loop
    async def before_table(self):
        await self.wait_until_ready()

    async def _run_table_update(self):
        channel = await self.get_channel_safe(self._table_channel_id())
        if not channel:
            return
        try:
            table = await asyncio.to_thread(self.api.get_division6_table)
        except Exception as e:
            print(f"[table] API error: {e}")
            return
        if not table:
            return
        last = db.get_config("table_last_ranks")
        if last:
            db.set_config("table_prev_ranks", last)
        changes = self._rank_changes(table)
        db.set_config("table_last_ranks", self._ranks_json(table))
        emb = embeds.standings_embed(table, changes=changes)
        msg_id, ch_id = self._table_msg()
        new_msg_id, new_ch_id = await self._edit_or_send(channel, emb, msg_id, ch_id, view=refresh_view("tabela"))
        db.set_config("msg_table_id", str(new_msg_id))
        db.set_config("msg_table_ch", str(new_ch_id))
        if feature_on("rank"):
            d = changes.get("PINDOLZ", 0)
            if d:
                prow = next((r for r in table if ((r.get("team") or {}).get("name") or "").upper() == "PINDOLZ"), None)
                new_rank = prow.get("rank") if prow else None
                main_ch = await self.get_channel_safe(self._main_channel_id())
                if main_ch and isinstance(new_rank, int):
                    try:
                        await main_ch.send(embed=embeds.rank_change_embed(new_rank + d, new_rank, prow.get("points")))
                    except Exception as e:
                        print(f"[rank] send error: {e}")
        print(f"[table] zaktualizowano o {datetime.now(TZ).strftime('%H:%M')}")

    @tasks.loop(minutes=10)
    async def daily_check(self):
        await self._run_daily_check()

    @daily_check.before_loop
    async def before_daily(self):
        await self.wait_until_ready()

    async def _run_daily_check(self):
        channel = await self.get_channel_safe(self._main_channel_id())
        if not channel:
            return
        try:
            history = await asyncio.to_thread(self.api.get_pindolz_history)
            upcoming = await asyncio.to_thread(self.api.get_pindolz_upcoming)
        except Exception as e:
            print(f"[daily] API error: {e}")
            return
        now = datetime.now(TZ)
        form = self.api.get_form(history, limit=5)
        standing = None
        try:
            standing = self.api.get_pindolz_standing()
        except Exception:
            pass
        cutoff = now - timedelta(days=14)
        for m in history:
            mid = m.get("id")
            if mid is None:
                continue
            date_s = m.get("matchDate")
            if date_s:
                try:
                    md = datetime.strptime(date_s, "%Y-%m-%d").replace(tzinfo=TZ)
                    if md < cutoff and not (db.get_match(mid) or {}).get("notified_result"):
                        score = m.get("score") or {}
                        db.upsert_match(mid, match_date=date_s, match_time=m.get("matchTime"), division=m.get("division"), opponent=self._opponent(m), status="finished", score_team1=score.get("team1"), score_team2=score.get("team2"), winner_team_id=m.get("winnerTeamId"), finished_at=datetime.utcnow().isoformat(), notified_result=1)
                        continue
                except Exception:
                    pass
            row = db.get_match(mid)
            score = m.get("score") or {}
            if row and row.get("notified_result"):
                old_s1, old_s2 = row.get("score_team1"), row.get("score_team2")
                new_s1, new_s2 = score.get("team1"), score.get("team2")
                if (old_s1, old_s2) != (new_s1, new_s2) and new_s1 is not None:
                    orig = db.get_config(f"result_orig_{mid}")
                    if not orig and old_s1 is not None and old_s2 is not None:
                        orig = f"{old_s1}:{old_s2}"
                        db.set_config(f"result_orig_{mid}", orig)
                    corr = orig if orig and orig != f"{new_s1}:{new_s2}" else None
                    msg_id, ch_id = await self._edit_or_send(channel, embeds.result_embed(m, form=form, standing=standing, correction=corr), row.get("msg_result_id"), row.get("msg_result_ch"), view=gg_view(mid))
                    db.upsert_match(mid, score_team1=new_s1, score_team2=new_s2, winner_team_id=m.get("winnerTeamId"), msg_result_id=msg_id, msg_result_ch=ch_id, status="finished")
                continue
            msg_id, ch_id = await self._edit_or_send(channel, embeds.result_embed(m, form=form, standing=standing), None, None, view=gg_view(mid))
            await self._react_result(ch_id, msg_id, m)
            await self._post_win_gif(ch_id, m)
            db.upsert_match(mid, match_date=m.get("matchDate"), match_time=m.get("matchTime"), division=m.get("division"), opponent=self._opponent(m), status="finished", score_team1=score.get("team1"), score_team2=score.get("team2"), winner_team_id=m.get("winnerTeamId"), finished_at=datetime.utcnow().isoformat(), notified_result=1, msg_result_id=msg_id, msg_result_ch=ch_id)
            if row and row.get("msg_live_id"):
                try:
                    live_ch = await self.get_channel_safe(row.get("msg_live_ch"))
                    if live_ch:
                        await self._edit_or_send(live_ch, embeds.match_ended_embed(m, form=form, standing=standing), row.get("msg_live_id"), row.get("msg_live_ch"))
                except Exception:
                    pass
        for m in upcoming:
            mid = m.get("id")
            if mid is None:
                continue
            match_date = m.get("matchDate")
            match_time = (m.get("matchTime") or "00:00:00")[:8]
            try:
                dt = datetime.strptime(f"{match_date} {match_time}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)
            except Exception:
                dt = None
            if dt and not (now <= dt <= now + timedelta(hours=48)):
                continue
            row = db.get_match(mid)
            opponent = self._opponent(m)
            if row and row.get("notified_upcoming"):
                date_changed = row.get("match_date") != m.get("matchDate") or (row.get("match_time") or "")[:5] != (m.get("matchTime") or "")[:5]
                opp_changed = row.get("opponent") != opponent
                if date_changed or opp_changed:
                    msg_id, ch_id = await self._edit_or_send(channel, embeds.single_upcoming_embed(m), row.get("msg_upcoming_id"), row.get("msg_upcoming_ch"), view=remind_view(mid))
                    if date_changed:
                        try:
                            await channel.send(embed=embeds.schedule_changed_embed(m, row.get("match_date"), row.get("match_time")))
                        except Exception as e:
                            print(f"[schedule] send error: {e}")
                    db.upsert_match(mid, match_date=m.get("matchDate"), match_time=m.get("matchTime"), division=m.get("division"), opponent=opponent, msg_upcoming_id=msg_id, msg_upcoming_ch=ch_id)
                continue
            msg_id, ch_id = await self._edit_or_send(channel, embeds.single_upcoming_embed(m), None, None, view=remind_view(mid))
            db.upsert_match(mid, match_date=m.get("matchDate"), match_time=m.get("matchTime"), division=m.get("division"), opponent=opponent, status="scheduled", notified_upcoming=1, msg_upcoming_id=msg_id, msg_upcoming_ch=ch_id)

    PREMATCH_MINUTES = 30

    def _upcoming_cached(self) -> list:
        now = datetime.now(TZ)
        if self._upcoming_cache and (now - self._upcoming_cache[0]) < timedelta(minutes=10):
            return self._upcoming_cache[1]
        data = self.api.get_pindolz_upcoming()
        self._upcoming_cache = (now, data)
        return data

    @tasks.loop(minutes=1)
    async def prematch_check(self):
        channel = await self.get_channel_safe(self._main_channel_id())
        try:
            upcoming = self._upcoming_cached()
        except Exception as e:
            print(f"[prematch] API error: {e}")
            return
        now = datetime.now(TZ)
        for m in upcoming:
            mid = m.get("id")
            dt = embeds._match_dt(m)
            if mid is None or dt is None:
                continue
            delta = dt - now
            if timedelta(0) < delta <= timedelta(minutes=self.PREMATCH_MINUTES):
                stage = self.PREMATCH_MINUTES
            elif timedelta(minutes=self.PREMATCH_MINUTES) < delta <= timedelta(minutes=60):
                stage = 60
            else:
                continue
            key = f"prematch_{mid}" if stage == self.PREMATCH_MINUTES else f"prematch60_{mid}"
            if db.get_config(key):
                continue
            db.set_config(key, "1")
            form = standing = opp_standing = None
            try:
                form = self.api.get_form(limit=5)
            except Exception:
                pass
            try:
                table = self.api.get_division6_table()
                opp_name = self._opponent(m).upper()
                for row in table:
                    name = ((row.get("team") or {}).get("name") or "").upper()
                    if name == "PINDOLZ":
                        standing = row
                    elif name == opp_name:
                        opp_standing = row
            except Exception:
                pass
            if stage == self.PREMATCH_MINUTES:
                await self._send_reminder_dms(m)
            if channel and feature_on("prematch" if stage == self.PREMATCH_MINUTES else "prematch1h"):
                try:
                    await channel.send(embed=embeds.prematch_embed(m, form=form, standing=standing, opp_standing=opp_standing, minutes=stage, lineup=self._lineup_ids(mid), nicks=_player_nicks()))
                    print(f"[prematch] wysłano przypomnienie ({stage} min) o meczu {mid}")
                except Exception as e:
                    db.set_config(key, None)
                    print(f"[prematch] send error: {e}")

    @prematch_check.before_loop
    async def before_prematch(self):
        await self.wait_until_ready()

    @tasks.loop(seconds=LIVE_INTERVAL_IDLE)
    async def live_check(self):
        await self._run_live_check()

    @live_check.before_loop
    async def before_live(self):
        await self.wait_until_ready()

    async def _run_live_check(self):
        if not feature_on("live"):
            return
        channel = await self.get_channel_safe(self._live_channel_id())
        if not channel:
            self.live_check.change_interval(seconds=LIVE_INTERVAL_IDLE)
            return
        try:
            lives = await asyncio.to_thread(self.api.get_pindolz_live)
            self._live_errors = 0
        except Exception as e:
            self._live_errors = getattr(self, "_live_errors", 0) + 1
            print(f"[live] API error ({self._live_errors}): {e}")
            backoff = min(30, LIVE_INTERVAL_IDLE * (1 + self._live_errors // 2))
            if self.live_check.seconds != backoff:
                self.live_check.change_interval(seconds=backoff)
            return
        target = LIVE_INTERVAL_ACTIVE if lives else LIVE_INTERVAL_IDLE
        if self.live_check.seconds != target:
            self.live_check.change_interval(seconds=target)
        current_ids = set()
        for m in lives:
            mid = m.get("id")
            if mid is None:
                continue
            current_ids.add(mid)
            row = db.get_match(mid)
            key = self._score_key(m)
            if not row or not row.get("msg_live_id"):
                emb = embeds.live_embed(m)
                view = None
                try:
                    guild = getattr(channel, "guild", None)
                    if guild:
                        view = LiveChannelView(guild.id, channel.id)
                except Exception:
                    view = None
                msg = await channel.send(embed=emb, view=view)
                db.upsert_match(mid, match_date=m.get("matchDate"), match_time=m.get("matchTime"), division=m.get("division"), opponent=self._opponent(m), status="live", updated_at=m.get("updatedAt"), live_score_key=key, msg_live_id=msg.id, msg_live_ch=channel.id)
                if feature_on("thread"):
                    await self._create_live_thread(msg, m)
                continue
            if key != row.get("live_score_key") or m.get("updatedAt") != row.get("updated_at"):
                msg_id, ch_id = await self._edit_or_send(channel, embeds.live_embed(m), row.get("msg_live_id"), row.get("msg_live_ch"))
                db.upsert_match(mid, status="live", updated_at=m.get("updatedAt"), live_score_key=key, msg_live_id=msg_id, msg_live_ch=ch_id)
                if key != row.get("live_score_key") and feature_on("thread"):
                    await self._post_thread_update(mid, self._live_line(m))
        known_live = db.get_live_matches()
        for row in known_live:
            mid = row["match_id"]
            if mid in current_ids:
                continue
            match_data = None
            history = []
            try:
                history = await asyncio.to_thread(self.api.get_pindolz_history)
                for h in history:
                    if h.get("id") == mid:
                        match_data = h
                        break
            except Exception:
                pass
            if match_data:
                form = self.api.get_form(history, limit=5) if history else None
                standing = None
                try:
                    standing = self.api.get_pindolz_standing()
                except Exception:
                    pass
                score = match_data.get("score") or {}
                await self._edit_or_send(channel, embeds.match_ended_embed(match_data, form=form, standing=standing), row.get("msg_live_id"), row.get("msg_live_ch"))
                await self._post_thread_update(mid, f"🏁 **Koniec meczu:** {embeds._team_name(match_data, 'team1')} **{embeds._score_str(match_data)}** {embeds._team_name(match_data, 'team2')}", archive=True)
                await self._finish_event(mid)
                if not row.get("notified_result"):
                    main_ch = await self.get_channel_safe(self._main_channel_id())
                    if main_ch:
                        msg_id, ch_id = await self._edit_or_send(main_ch, embeds.result_embed(match_data, form=form, standing=standing), None, None, view=gg_view(mid))
                        await self._react_result(ch_id, msg_id, match_data)
                        await self._post_win_gif(ch_id, match_data)
                        db.upsert_match(mid, notified_result=1, msg_result_id=msg_id, msg_result_ch=ch_id)
                db.upsert_match(mid, status="finished", score_team1=score.get("team1"), score_team2=score.get("team2"), winner_team_id=match_data.get("winnerTeamId"), finished_at=datetime.utcnow().isoformat())
            else:
                await self._post_thread_update(mid, "🏁 **Mecz zakończony.**", archive=True)
                await self._finish_event(mid)
                db.mark_finished(mid)

    @tasks.loop(time=time(20, 0, tzinfo=TZ))
    async def weekly_summary(self):
        if datetime.now(TZ).weekday() != 6:
            return
        channel = await self.get_channel_safe(self._main_channel_id())
        if not channel:
            return
        try:
            history = self.api.get_pindolz_history()
        except Exception as e:
            print(f"[weekly] API error: {e}")
            return
        now = datetime.now(TZ)
        week_ago = now - timedelta(days=7)
        week_matches, wins, losses = [], 0, 0
        for m in history:
            date_s = m.get("matchDate")
            if not date_s:
                continue
            try:
                md = datetime.strptime(date_s, "%Y-%m-%d").replace(tzinfo=TZ)
            except Exception:
                continue
            if md < week_ago:
                continue
            week_matches.append(m)
            w = self.api.did_pindolz_win(m)
            if w is True:
                wins += 1
            elif w is False:
                losses += 1
        standing = None
        try:
            standing = self.api.get_pindolz_standing()
        except Exception:
            pass
        await channel.send(embed=embeds.weekly_summary_embed(week_matches, wins, losses, standing))
        print("[weekly] wysłano podsumowanie tygodnia")

    @weekly_summary.before_loop
    async def before_weekly(self):
        await self.wait_until_ready()

    # ---------- STATUS BOTA ----------
    @staticmethod
    def _pl_plural(n: int, one: str, few: str, many: str) -> str:
        if n == 1:
            return one
        if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
            return few
        return many

    @staticmethod
    def _time_left(delta: timedelta) -> str:
        mins = max(1, int(delta.total_seconds() // 60))
        if mins >= 1440:
            d = mins // 1440
            return f"{d} {'dzień' if d == 1 else 'dni'}"
        if mins >= 60:
            return f"{mins // 60} godz."
        return f"{mins} min"

    async def _build_statuses(self) -> tuple[list[str], bool]:
        """Zwraca (lista tekstów statusu do rotacji, czy trwa LIVE)."""
        now = datetime.now(TZ)

        # 3. LIVE – ma pierwszeństwo
        try:
            lives = await asyncio.to_thread(self.api.get_pindolz_live)
        except Exception:
            lives = []
        if lives:
            m = lives[0]
            t1 = (m.get("team1") or {}).get("name") or "???"
            t2 = (m.get("team2") or {}).get("name") or "???"
            series = m.get("seriesScore") or {}
            cur = (m.get("currentMap") or {}).get("score") or {}
            s1, s2 = series.get("team1") or 0, series.get("team2") or 0
            if s1 + s2 == 0:
                s1, s2 = cur.get("team1") or 0, cur.get("team2") or 0
            return [f"🔴 LIVE: {t1} {s1}:{s2} {t2}"[:128]], True

        statuses: list[str] = []

        # 1 + 2. Odliczanie i „dziś gramy"
        try:
            upcoming = await asyncio.to_thread(self.api.get_pindolz_upcoming)
        except Exception:
            upcoming = []
        nxt = None
        for m in upcoming:
            dt = embeds._match_dt(m)
            if dt and dt > now and (nxt is None or dt < nxt[0]):
                nxt = (dt, m)
        if nxt:
            dt, m = nxt
            opp = self._opponent(m)
            if dt.date() == now.date():
                statuses.append(f"🎮 Dziś o {dt.strftime('%H:%M')} vs {opp}")
            statuses.append(f"⏳ PINDOLZ vs {opp} za {self._time_left(dt - now)}")

        # 8. Seria wygranych / porażek
        try:
            history = await asyncio.to_thread(self.api.get_pindolz_history)
        except Exception:
            history = []
        streak = 0
        first = None
        for m in history:
            winner = m.get("winnerTeamId")
            if winner is None:
                break
            won = winner == PINDOLZ_TEAM_ID
            if first is None:
                first = won
            if won != first:
                break
            streak += 1
        if streak >= 2:
            if first:
                word = self._pl_plural(streak, "wygrana", "wygrane", "wygranych")
                statuses.append(f"🔥 {streak} {word} z rzędu")
            else:
                word = self._pl_plural(streak, "porażka", "porażki", "porażek")
                statuses.append(f"📉 {streak} {word} z rzędu")

        # Winrate i strata do lidera (z tabeli)
        try:
            table = await asyncio.to_thread(self.api.get_division6_table)
        except Exception:
            table = []
        us = next((r for r in table if ((r.get("team") or {}).get("name") or "").upper() == "PINDOLZ"), None)
        if us:
            w, l = us.get("wins") or 0, us.get("losses") or 0
            if w + l > 0:
                statuses.append(f"📈 Winrate: {round(w / (w + l) * 100)}%")
            leader_pts = max((r.get("points") or 0 for r in table), default=None)
            our_pts = us.get("points")
            if leader_pts is not None and our_pts is not None:
                gap = leader_pts - our_pts
                if us.get("rank") == 1:
                    statuses.append("👑 PINDOLZ prowadzi w tabeli")
                elif gap > 0:
                    statuses.append(f"📊 Do lidera brakuje {gap} pkt")
                else:
                    statuses.append("📊 Remis punktowy z liderem")

        # Losowe hasło
        if STATUS_PHRASES:
            statuses.append(random.choice(STATUS_PHRASES))

        if not statuses:
            statuses.append("👀 PINDOLZ · /pomoc")
        return [s[:128] for s in statuses], False

    @tasks.loop(seconds=30)
    async def status_loop(self):
        if not feature_on("status"):
            if self._status_current is not None:
                try:
                    await self.change_presence(status=discord.Status.online, activity=None)
                except Exception:
                    pass
                self._status_current = None
            return
        try:
            statuses, is_live = await self._build_statuses()
        except Exception as e:
            print(f"[status] error: {e}")
            return
        text = statuses[self._status_idx % len(statuses)]
        self._status_idx += 1
        # 12. dnd (czerwona kropka) w trakcie LIVE, w pozostałych chwilach online
        state = discord.Status.dnd if is_live else discord.Status.online
        if self._status_current == (text, state):
            return
        try:
            await self.change_presence(status=state, activity=discord.CustomActivity(name=text))
            self._status_current = (text, state)
        except Exception as e:
            print(f"[status] change_presence error: {e}")

    @status_loop.before_loop
    async def before_status(self):
        await self.wait_until_ready()

    # ---------- PRZYPOMNIENIE „PRZYPOMNIJ MI” (DM) ----------
    async def toggle_reminder(self, interaction: discord.Interaction, mid: int):
        key = f"remind_{mid}"
        try:
            users = json.loads(db.get_config(key) or "[]")
        except Exception:
            users = []
        row = db.get_match(mid) or {}
        dt = embeds._match_dt({"matchDate": row.get("match_date"), "matchTime": row.get("match_time")}) if row else None
        now = datetime.now(TZ)
        if dt and dt <= now:
            await interaction.response.send_message("Ten mecz już się rozpoczął.", ephemeral=True)
            return
        uid = interaction.user.id
        if uid in users:
            users.remove(uid)
            db.set_config(key, json.dumps(users))
            await interaction.response.send_message("🔕 Przypomnienie anulowane.", ephemeral=True)
            return
        users.append(uid)
        db.set_config(key, json.dumps(users))
        extra = ""
        if dt and dt - now <= timedelta(minutes=self.PREMATCH_MINUTES):
            extra = "\n⚠️ Do meczu zostało mniej niż 30 minut, więc przypomnienie może już nie przyjść."
        await interaction.response.send_message(
            "🔔 Wyślę Ci wiadomość prywatną 30 minut przed meczem.\n"
            "Upewnij się, że masz włączone wiadomości prywatne od członków serwera. Kliknij ponownie, aby anulować." + extra,
            ephemeral=True,
        )

    async def _send_reminder_dms(self, match: dict):
        mid = match.get("id")
        if mid is None or db.get_config(f"remind_sent_{mid}"):
            return
        db.set_config(f"remind_sent_{mid}", "1")
        try:
            users = json.loads(db.get_config(f"remind_{mid}") or "[]")
        except Exception:
            users = []
        for uid in users:
            try:
                user = self.get_user(uid) or await self.fetch_user(uid)
                await user.send(
                    content="🔔 **Przypomnienie:** mecz PINDOLZ zaczyna się za około 30 minut!",
                    embed=embeds.prematch_embed(match, lineup=self._lineup_ids(match.get("id")), nicks=_player_nicks()),
                )
            except Exception as e:
                print(f"[remind] DM do {uid}: {e}")

    # ---------- ANKIETA DOSTĘPNOŚCI ----------
    def _poll_roles(self) -> list[int]:
        try:
            return [int(x) for x in json.loads(db.get_config("poll_roles") or "[]")]
        except Exception:
            return []

    def _poll_info(self, mid: int) -> dict:
        try:
            return json.loads(db.get_config(f"poll_info_{mid}") or "{}")
        except Exception:
            return {}

    def _poll_votes(self, mid: int) -> dict:
        try:
            return json.loads(db.get_config(f"poll_votes_{mid}") or "{}")
        except Exception:
            return {}

    async def handle_poll_vote(self, interaction: discord.Interaction, mid: int, vote: str):
        info = self._poll_info(mid)
        ts = info.get("ts")
        if ts and datetime.now(TZ).timestamp() >= ts:
            await interaction.response.send_message("Ankieta zakończona, mecz już się rozpoczął.", ephemeral=True)
            return
        votes = self._poll_votes(mid)
        uid = str(interaction.user.id)
        if votes.get(uid) == vote:
            votes.pop(uid, None)
        else:
            votes[uid] = vote
        db.set_config(f"poll_votes_{mid}", json.dumps(votes))
        await interaction.response.edit_message(embed=embeds.poll_embed(info, votes))

    @tasks.loop(minutes=5)
    async def poll_check(self):
        if not feature_on("polls"):
            return
        channel = await self.get_channel_safe(db.get_config_int("poll_channel_id"))
        if not channel:
            return
        try:
            upcoming = await asyncio.to_thread(self.api.get_pindolz_upcoming)
        except Exception as e:
            print(f"[poll] API error: {e}")
            return
        now = datetime.now(TZ)
        nxt = None
        for m in upcoming:
            dt = embeds._match_dt(m)
            # ankieta tylko gdy ustalona jest i data, i godzina
            if m.get("id") is None or dt is None or not m.get("matchDate") or not m.get("matchTime") or dt <= now:
                continue
            if nxt is None or dt < nxt[0]:
                nxt = (dt, m)
        if not nxt:
            return
        dt, m = nxt
        mid = m["id"]
        info = {"opp": self._opponent(m), "ts": int(dt.timestamp()), "div": m.get("division"), "bo": m.get("bestOf")}
        mentions = " ".join(f"<@&{r}>" for r in self._poll_roles())
        allowed = discord.AllowedMentions(roles=True, users=False, everyone=False)
        existing = db.get_config(f"poll_msg_{mid}")
        if not existing:
            try:
                msg = await channel.send(
                    content=mentions or None,
                    embed=embeds.poll_embed(info, {}),
                    view=poll_view(mid),
                    allowed_mentions=allowed,
                )
            except Exception as e:
                print(f"[poll] send error: {e}")
                return
            db.set_config(f"poll_msg_{mid}", f"{channel.id}:{msg.id}")
            _index_add("poll_index", mid)
            db.set_config(f"poll_info_{mid}", json.dumps(info))
            db.set_config(f"poll_votes_{mid}", "{}")
            print(f"[poll] wysłano ankietę dla meczu {mid}")
            return
        old = self._poll_info(mid)
        if old.get("ts") == info["ts"] and old.get("opp") == info["opp"]:
            return
        try:
            ch_id, msg_id = (int(x) for x in existing.split(":"))
            ch = await self.get_channel_safe(ch_id) or channel
            msg = await ch.fetch_message(msg_id)
            await msg.edit(embed=embeds.poll_embed(info, self._poll_votes(mid)), view=poll_view(mid))
            db.set_config(f"poll_info_{mid}", json.dumps(info))
            if old.get("ts") != info["ts"]:
                text = "📅 **Zmiana terminu meczu.** Zagłosuj ponownie, jeśli Twoja dostępność się zmieniła."
                await ch.send(content=f"{mentions} {text}".strip(), allowed_mentions=allowed)
        except Exception as e:
            print(f"[poll] update error: {e}")

    @poll_check.before_loop
    async def before_poll(self):
        await self.wait_until_ready()

    # ---------- WĄTEK LIVE ----------
    @staticmethod
    def _live_line(m: dict) -> str:
        t1 = (m.get("team1") or {}).get("name") or "???"
        t2 = (m.get("team2") or {}).get("name") or "???"
        cur = m.get("currentMap") or {}
        cs = cur.get("score") or {}
        series = m.get("seriesScore") or {}
        line = f"🗺️ **{cur.get('name') or '?'}** · {t1} **{cs.get('team1', 0)}:{cs.get('team2', 0)}** {t2}"
        if series.get("team1") is not None:
            line += f" · seria **{series.get('team1', 0)}:{series.get('team2', 0)}**"
        return line

    async def _create_live_thread(self, msg, match: dict):
        mid = match.get("id")
        try:
            thread = await msg.create_thread(name=f"LIVE PINDOLZ vs {self._opponent(match)}"[:100], auto_archive_duration=1440)
            db.set_config(f"live_thread_{mid}", str(thread.id))
            await thread.send(f"🔴 **Start meczu!**\n{self._live_line(match)}")
        except Exception as e:
            print(f"[thread] create error: {e}")

    async def _post_thread_update(self, mid: int, text: str, archive: bool = False):
        tid = db.get_config_int(f"live_thread_{mid}")
        if not tid:
            return
        try:
            thread = await self.get_channel_safe(tid)
            if not thread:
                return
            await thread.send(text)
            if archive:
                await thread.edit(archived=True)
        except Exception as e:
            print(f"[thread] update error: {e}")

    # ---------- WYDARZENIE SERWERA DISCORD ----------
    @tasks.loop(minutes=5)
    async def event_check(self):
        if not feature_on("events"):
            return
        channel = await self.get_channel_safe(self._main_channel_id())
        guild = getattr(channel, "guild", None)
        if not guild:
            return
        try:
            upcoming = await asyncio.to_thread(self.api.get_pindolz_upcoming)
        except Exception as e:
            print(f"[event] API error: {e}")
            return
        now = datetime.now(TZ)
        nxt = None
        for m in upcoming:
            dt = embeds._match_dt(m)
            if m.get("id") is None or dt is None or not m.get("matchDate") or not m.get("matchTime") or dt <= now:
                continue
            if nxt is None or dt < nxt[0]:
                nxt = (dt, m)
        if not nxt:
            return
        dt, m = nxt
        mid = m["id"]
        name = f"PINDOLZ vs {self._opponent(m)}"[:100]
        end = dt + timedelta(hours=2)
        desc = f"{m.get('division') or ''} · Bo{m.get('bestOf') or '?'}\nWyniki na żywo na kanale LIVE.".strip()
        names = self._lineup_names(guild, self._lineup_ids(mid))
        if names:
            desc += "\nSkład: " + ", ".join(names)
        desc = desc[:1000]
        eid = db.get_config_int(f"event_{mid}")
        if eid:
            try:
                ev = guild.get_scheduled_event(eid) or await guild.fetch_scheduled_event(eid)
            except discord.NotFound:
                return  # usunięte ręcznie – nie tworzymy ponownie
            except Exception as e:
                print(f"[event] fetch error: {e}")
                return
            if ev.status != discord.EventStatus.scheduled:
                return
            if abs(ev.start_time.timestamp() - dt.timestamp()) > 30 or ev.name != name or (ev.description or "") != desc:
                try:
                    await ev.edit(name=name, start_time=dt, end_time=end, description=desc)
                    print(f"[event] zaktualizowano wydarzenie meczu {mid}")
                except Exception as e:
                    print(f"[event] edit error: {e}")
            return
        try:
            ev = await guild.create_scheduled_event(
                name=name, start_time=dt, end_time=end, location="StarterLeague · online", description=desc,
            )
        except Exception as e:
            print(f"[event] create error: {e}")
            return
        db.set_config(f"event_{mid}", str(ev.id))
        print(f"[event] utworzono wydarzenie meczu {mid}")

    @event_check.before_loop
    async def before_event_check(self):
        await self.wait_until_ready()

    async def _finish_event(self, mid: int):
        eid = db.get_config_int(f"event_{mid}")
        if not eid:
            return
        try:
            channel = await self.get_channel_safe(self._main_channel_id())
            guild = getattr(channel, "guild", None)
            if not guild:
                return
            ev = guild.get_scheduled_event(eid) or await guild.fetch_scheduled_event(eid)
            if ev.status == discord.EventStatus.active:
                await ev.edit(status=discord.EventStatus.completed)
        except Exception as e:
            print(f"[event] finish error: {e}")

    # ---------- GIF PO WYGRANEJ ----------
    async def _post_win_gif(self, ch_id, match: dict):
        if not feature_on("gif") or not ch_id:
            return
        if self.api.did_pindolz_win(match) is not True or embeds._is_walkover(match):
            return
        dt = embeds._match_dt(match)
        if dt and dt < datetime.now(TZ) - timedelta(hours=36):
            return  # nie spamujemy GIF-ami przy nadrabianiu starszych wyników
        gifs = _win_gifs()
        if not gifs:
            return
        try:
            last = int(db.get_config("win_gif_last") or -1)
        except ValueError:
            last = -1
        choices = [i for i in range(len(gifs)) if i != last] or [0]
        idx = random.choice(choices)
        db.set_config("win_gif_last", str(idx))
        try:
            ch = await self.get_channel_safe(ch_id)
            if ch:
                await ch.send(gifs[idx])
        except Exception as e:
            print(f"[gif] send error: {e}")

    # ---------- SKŁAD NA MECZ ----------
    def _lineup_ids(self, mid) -> list[int]:
        if mid is None:
            return []
        try:
            return [int(x) for x in json.loads(db.get_config(f"lineup_{mid}") or "[]")]
        except Exception:
            return []

    @staticmethod
    def _lineup_names(guild, ids: list[int]) -> list[str]:
        names = []
        nicks = _player_nicks()
        for uid in ids:
            member = guild.get_member(uid) if guild else None
            if member:
                nick = nicks.get(uid)
                names.append(f"{member.display_name} ({nick})" if nick else member.display_name)
        return names

    @staticmethod
    def _next_match(upcoming: list[dict]):
        now = datetime.now(TZ)
        nxt = None
        for m in upcoming:
            dt = embeds._match_dt(m)
            if m.get("id") is None or dt is None or dt <= now:
                continue
            if nxt is None or dt < nxt[0]:
                nxt = (dt, m)
        return nxt

    # ---------- NOWA WERSJA NA GITHUBIE ----------
    @staticmethod
    def _ver_tuple(v: str) -> tuple:
        try:
            return tuple(int(x) for x in v.strip().lstrip("v").split("."))
        except Exception:
            return ()

    @staticmethod
    def _fetch_remote_version() -> str | None:
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/VERSION"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.text.strip()

    @tasks.loop(hours=6)
    async def update_check(self):
        if not feature_on("updates"):
            return
        try:
            remote = await asyncio.to_thread(self._fetch_remote_version)
        except Exception as e:
            print(f"[update] błąd sprawdzania wersji: {e}")
            return
        rt = self._ver_tuple(remote or "")
        if not rt or rt <= self._ver_tuple(BOT_VERSION):
            return
        if db.get_config("update_notified") == remote:
            return
        db.set_config("update_notified", remote)
        await self._dm_owner(
            f"🆕 **Nowa wersja bota na GitHubie: {remote}** (uruchomiona: {BOT_VERSION}).\n"
            "Zrestartuj serwer na hostingu, aby pobrać zmiany (jeśli masz włączone Auto Update) "
            "albo wgraj nowe pliki ręcznie."
        )

    @update_check.before_loop
    async def before_update_check(self):
        await self.wait_until_ready()

    # ---------- KAPITAN (DM) ----------
    async def _dm_captain(self, content: str | None = None, embed: discord.Embed | None = None) -> bool:
        try:
            cid = db.get_config_int("captain_id")
            if cid:
                user = self.get_user(cid) or await self.fetch_user(cid)
            else:
                user = (await self.application_info()).owner
            await user.send(content=content, embed=embed)
            return True
        except Exception as e:
            print(f"[captain] nie udało się wysłać DM: {e}")
            return False

    # ---------- NOWY MECZ / USTALONY TERMIN ----------
    @tasks.loop(minutes=2)
    async def schedule_watch(self):
        if not feature_on("newmatch"):
            return
        channel = await self.get_channel_safe(self._main_channel_id())
        if not channel:
            return
        try:
            upcoming = await asyncio.to_thread(self.api.get_pindolz_upcoming)
        except Exception as e:
            print(f"[schedule] API error: {e}")
            return
        raw = db.get_config("seen_matches")
        now = datetime.now(TZ)
        has_date = lambda m: bool(m.get("matchDate") and m.get("matchTime"))
        if raw is None:  # pierwszy start: zapamiętaj istniejące mecze, nic nie ogłaszaj
            ids = [m["id"] for m in upcoming if m.get("id") is not None]
            db.set_config("seen_matches", json.dumps(ids[-300:]))
            db.set_config("dated_matches", json.dumps([m["id"] for m in upcoming if m.get("id") is not None and has_date(m)][-300:]))
            return
        seen = set(_index_list("seen_matches"))
        dated = set(_index_list("dated_matches"))
        for m in upcoming:
            mid = m.get("id")
            if mid is None:
                continue
            dt = embeds._match_dt(m) if has_date(m) else None
            if dt and dt <= now:
                seen.add(mid)
                dated.add(mid)
                continue
            if mid not in seen:
                try:
                    await channel.send(embed=embeds.new_match_embed(m))
                except Exception as e:
                    print(f"[schedule] send error: {e}")
                    continue
                seen.add(mid)
                if has_date(m):
                    dated.add(mid)
            elif has_date(m) and mid not in dated:
                try:
                    await channel.send(embed=embeds.new_match_embed(m, dated=True))
                except Exception as e:
                    print(f"[schedule] send error: {e}")
                    continue
                dated.add(mid)
        db.set_config("seen_matches", json.dumps(sorted(seen)[-300:]))
        db.set_config("dated_matches", json.dumps(sorted(dated)[-300:]))

    @schedule_watch.before_loop
    async def before_schedule_watch(self):
        await self.wait_until_ready()

    # ---------- OPÓŹNIONY START MECZU ----------
    @tasks.loop(minutes=2)
    async def delay_check(self):
        if not feature_on("delay"):
            return
        try:
            upcoming = await asyncio.to_thread(self._upcoming_cached)
        except Exception as e:
            print(f"[delay] API error: {e}")
            return
        now = datetime.now(TZ)
        cands = []
        for m in upcoming:
            mid = m.get("id")
            dt = embeds._match_dt(m) if (m.get("matchDate") and m.get("matchTime")) else None
            if mid is None or dt is None or db.get_config(f"delay_{mid}"):
                continue
            late = (now - dt).total_seconds() / 60
            if 15 <= late <= 180:
                cands.append((int(late), m))
        if not cands:
            return
        try:
            lives = await asyncio.to_thread(self.api.get_pindolz_live)
        except Exception:
            return  # bez pewności, czy trwa LIVE, nie alarmujemy
        live_ids = {x.get("id") for x in lives}
        for late, m in cands:
            mid = m["id"]
            if mid in live_ids or (db.get_match(mid) or {}).get("status") in ("live", "finished"):
                continue
            db.set_config(f"delay_{mid}", "1")
            emb = embeds.delay_embed(m, late)
            sent = await self._dm_captain(content="⏳ Mecz powinien już trwać, a LIVE nie widać.", embed=emb)
            if not sent:
                ch = await self.get_channel_safe(self._main_channel_id())
                if ch:
                    try:
                        await ch.send(embed=emb)
                    except Exception as e:
                        print(f"[delay] send error: {e}")
            print(f"[delay] alert o opóźnieniu meczu {mid} ({late} min)")

    @delay_check.before_loop
    async def before_delay_check(self):
        await self.wait_until_ready()

    # ---------- KARTA GRACZA ----------
    def _player_stats(self, uid: int) -> dict:
        now_ts = datetime.now(TZ).timestamp()
        yes = no = maybe = polls = 0
        for mid in _index_list("poll_index"):
            ts = self._poll_info(mid).get("ts")
            if ts and ts > now_ts:
                continue  # liczymy tylko zamknięte ankiety
            polls += 1
            vote = self._poll_votes(mid).get(str(uid))
            if vote == "yes":
                yes += 1
            elif vote == "no":
                no += 1
            elif vote == "maybe":
                maybe += 1
        lineups = _index_list("lineup_index")
        return {
            "polls": polls, "yes": yes, "no": no, "maybe": maybe,
            "lineups": len(lineups), "in_lineup": sum(1 for mid in lineups if uid in self._lineup_ids(mid)),
        }

    # ---------- RAPORT KAPITANA ----------
    async def _build_report(self, save_rank: bool = False) -> discord.Embed:
        now = datetime.now(TZ)
        sections: list[tuple[str, str]] = []
        warnings: list[str] = []
        try:
            upcoming = await asyncio.to_thread(self.api.get_pindolz_upcoming)
        except Exception:
            upcoming = []
            warnings.append("API nie odpowiada, dane mogą być niepełne.")
        dated, undated = [], []
        for m in upcoming:
            if m.get("id") is None:
                continue
            dt = embeds._match_dt(m) if (m.get("matchDate") and m.get("matchTime")) else None
            if dt is None:
                undated.append(m)
            elif dt > now:
                dated.append((dt, m))
        dated.sort(key=lambda x: x[0])
        lines = [f"<t:{int(dt.timestamp())}:F> · vs **{self._opponent(m)}**" for dt, m in dated[:3]]
        for m in undated[:3]:
            lines.append(f"⚠️ termin nieustalony · vs **{self._opponent(m)}**")
            warnings.append(f"Ustalcie termin meczu z {self._opponent(m)}.")
        sections.append(("📅 Najbliższe mecze", "\n".join(lines) or "Brak zaplanowanych meczów."))
        if dated:
            dt, m = dated[0]
            mid, opp = m["id"], self._opponent(m)
            if self._poll_info(mid):
                votes = list(self._poll_votes(mid).values())
                y, n, mb = votes.count("yes"), votes.count("no"), votes.count("maybe")
                sections.append(("🗳️ Ankieta (najbliższy mecz)", f"✅ {y} · ❌ {n} · ❔ {mb}"))
                if dt - now < timedelta(hours=48) and y == 0:
                    warnings.append(f"Nikt jeszcze nie potwierdził gry w meczu z {opp}.")
            elif not db.get_config_int("poll_channel_id"):
                warnings.append("Nie ustawiono kanału ankiet (`/setup-ankiety`).")
            else:
                sections.append(("🗳️ Ankieta (najbliższy mecz)", "Jeszcze nie wysłana."))
            lineup = self._lineup_ids(mid)
            if lineup:
                sections.append(("👥 Skład (najbliższy mecz)", " ".join(f"<@{u}>" for u in lineup)))
            else:
                warnings.append(f"Nie ustawiono składu na mecz z {opp} (`/sklad`).")
        try:
            history = await asyncio.to_thread(self.api.get_pindolz_history)
        except Exception:
            history = []
        week = [m for m in history if (embeds._match_dt(m) and now - embeds._match_dt(m) <= timedelta(days=7))]
        wins = sum(1 for m in week if m.get("winnerTeamId") == PINDOLZ_TEAM_ID)
        losses = sum(1 for m in week if m.get("winnerTeamId") not in (None, PINDOLZ_TEAM_ID))
        wlines = [
            f"{embeds._icon(embeds._result(m))} {embeds._team_name(m, 'team1')} {embeds._score_str(m)} {embeds._team_name(m, 'team2')}"
            for m in week[:5]
        ]
        sections.append(("📜 Ostatnie 7 dni", f"**{wins}W – {losses}L**" + ("\n" + "\n".join(wlines) if wlines else "\nBrak meczów.")))
        try:
            table = await asyncio.to_thread(self.api.get_division6_table)
        except Exception:
            table = []
        us = next((r for r in table if ((r.get("team") or {}).get("name") or "").upper() == "PINDOLZ"), None)
        if us and us.get("rank") is not None:
            rank = us["rank"]
            prev = db.get_config_int("report_rank_prev")
            delta = ""
            if prev and prev != rank:
                delta = f" · {'▲' if rank < prev else '▼'}{abs(prev - rank)} vs poprzedni raport"
            sections.append(("🏆 Tabela", f"{embeds._medal(rank)} **{rank}.** miejsce · **{us.get('points', '–')}** pkt{delta}"))
            if save_rank:
                db.set_config("report_rank_prev", str(rank))
        return embeds.captain_report_embed(sections, warnings)

    @tasks.loop(time=time(9, 0, tzinfo=TZ))
    async def captain_report(self):
        if datetime.now(TZ).weekday() != 0 or not feature_on("report"):
            return
        emb = await self._build_report(save_rank=True)
        await self._dm_captain(embed=emb)
        print("[report] wysłano raport kapitana")

    @captain_report.before_loop
    async def before_captain_report(self):
        await self.wait_until_ready()

    # ---------- ZAPLANOWANE WIADOMOŚCI ----------
    @tasks.loop(minutes=1)
    async def scheduled_messages(self):
        items = _sched_list()
        if not items:
            return
        now_ts = datetime.now(TZ).timestamp()
        due = sorted((i for i in items if i.get("ts", 0) <= now_ts), key=lambda i: i["ts"])
        if not due:
            return
        db.set_config("sched_msgs", json.dumps([i for i in items if i.get("ts", 0) > now_ts]))  # najpierw usuń, by nie wysłać dwa razy
        for it in due:
            text = it.get("text") or ""
            if now_ts - it["ts"] > 12 * 3600:
                await self._dm_owner(f"⏰ Pominięto zaplanowaną wiadomość #{it.get('id')} (bot był offline ponad 12 h): {text[:200]}")
                continue
            ch = await self.get_channel_safe(it.get("ch"))
            rid = it.get("role")
            try:
                if not ch:
                    raise RuntimeError("nie znaleziono kanału")
                await ch.send(
                    ((f"<@&{rid}> " if rid else "") + text)[:2000],
                    allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=[discord.Object(id=rid)] if rid else False),
                )
                print(f"[sched] wysłano zaplanowaną wiadomość #{it.get('id')}")
            except Exception as e:
                print(f"[sched] send error: {e}")
                await self._dm_owner(f"⏰ Nie udało się wysłać zaplanowanej wiadomości #{it.get('id')}: {e}\n{text[:200]}")

    @scheduled_messages.before_loop
    async def before_scheduled_messages(self):
        await self.wait_until_ready()

    # ---------- ALERT O AWARII API ----------
    async def _dm_owner(self, text: str):
        try:
            info = await self.application_info()
            await info.owner.send(text)
        except Exception as e:
            print(f"[alert] nie udało się wysłać DM: {e}")

    @staticmethod
    def _api_error_text(err: Exception | None) -> str:
        code = getattr(getattr(err, "response", None), "status_code", None)
        if code in (401, 403):
            return (
                f"🔑 **Token API StarterLeague jest błędny lub wygasł** (HTTP {code}).\n"
                "Wygeneruj nowy i wpisz go w pliku `.env` (`STARTERLEAGUE_API_TOKEN`), a potem zrestartuj serwer."
            )
        if code == 429:
            return "⏳ **API StarterLeague zwraca limit zapytań** (HTTP 429). Bot spróbuje ponownie sam."
        return f"🚨 **API StarterLeague nie odpowiada od ok. 3 minut.**\n`{str(err)[:300]}`"

    @tasks.loop(seconds=60)
    async def api_watch(self):
        if not feature_on("alerts"):
            return
        try:
            await asyncio.to_thread(self.api.get_pindolz_live)
        except Exception as e:
            self._api_fail += 1
            print(f"[api_watch] błąd ({self._api_fail}): {e}")
            if self._api_fail >= 3 and not self._api_alerted:
                self._api_alerted = True
                await self._dm_owner(self._api_error_text(e))
            return
        self._api_fail = 0
        if self._api_alerted:
            self._api_alerted = False
            await self._dm_owner("✅ **API StarterLeague znów działa.**")

    @api_watch.before_loop
    async def before_api_watch(self):
        await self.wait_until_ready()

    @tasks.loop(time=time(4, 0, tzinfo=TZ))
    async def cleanup_task(self):
        try:
            n = db.cleanup_old(30)
            if n:
                print(f"[cleanup] usunięto {n} starych rekordów")
        except Exception as e:
            print(f"[cleanup] error: {e}")

    @cleanup_task.before_loop
    async def before_cleanup(self):
        await self.wait_until_ready()


bot = PindolzBot()


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
    await interaction.followup.send(embed=embeds.history_embed(history), view=refresh_view("wyniki"))


@bot.tree.command(name="nadchodzace", description="Nadchodzące mecze PINDOLZ")
async def cmd_nadchodzace(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        upcoming = bot.api.get_pindolz_upcoming()
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    await interaction.followup.send(embed=embeds.upcoming_embed(upcoming))


@bot.tree.command(name="tabela", description="Tabela dywizji PINDOLZ")
async def cmd_tabela(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        table = bot.api.get_division6_table()
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    await interaction.followup.send(embed=embeds.standings_embed(table, changes=bot._rank_changes(table)), view=refresh_view("tabela"))


@bot.tree.command(name="pomoc", description="Lista komend i automatów bota")
async def cmd_pomoc(interaction: discord.Interaction):
    await interaction.response.send_message(embed=embeds.help_embed(), ephemeral=True)


@bot.tree.command(name="wersja", description="Aktualna wersja bota")
async def cmd_wersja(interaction: discord.Interaction):
    uptime = datetime.now(TZ) - bot.started_at
    hours, rem = divmod(int(uptime.total_seconds()), 3600)
    mins, secs = divmod(rem, 60)
    uptime_str = f"{hours}h {mins}m {secs}s" if hours else f"{mins}m {secs}s"
    emb = discord.Embed(title="PINDOLZ Bot", color=0x6366F1, timestamp=datetime.now(TZ))
    emb.add_field(name="Wersja", value=f"`{BOT_VERSION}`", inline=True)
    emb.add_field(name="Uptime", value=uptime_str, inline=True)
    emb.add_field(name="discord.py", value=f"`{discord.__version__}`", inline=True)
    await interaction.response.send_message(embed=emb, ephemeral=True)


@bot.tree.command(name="status", description="Status bota, API i kanałów")
async def cmd_status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    api_ok, api_detail = "❌", "błąd"
    try:
        lives = await asyncio.to_thread(bot.api.get_pindolz_live)
        api_ok, api_detail = "✅", f"OK · live: {len(lives)}"
    except Exception as e:
        api_detail = str(e)[:120]
    main_id, live_id, table_id = bot._main_channel_id(), bot._live_channel_id(), bot._table_channel_id()

    def ch_line(label, cid):
        return f"{label}: **nie ustawiony**" if not cid else f"{label}: <#{cid}>"

    uptime = datetime.now(TZ) - bot.started_at
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    up = f"{h}h {m}m {s}s" if h else f"{m}m {s}s"
    emb = discord.Embed(title="Status bota PINDOLZ", color=0x3B82F6, timestamp=datetime.now(TZ))
    emb.add_field(name="Wersja", value=f"`{BOT_VERSION}`", inline=True)
    emb.add_field(name="Uptime", value=up, inline=True)
    emb.add_field(name="LIVE task", value="✅" if bot.live_check.is_running() else "❌", inline=True)
    emb.add_field(name="API StarterLeague", value=f"{api_ok} {api_detail}", inline=False)
    emb.add_field(name="Kanały", value="\n".join([ch_line("Główny", main_id), ch_line("LIVE", live_id), ch_line("Tabela", table_id)]), inline=False)
    await interaction.followup.send(embed=emb, ephemeral=True)


@bot.tree.command(name="setup-all", description="Ustaw wszystkie kanały naraz (właściciel)")
@app_commands.describe(glowny="Kanał na wyniki i nadchodzące", live="Kanał LIVE", tabela="Kanał tabeli dywizji")
async def cmd_setup_all(interaction: discord.Interaction, glowny: discord.TextChannel, live: discord.TextChannel, tabela: discord.TextChannel):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    db.set_config("main_channel_id", str(glowny.id))
    db.set_config("live_channel_id", str(live.id))
    db.set_config("table_channel_id", str(tabela.id))
    await interaction.response.defer(ephemeral=True)
    try:
        table = bot.api.get_division6_table()
        if table:
            emb = embeds.standings_embed(table, changes=bot._rank_changes(table))
            msg = await tabela.send(embed=emb, view=refresh_view("tabela"))
            db.set_config("msg_table_id", str(msg.id))
            db.set_config("msg_table_ch", str(tabela.id))
    except Exception as e:
        await interaction.followup.send(f"Kanały ustawione, ale tabela: {e}\nGłówny: {glowny.mention} · LIVE: {live.mention} · Tabela: {tabela.mention}", ephemeral=True)
        return
    await interaction.followup.send(f"**Setup OK**\nGłówny: {glowny.mention}\nLIVE: {live.mention}\nTabela: {tabela.mention}\nTabela: **08:00, 18:00, 20:00, 21:30, 23:00**", ephemeral=True)


@bot.tree.command(name="setup", description="Ustaw kanał główny (wyniki + nadchodzące)")
@app_commands.describe(kanal="Kanał na wyniki i nadchodzące mecze")
async def cmd_setup(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    db.set_config("main_channel_id", str(kanal.id))
    await interaction.response.send_message(f"Kanał główny ustawiony na {kanal.mention}", ephemeral=True)


@bot.tree.command(name="setup-live", description="Ustaw kanał LIVE")
@app_commands.describe(kanal="Kanał na powiadomienia live")
async def cmd_setup_live(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    db.set_config("live_channel_id", str(kanal.id))
    await interaction.response.send_message(f"Kanał live ustawiony na {kanal.mention}", ephemeral=True)


@bot.tree.command(name="setup-tabela", description="Ustaw kanał tabeli dywizji")
@app_commands.describe(kanal="Kanał na automatyczną tabelę")
async def cmd_setup_tabela(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    db.set_config("table_channel_id", str(kanal.id))
    await interaction.response.defer(ephemeral=True)
    try:
        table = bot.api.get_division6_table()
        if table:
            emb = embeds.standings_embed(table, changes=bot._rank_changes(table))
            msg = await kanal.send(embed=emb, view=refresh_view("tabela"))
            db.set_config("msg_table_id", str(msg.id))
            db.set_config("msg_table_ch", str(kanal.id))
            await interaction.followup.send(f"Kanał tabeli ustawiony na {kanal.mention}\nTabela: **08:00, 18:00, 20:00, 21:30, 23:00**", ephemeral=True)
        else:
            await interaction.followup.send(f"Kanał ustawiony na {kanal.mention}, ale tabela pusta.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Kanał ustawiony, błąd tabeli: {e}", ephemeral=True)


def _demo_embeds(user_id: int) -> list[tuple[str, discord.Embed]]:
    now = datetime.now(TZ)
    start = now + timedelta(days=2, hours=3)
    past = now - timedelta(days=1)
    t_us = {"id": PINDOLZ_TEAM_ID, "name": "PINDOLZ"}
    t_op = {"id": 1, "name": "Przykładowa Drużyna"}
    base = {
        "id": 0, "division": "Starter Division 6", "bestOf": 3, "team1": t_us, "team2": t_op,
        "matchDate": start.strftime("%Y-%m-%d"), "matchTime": start.strftime("%H:%M:%S"),
    }
    win = {**base, "matchDate": past.strftime("%Y-%m-%d"), "score": {"team1": 2, "team2": 0}, "winnerTeamId": PINDOLZ_TEAM_ID}
    loss = {**win, "score": {"team1": 0, "team2": 2}, "winnerTeamId": 1}
    live = {**base, "currentMap": {"name": "Mirage", "score": {"team1": 7, "team2": 5}}, "seriesScore": {"team1": 1, "team2": 0}}
    names = ["Alfa", "Bravo", "Charlie", "Delta", "PINDOLZ", "Foxtrot", "Golf", "Hotel", "India", "Juliett", "Kilo", "Lima"]
    table = [
        {"rank": i + 1, "team": {"id": 100 + i, "name": n}, "wins": 9 - i // 2, "losses": 1 + i // 2,
         "roundDifference": 30 - i * 5, "points": 27 - i * 2}
        for i, n in enumerate(names)
    ]
    standing, opp_standing = table[4], table[2]
    poll_info = {"opp": t_op["name"], "ts": int(start.timestamp()), "div": base["division"], "bo": 3}
    votes = {str(user_id): "yes", "111": "no", "222": "maybe"}
    items = [
        ("Nadchodzące mecze", lambda: embeds.upcoming_embed([base])),
        ("Karta meczu", lambda: embeds.single_upcoming_embed(base)),
        ("Skład na mecz", lambda: embeds.lineup_embed(base, [user_id, 111, 222], {user_id: "grabovsky"})),
        ("Przypomnienie 1 h", lambda: embeds.prematch_embed(base, form="WWLWL", standing=standing, opp_standing=opp_standing, minutes=60)),
        ("Przypomnienie 30 min", lambda: embeds.prematch_embed(base, form="WWLWL", standing=standing, opp_standing=opp_standing, lineup=[user_id], nicks={user_id: "grabovsky"})),
        ("Ankieta dostępności", lambda: embeds.poll_embed(poll_info, votes)),
        ("Zmiana terminu", lambda: embeds.schedule_changed_embed(base, past.strftime("%Y-%m-%d"), "18:00:00")),
        ("Nowy mecz", lambda: embeds.new_match_embed(base)),
        ("Ustalono termin", lambda: embeds.new_match_embed(base, dated=True)),
        ("Mecz opóźniony", lambda: embeds.delay_embed(base, 18)),
        ("Korekta wyniku", lambda: embeds.result_embed(win, form="WWLWW", standing=standing, correction="2:1")),
        ("Karta gracza", lambda: embeds.player_card_embed("Grabek", "grabovsky", {"polls": 8, "yes": 6, "no": 1, "maybe": 1, "lineups": 5, "in_lineup": 4})),
        ("Raport kapitana", lambda: embeds.captain_report_embed([("📅 Najbliższe mecze", f"{embeds._ts(base, 'F')} · vs **Przykładowa Drużyna**"), ("🏆 Tabela", "🏅 **5.** miejsce · **21** pkt · ▲2 vs poprzedni raport")], ["Nie ustawiono składu na mecz z Przykładową Drużyną (`/sklad`)."])),
        ("LIVE", lambda: embeds.live_embed(live)),
        ("Start meczu", lambda: embeds.match_started_embed(base)),
        ("Wynik: wygrana", lambda: embeds.result_embed(win, form="WWLWW", standing=standing)),
        ("Wynik: porażka", lambda: embeds.result_embed(loss, form="WWLWL", standing=standing)),
        ("Ostatnie wyniki", lambda: embeds.history_embed([win, loss])),
        ("Tabela", lambda: embeds.standings_embed(table, changes={"PINDOLZ": 2, "ALFA": -1})),
        ("Awans w tabeli", lambda: embeds.rank_change_embed(6, 5, standing["points"])),
        ("Spadek w tabeli", lambda: embeds.rank_change_embed(4, 5, standing["points"])),
        ("Podsumowanie tygodnia", lambda: embeds.weekly_summary_embed([win, loss], 1, 1, standing)),
        ("Bot online", lambda: embeds.restart_embed(BOT_VERSION, None, None, None)),
        ("Pomoc", lambda: embeds.help_embed()),
    ]
    out = []
    for name, fn in items:
        try:
            out.append((name, fn()))
        except Exception as e:
            out.append((name, discord.Embed(title=f"Błąd karty: {name}", description=str(e)[:500], color=0xEF4444)))
    return out


@bot.tree.command(name="setup-ankiety", description="Ustaw osobny kanał na ankiety dostępności (właściciel)")
@app_commands.describe(kanal="Kanał, na którym bot będzie pytał „Kto może grać?”")
async def cmd_setup_ankiety(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    db.set_config("poll_channel_id", str(kanal.id))
    roles = bot._poll_roles()
    roles_txt = " ".join(f"<@&{r}>" for r in roles) if roles else "brak (ustaw przez `/ankieta-role`)"
    await interaction.response.send_message(
        f"Kanał ankiet ustawiony na {kanal.mention}.\nPingowane role: {roles_txt}\n"
        "Ankieta pojawi się, gdy najbliższy mecz będzie miał ustaloną datę i godzinę.",
        ephemeral=True,
    )


@bot.tree.command(name="ankieta-role", description="Role pingowane przy ankiecie (bez argumentów czyści listę)")
@app_commands.describe(rola1="Rola 1", rola2="Rola 2", rola3="Rola 3", rola4="Rola 4", rola5="Rola 5")
async def cmd_ankieta_role(
    interaction: discord.Interaction,
    rola1: Optional[discord.Role] = None,
    rola2: Optional[discord.Role] = None,
    rola3: Optional[discord.Role] = None,
    rola4: Optional[discord.Role] = None,
    rola5: Optional[discord.Role] = None,
):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    roles = [r for r in (rola1, rola2, rola3, rola4, rola5) if r is not None]
    db.set_config("poll_roles", json.dumps([r.id for r in roles]))
    if roles:
        await interaction.response.send_message("Ankieta będzie pingować: " + " ".join(r.mention for r in roles), ephemeral=True)
    else:
        await interaction.response.send_message("Lista ról wyczyszczona, ankieta nie będzie nikogo pingować.", ephemeral=True)


@bot.tree.command(name="ustawienia", description="Włączanie i wyłączanie funkcji bota (właściciel)")
async def cmd_ustawienia(interaction: discord.Interaction):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    await interaction.response.send_message(embed=settings_embed(), view=SettingsView(), ephemeral=True)


@bot.tree.command(name="pokaz-embedy", description="Podgląd wszystkich kart bota z przykładowymi danymi (właściciel)")
async def cmd_pokaz_embedy(interaction: discord.Interaction):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    cards = _demo_embeds(interaction.user.id)
    for i in range(0, len(cards), 3):
        chunk = cards[i:i + 3]
        content = " · ".join(f"**{n}**" for n, _ in chunk)
        try:
            await interaction.followup.send(content=content, embeds=[e for _, e in chunk], ephemeral=True)
        except discord.HTTPException:
            for n, e in chunk:
                try:
                    await interaction.followup.send(content=f"**{n}**", embed=e, ephemeral=True)
                except discord.HTTPException as err:
                    await interaction.followup.send(f"Nie udało się pokazać „{n}”: {err}", ephemeral=True)


@bot.tree.command(name="sklad", description="Ustaw skład na najbliższy mecz + DM z prośbą o potwierdzenie (właściciel)")
@app_commands.describe(
    gracz1="Gracz 1", gracz2="Gracz 2", gracz3="Gracz 3", gracz4="Gracz 4",
    gracz5="Gracz 5", gracz6="Gracz 6", gracz7="Gracz 7",
)
async def cmd_sklad(
    interaction: discord.Interaction,
    gracz1: Optional[discord.Member] = None,
    gracz2: Optional[discord.Member] = None,
    gracz3: Optional[discord.Member] = None,
    gracz4: Optional[discord.Member] = None,
    gracz5: Optional[discord.Member] = None,
    gracz6: Optional[discord.Member] = None,
    gracz7: Optional[discord.Member] = None,
):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    await interaction.response.defer()
    try:
        upcoming = await asyncio.to_thread(bot.api.get_pindolz_upcoming)
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    nxt = bot._next_match(upcoming)
    if not nxt:
        await interaction.followup.send("Brak nadchodzącego meczu z ustaloną datą, nie ma dla czego ustawić składu.")
        return
    _, m = nxt
    mid = int(m["id"])
    players = [p for p in (gracz1, gracz2, gracz3, gracz4, gracz5, gracz6, gracz7) if p is not None]
    ids = list(dict.fromkeys(p.id for p in players))
    db.set_config(f"lineup_{mid}", json.dumps(ids))
    _index_add("lineup_index", mid)

    # Reset potwierdzeń przy nowym składzie
    if ids:
        _set_lineup_confirms(mid, {str(i): "pending" for i in ids})
    else:
        _set_lineup_confirms(mid, {})

    await interaction.followup.send(embed=embeds.lineup_embed(m, ids, _player_nicks()))

    # DM do każdego gracza: czy może grać?
    dm_ok, dm_fail = [], []
    opp = "?"
    try:
        t1, t2 = m.get("team1") or {}, m.get("team2") or {}
        n1, n2 = t1.get("name") or "?", t2.get("name") or "?"
        opp = n2 if "pindolz" in n1.lower() else n1
    except Exception:
        pass
    when = f"{m.get('date') or '?'} {m.get('time') or ''}".strip()

    for member in players:
        try:
            emb = discord.Embed(
                title="🎮 Potwierdzenie składu PINDOLZ",
                description=(
                    f"Zostałeś wpisany w skład na mecz.\n"
                    f"**Rywal:** {opp}\n"
                    f"**Termin:** {when}\n\n"
                    f"Czy możesz grać? Kliknij poniżej."
                ),
                color=0x5865F2,
            )
            emb.set_footer(text=f"Mecz #{mid} · odpowiedź dostanie kapitan")
            await member.send(embed=emb, view=sklad_confirm_view(mid))
            dm_ok.append(member.mention)
        except Exception:
            dm_fail.append(member.mention)

    summary = []
    if dm_ok:
        summary.append(f"DM wysłane do: {', '.join(dm_ok)}")
    if dm_fail:
        summary.append(f"Nie udało się wysłać DM (zamknięte PW?): {', '.join(dm_fail)}")
    if not ids:
        summary.append("Skład wyczyszczony – bez zapytań DM.")
    if summary:
        await interaction.followup.send("\n".join(summary), ephemeral=True)

    try:
        await bot.event_check.coro(bot)  # od razu odśwież opis wydarzenia serwera
    except Exception as e:
        print(f"[sklad] event: {e}")


@bot.tree.command(name="polacz", description="Powiąż osobę z nickiem gracza w lidze (bez nicku usuwa; właściciel)")
@app_commands.describe(osoba="Osoba na serwerze", nick="Nick gracza w lidze (puste = usuń powiązanie)")
async def cmd_polacz(interaction: discord.Interaction, osoba: discord.Member, nick: Optional[str] = None):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    none = discord.AllowedMentions.none()
    nicks = _player_nicks()
    if nick is None or not nick.strip():
        if nicks.pop(osoba.id, None) is None:
            await interaction.response.send_message(f"{osoba.mention} nie ma powiązanego nicku.", ephemeral=True, allowed_mentions=none)
            return
        db.set_config("player_links", json.dumps({str(k): v for k, v in nicks.items()}))
        await interaction.response.send_message(f"Usunięto powiązanie dla {osoba.mention}.", allowed_mentions=none)
        return
    nick = nick.strip()
    if not 2 <= len(nick) <= 32 or "`" in nick or "\n" in nick:
        await interaction.response.send_message("Nick musi mieć 2–32 znaki i nie może zawierać znaku ` ani nowej linii.", ephemeral=True)
        return
    taken = next((uid for uid, n in nicks.items() if uid != osoba.id and n.casefold() == nick.casefold()), None)
    if taken:
        await interaction.response.send_message(f"Nick `{nick}` jest już powiązany z <@{taken}>.", ephemeral=True, allowed_mentions=none)
        return
    nicks[osoba.id] = nick
    db.set_config("player_links", json.dumps({str(k): v for k, v in nicks.items()}))
    await interaction.response.send_message(f"🔗 Powiązano {osoba.mention} z nickiem `{nick}`.", allowed_mentions=none)


@bot.tree.command(name="gracze", description="Lista graczy powiązanych z nickami w lidze")
async def cmd_gracze(interaction: discord.Interaction):
    await interaction.response.send_message(embed=embeds.players_embed(_player_nicks()))


@bot.tree.command(name="gif-dodaj", description="Dodaj GIF lub obrazek do losowania po wygranej (właściciel)")
@app_commands.describe(link="Link https:// do GIF-a lub obrazka (np. Tenor, Giphy, Imgur)")
async def cmd_gif_dodaj(interaction: discord.Interaction, link: str):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    link = link.strip()
    if not link.startswith("https://") or len(link) > 300 or any(c.isspace() for c in link):
        await interaction.response.send_message("Podaj poprawny link zaczynający się od `https://` (bez spacji, do 300 znaków).", ephemeral=True)
        return
    gifs = _win_gifs()
    if link in gifs:
        await interaction.response.send_message("Ten link jest już na liście.", ephemeral=True)
        return
    if len(gifs) >= 50:
        await interaction.response.send_message("Lista jest pełna (max 50). Usuń coś przez `/gif-usun`.", ephemeral=True)
        return
    gifs.append(link)
    db.set_config("win_gifs", json.dumps(gifs))
    await interaction.response.send_message(f"🎞️ Dodano jako #{len(gifs)} (na liście: {len(gifs)}). Podgląd:\n{link}", ephemeral=True)


@bot.tree.command(name="gif-lista", description="Lista GIF-ów losowanych po wygranej (właściciel)")
async def cmd_gif_lista(interaction: discord.Interaction):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    gifs = _win_gifs()
    emb = embeds._base("🎞️ GIF-y po wygranej", embeds.C_INFO)
    if gifs:
        emb.description = "\n".join(f"**{i}.** {g[:70]}" for i, g in enumerate(gifs, 1))[:4000]
    else:
        emb.description = "Lista jest pusta. Dodaj pierwszy GIF komendą `/gif-dodaj`."
    await interaction.response.send_message(embed=emb, ephemeral=True)


@bot.tree.command(name="gif-usun", description="Usuń GIF z listy po numerze (właściciel)")
@app_commands.describe(numer="Numer z listy `/gif-lista`")
async def cmd_gif_usun(interaction: discord.Interaction, numer: app_commands.Range[int, 1, 50]):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    gifs = _win_gifs()
    if numer > len(gifs):
        await interaction.response.send_message(f"Na liście jest tylko {len(gifs)} pozycji.", ephemeral=True)
        return
    removed = gifs.pop(numer - 1)
    db.set_config("win_gifs", json.dumps(gifs))
    db.set_config("win_gif_last", None)
    await interaction.response.send_message(f"Usunięto #{numer}: {removed[:80]}\nPozostało: {len(gifs)}.", ephemeral=True)


@bot.tree.command(name="gracz", description="Karta gracza: nick, dostępność w ankietach, występy w składzie")
@app_commands.describe(osoba="Osoba z serwera")
async def cmd_gracz(interaction: discord.Interaction, osoba: discord.Member):
    nick = _player_nicks().get(osoba.id)
    await interaction.response.send_message(
        embed=embeds.player_card_embed(osoba.display_name, nick, bot._player_stats(osoba.id), osoba.display_avatar.url)
    )


@bot.tree.command(name="kapitan", description="Ustaw kapitana: odbiorcę raportu i alertów w DM (bez argumentów czyści; właściciel)")
@app_commands.describe(osoba="Kapitan drużyny")
async def cmd_kapitan(interaction: discord.Interaction, osoba: Optional[discord.Member] = None):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    none = discord.AllowedMentions.none()
    if osoba is None:
        db.set_config("captain_id", None)
        await interaction.response.send_message("Kapitan wyczyszczony. Raporty i alerty trafią do właściciela aplikacji bota.", ephemeral=True)
        return
    db.set_config("captain_id", str(osoba.id))
    await interaction.response.send_message(
        f"👑 Kapitan: {osoba.mention}. Poniedziałkowy raport i alerty o opóźnieniu meczu trafią do niego w wiadomości prywatnej.",
        ephemeral=True, allowed_mentions=none,
    )


@bot.tree.command(name="raport", description="Pokaż raport kapitana teraz (właściciel)")
async def cmd_raport(interaction: discord.Interaction):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(embed=await bot._build_report(), ephemeral=True)


@bot.tree.command(name="zaplanuj", description="Zaplanuj wiadomość na wybrany dzień i godzinę (właściciel)")
@app_commands.describe(
    data="Data: DD.MM lub DD.MM.RRRR", godzina="Godzina HH:MM (czas polski)", kanal="Kanał docelowy",
    tresc="Treść wiadomości (max 1800 znaków)", rola="Opcjonalnie: rola do oznaczenia",
)
async def cmd_zaplanuj(
    interaction: discord.Interaction, data: str, godzina: str, kanal: discord.TextChannel,
    tresc: str, rola: Optional[discord.Role] = None,
):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    dt = _parse_when(data, godzina)
    if dt is None:
        await interaction.response.send_message("Nie rozumiem daty lub godziny. Użyj np. `20.10` lub `20.10.2026` oraz `18:30`.", ephemeral=True)
        return
    if dt <= datetime.now(TZ) + timedelta(minutes=1):
        await interaction.response.send_message("Ten termin już minął. Podaj datę z przyszłości.", ephemeral=True)
        return
    tresc = tresc.strip()
    if not tresc or len(tresc) > 1800:
        await interaction.response.send_message("Treść musi mieć od 1 do 1800 znaków.", ephemeral=True)
        return
    items = _sched_list()
    if len(items) >= 25:
        await interaction.response.send_message("Limit 25 zaplanowanych wiadomości. Usuń coś przez `/zaplanuj-usun`.", ephemeral=True)
        return
    me = interaction.guild.me if interaction.guild else None
    if me and not kanal.permissions_for(me).send_messages:
        await interaction.response.send_message(f"Bot nie ma uprawnienia do pisania na {kanal.mention}.", ephemeral=True)
        return
    seq = (db.get_config_int("sched_seq") or 0) + 1
    db.set_config("sched_seq", str(seq))
    items.append({"id": seq, "ts": int(dt.timestamp()), "ch": kanal.id, "text": tresc, "role": rola.id if rola else None, "by": interaction.user.id})
    db.set_config("sched_msgs", json.dumps(items))
    await interaction.response.send_message(
        f"⏰ Zaplanowano #{seq} na <t:{int(dt.timestamp())}:F> (<t:{int(dt.timestamp())}:R>) w {kanal.mention}.",
        ephemeral=True,
    )


@bot.tree.command(name="zaplanowane", description="Lista zaplanowanych wiadomości (właściciel)")
async def cmd_zaplanowane(interaction: discord.Interaction):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    items = sorted(_sched_list(), key=lambda i: i.get("ts", 0))
    emb = embeds._base("⏰ Zaplanowane wiadomości", embeds.C_INFO)
    if items:
        emb.description = "\n".join(
            f"**#{i['id']}** · <t:{i['ts']}:F> · <#{i['ch']}>\n> {i['text'][:80]}" for i in items
        )[:4000]
    else:
        emb.description = "Brak zaplanowanych wiadomości. Dodaj je komendą `/zaplanuj`."
    await interaction.response.send_message(embed=emb, ephemeral=True)


@bot.tree.command(name="zaplanuj-usun", description="Usuń zaplanowaną wiadomość po numerze (właściciel)")
@app_commands.describe(numer="Numer z listy `/zaplanowane`")
async def cmd_zaplanuj_usun(interaction: discord.Interaction, numer: int):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    items = _sched_list()
    left = [i for i in items if i.get("id") != numer]
    if len(left) == len(items):
        await interaction.response.send_message(f"Nie ma zaplanowanej wiadomości o numerze {numer}.", ephemeral=True)
        return
    db.set_config("sched_msgs", json.dumps(left))
    await interaction.response.send_message(f"Usunięto zaplanowaną wiadomość #{numer}.", ephemeral=True)


@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    print(f"Wersja: {BOT_VERSION}")
    try:
        embeds.AUTHOR_ICON = str(bot.user.display_avatar.url)
    except Exception:
        pass
    print("Bot gotowy – taski i komendy według harmonogramu soft-startu.")
    if bot._announced:
        return
    bot._announced = True

    async def _send_restart_notice():
        channel = await bot.get_channel_safe(bot._main_channel_id())
        if not channel:
            return
        try:
            emb = bot._boot_progress_embed(set(), current="live")
            msg = await channel.send(embed=emb)
            bot._boot_msg = msg

            async def _delete_later():
                await asyncio.sleep(600)
                try:
                    await msg.delete()
                except Exception:
                    pass

            asyncio.create_task(_delete_later())
        except Exception as e:
            print(f"[restart-msg] {e}")

    asyncio.create_task(_send_restart_notice())


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("Brak DISCORD_BOT_TOKEN")
    bot.run(TOKEN)
