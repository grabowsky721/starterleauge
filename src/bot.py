import asyncio
import functools
import json
import os
import random
import requests
import sys
import traceback

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
# Soft-start: mecz → komendy@60s → tło → utrzymanie (~3 min)
# Soft-start łącznie ~90 s od ready
START_DELAY_LIVE = 4
START_DELAY_PREMATCH = 8
START_DELAY_DAILY = 12
START_DELAY_COMMANDS = 16
START_DELAY_TABLE = 20
START_DELAY_STATUS = 30
START_DELAY_POLL = 40
START_DELAY_API = 50
START_DELAY_EVENT = 60
START_DELAY_CLEANUP = 70
START_DELAY_UPDATE = 80
START_DELAY_WEEKLY = 90
START_DELAY_COMMANDS_SYNC = 16

# Kolejność startu komend slash (UI; krótka przerwa, by zmieścić się w 90 s)
COMMAND_START_GAP = 0.35
COMMAND_START_ORDER = [
    "pomoc",
    "setup",
    "setup-live",
    "setup-tabela",
    "setup-ankiety",
    "setup-rola-sklad",
    "setup-ogloszenia",
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
    "panel",
    "sklad-status",
    "ping-sklad",
    "moj-status",
    "kapitan",
    "vicekapitan",
    "sztab",
    "trening",
    "ogloszenie",
    "szablon-usun",
    "szablon-lista",
    "szablon-dodaj",
    "zaplanuj",
    "zaplanuj-lista",
    "coach",
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
    "quiet": ("Ciche godziny", "🌙 W nocy (23–8) tylko LIVE – bez tabeli/daily/prematch"),
}


def feature_on(name: str) -> bool:
    return db.get_config(f"feat_{name}") != "0"


def log(tag: str, msg: str) -> None:
    """Jednolity log do konsoli GameHost."""
    print(f"[{tag}] {msg}")


def cfg_json(key: str, default=None):
    """Bezpieczny odczyt JSON z configu."""
    if default is None:
        default = None
    try:
        raw = db.get_config(key)
        if raw is None or raw == "":
            return default if default is not None else None
        return json.loads(raw)
    except Exception:
        return default if default is not None else None


def cfg_json_list(key: str) -> list:
    v = cfg_json(key, [])
    return v if isinstance(v, list) else []


def cfg_json_dict(key: str) -> dict:
    v = cfg_json(key, {})
    return v if isinstance(v, dict) else {}


def active_lineup_role_id() -> int | None:
    return db.get_config_int("active_lineup_role_id")


def announce_templates() -> dict[str, str]:
    """Szablony ogłoszeń: nazwa → treść."""
    d = cfg_json_dict("announce_templates")
    return {str(k): str(v) for k, v in d.items() if str(v).strip()}


def save_announce_templates(data: dict[str, str]) -> None:
    db.set_config("announce_templates", json.dumps(data, ensure_ascii=False))





async def safe_ephemeral(interaction: discord.Interaction, content: str = None, **kwargs) -> None:
    """Odpowiedź ephemeral odporna na już użyte interaction.response."""
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content=content, ephemeral=True, **kwargs)
        else:
            await interaction.response.send_message(content=content, ephemeral=True, **kwargs)
    except Exception as e:
        log("interact", f"safe_ephemeral: {e}")



def quiet_now() -> bool:
    """True gdy włączone ciche godziny i jesteśmy w oknie 23:00–07:59 Europe/Warsaw."""
    if not feature_on("quiet"):
        return False
    h = datetime.now(TZ).hour
    return h >= 23 or h < 8


def _sched_key(sid: int) -> str:
    return f"sched_msg_{sid}"


def _load_sched(sid: int) -> dict | None:
    try:
        raw = db.get_config(_sched_key(sid))
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _save_sched(sid: int, data: dict) -> None:
    db.set_config(_sched_key(sid), json.dumps(data, ensure_ascii=False))


def _next_sched_id() -> int:
    n = int(db.get_config("sched_msg_seq") or "1")
    db.set_config("sched_msg_seq", str(n + 1))
    return n


def _mvp_key(mid: int) -> str:
    return f"mvp_votes_{mid}"




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


LOOP_NAMES = (
    "table_update", "daily_check", "prematch_check", "live_check", "weekly_summary", "status_loop",
    "poll_check", "event_check", "update_check", "api_watch", "cleanup_task", "scheduled_messages_loop",
)

# Klucze konfiguracji tworzone osobno dla każdego meczu (sprzątane po 60 dniach bez zmian)
PER_MATCH_CONFIG_PREFIXES = (
    "lineup_confirm_", "lineup_", "poll_votes_", "poll_info_", "poll_msg_", "event_",
    "remind_sent_", "remind_", "live_thread_", "gg_", "prematch60_", "prematch_",
)


def guarded(fn):
    """Osłona pętli tasks.loop: wyjątek w jednym przebiegu nie zabija całej pętli."""
    @functools.wraps(fn)
    async def wrapper(self, *args, **kwargs):
        try:
            return await fn(self, *args, **kwargs)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[{fn.__name__}] nieobsłużony błąd (pętla działa dalej): {type(e).__name__}: {e}")
            traceback.print_exc()
            await self._report_loop_error(fn.__name__, e)
    return wrapper


def _when_text(m: dict) -> str:
    """Termin meczu jako znacznik czasu Discorda (API zwraca matchDate/matchTime)."""
    dt = embeds._match_dt(m) if (m.get("matchDate") and m.get("matchTime")) else None
    return f"<t:{int(dt.timestamp())}:F>" if dt else "?"


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



class MvpButton(discord.ui.DynamicItem[discord.ui.Button], template=r"pindolz_mvp:(?P<mid>\d+):(?P<idx>\d+)"):
    def __init__(self, mid: int, idx: int, label: str = "?"):
        super().__init__(
            discord.ui.Button(
                label=label[:80],
                style=discord.ButtonStyle.primary,
                custom_id=f"pindolz_mvp:{mid}:{idx}",
            )
        )
        self.mid = mid
        self.idx = idx

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match, /):
        return cls(int(match["mid"]), int(match["idx"]), item.label or "?")

    async def callback(self, interaction: discord.Interaction):
        await bot._handle_mvp_vote(interaction, self.mid, self.idx)


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




# ---------- Ankieta treningu (dni → godziny → wydarzenie) ----------
WEEKDAYS_PL = [
    ("poniedzialek", "Poniedziałek"),
    ("wtorek", "Wtorek"),
    ("sroda", "Środa"),
    ("czwartek", "Czwartek"),
    ("piatek", "Piątek"),
    ("sobota", "Sobota"),
    ("niedziela", "Niedziela"),
]
# weekday index: Monday=0 ... Sunday=6
WEEKDAY_INDEX = {k: i for i, (k, _) in enumerate(WEEKDAYS_PL)}
DEFAULT_HOURS = ["16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00"]


def _training_key(pid: int) -> str:
    return f"training_poll_{pid}"


def _load_training(pid: int) -> dict | None:
    try:
        raw = db.get_config(_training_key(pid))
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _save_training(pid: int, data: dict) -> None:
    db.set_config(_training_key(pid), json.dumps(data, ensure_ascii=False))


def _next_training_id() -> int:
    n = int(db.get_config("training_poll_seq") or "1")
    db.set_config("training_poll_seq", str(n + 1))
    return n


def _next_weekday_dt(weekday: int, hour: int, minute: int) -> datetime:
    """Najbliższy wybrany dzień tygodnia (0=pn) o danej godzinie Europe/Warsaw."""
    now = datetime.now(TZ)
    days_ahead = (weekday - now.weekday()) % 7
    candidate = (now + timedelta(days=days_ahead)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    if candidate <= now + timedelta(minutes=5):
        candidate += timedelta(days=7)
    return candidate


def training_embed(data: dict, closed: bool = False) -> discord.Embed:
    phase = data.get("phase") or "days"
    opts = data.get("options") or []
    votes = data.get("votes") or {}
    title_map = {
        "days": "🏋️ Trening – który dzień?",
        "hours": "🏋️ Trening – o której?",
        "done": "🏋️ Trening – ustalone",
    }
    title = title_map.get(phase, "🏋️ Trening")
    if closed or phase == "done":
        title += " · zamknięte"
    day_label = data.get("winning_day_label") or ""
    desc = data.get("question") or "Głosujcie przyciskiem."
    if phase == "hours" and day_label:
        desc = f"**Dzień: {day_label}**\nWybierzcie godzinę."
    if phase == "done":
        desc = data.get("result_text") or "Termin ustalony."
    emb = discord.Embed(
        title=title,
        description=desc,
        color=0x95A5A6 if (closed or phase == "done") else 0x5865F2,
    )
    counts = [0] * len(opts)
    by_opt: list[list[str]] = [[] for _ in opts]
    for uid, oi in votes.items():
        try:
            oi = int(oi)
        except (TypeError, ValueError):
            continue
        if 0 <= oi < len(opts):
            counts[oi] += 1
            by_opt[oi].append(f"<@{uid}>")
    for i, opt in enumerate(opts):
        people = ", ".join(by_opt[i][:10]) if by_opt[i] else "_brak_"
        more = f" +{len(by_opt[i])-10}" if len(by_opt[i]) > 10 else ""
        emb.add_field(name=f"{opt} ({counts[i]})", value=people + more, inline=True)
    emb.set_footer(text=f"ID {data.get('id')} · faza: {phase}")
    return emb


def training_view(pid: int, data: dict) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    phase = data.get("phase") or "days"
    opts = data.get("options") or []
    if phase in ("days", "hours") and not data.get("closed"):
        for i, lab in enumerate(opts[:7]):
            view.add_item(TreningButton(pid, i, label=str(lab)[:80]))
        # staff controls
        if phase == "days":
            view.add_item(TreningStaffButton(pid, "hours", "Dalej: godziny"))
        elif phase == "hours":
            view.add_item(TreningStaffButton(pid, "event", "Utwórz wydarzenie"))
    return view


class TreningButton(discord.ui.DynamicItem[discord.ui.Button], template=r"pindolz_train:(?P<pid>\d+):(?P<opt>\d+)"):
    def __init__(self, pid: int, opt: int, label: str | None = None):
        super().__init__(
            discord.ui.Button(
                label=(label or f"Opcja {opt + 1}")[:80],
                style=discord.ButtonStyle.primary,
                custom_id=f"pindolz_train:{pid}:{opt}",
            )
        )
        self.pid = pid
        self.opt = opt

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match, /):
        return cls(int(match["pid"]), int(match["opt"]), item.label or "?")

    async def callback(self, interaction: discord.Interaction):
        data = _load_training(self.pid)
        if not data or data.get("closed") or data.get("phase") == "done":
            await interaction.response.send_message("Ta ankieta jest już zamknięta.", ephemeral=True)
            return
        opts = data.get("options") or []
        if self.opt < 0 or self.opt >= len(opts):
            await interaction.response.send_message("Nieprawidłowa opcja.", ephemeral=True)
            return
        votes = data.setdefault("votes", {})
        votes[str(interaction.user.id)] = self.opt
        data["votes"] = votes
        _save_training(self.pid, data)
        emb = training_embed(data)
        try:
            await interaction.response.edit_message(embed=emb, view=training_view(self.pid, data))
        except Exception:
            await interaction.response.send_message(f"Głos: **{opts[self.opt]}**", ephemeral=True)


class TreningStaffButton(discord.ui.DynamicItem[discord.ui.Button], template=r"pindolz_train_staff:(?P<pid>\d+):(?P<action>hours|event)"):
    def __init__(self, pid: int, action: str, label: str = "Dalej"):
        style = discord.ButtonStyle.success if action == "event" else discord.ButtonStyle.secondary
        super().__init__(
            discord.ui.Button(
                label=label[:80],
                style=style,
                custom_id=f"pindolz_train_staff:{pid}:{action}",
            )
        )
        self.pid = pid
        self.action = action

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match, /):
        return cls(int(match["pid"]), match["action"], item.label or "Dalej")

    async def callback(self, interaction: discord.Interaction):
        if not bot.is_staff(interaction):
            await interaction.response.send_message("Tylko sztab.", ephemeral=True)
            return
        data = _load_training(self.pid)
        if not data:
            await interaction.response.send_message("Brak ankiety.", ephemeral=True)
            return
        if self.action == "hours":
            await bot._trening_advance_to_hours(interaction, self.pid, data)
        else:
            await bot._trening_create_event(interaction, self.pid, data)



class TreningRateButton(discord.ui.DynamicItem[discord.ui.Button], template=r"pindolz_trate:(?P<pid>\d+):(?P<score>[1-5])"):
    def __init__(self, pid: int, score: int):
        super().__init__(
            discord.ui.Button(
                label=str(score),
                style=discord.ButtonStyle.secondary,
                custom_id=f"pindolz_trate:{pid}:{score}",
            )
        )
        self.pid = pid
        self.score = score

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match, /):
        return cls(int(match["pid"]), int(match["score"]))

    async def callback(self, interaction: discord.Interaction):
        data = _load_training(self.pid) or {}
        rates = data.setdefault("ratings", {})
        rates[str(interaction.user.id)] = self.score
        data["ratings"] = rates
        _save_training(self.pid, data)
        await interaction.response.send_message(
            f"Twoja ocena treningu: **{self.score}/5** (możesz zmienić klikając ponownie).",
            ephemeral=True,
        )


class TreningRateStaffButton(discord.ui.DynamicItem[discord.ui.Button], template=r"pindolz_trate_staff:(?P<pid>\d+)"):
    def __init__(self, pid: int):
        super().__init__(
            discord.ui.Button(
                label="Wyniki (sztab)",
                style=discord.ButtonStyle.primary,
                custom_id=f"pindolz_trate_staff:{pid}",
            )
        )
        self.pid = pid

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match, /):
        return cls(int(match["pid"]))

    async def callback(self, interaction: discord.Interaction):
        if not bot.is_staff(interaction):
            await interaction.response.send_message("Tylko sztab widzi wyniki.", ephemeral=True)
            return
        data = _load_training(self.pid) or {}
        rates = data.get("ratings") or {}
        if not rates:
            await interaction.response.send_message("Brak ocen.", ephemeral=True)
            return
        scores = [int(v) for v in rates.values() if str(v).isdigit()]
        avg = sum(scores) / len(scores) if scores else 0
        dist = {i: 0 for i in range(1, 6)}
        for s in scores:
            if 1 <= s <= 5:
                dist[s] += 1
        lines = [f"**{i}/5** — {dist[i]}×" for i in range(1, 6)]
        emb = discord.Embed(
            title=f"⭐ Ocena treningu #{self.pid}",
            description=f"Średnia: **{avg:.2f}/5** · głosów: **{len(scores)}**\n\n" + "\n".join(lines),
            color=0xF1C40F,
        )
        await interaction.response.send_message(embed=emb, ephemeral=True)


def training_rate_view(pid: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for s in range(1, 6):
        view.add_item(TreningRateButton(pid, s))
    view.add_item(TreningRateStaffButton(pid))
    return view


class TreningSetupView(discord.ui.View):
    """Ephemeral: wybór dni tygodnia i publikacja ankiety."""

    def __init__(self, owner_id: int):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.selected_days: list[str] = []
        self.add_item(TreningDaySelect(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id and not bot.is_staff(interaction):
            await interaction.response.send_message("To nie Twoja ankieta.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Opublikuj ankietę dni", style=discord.ButtonStyle.success, row=2)
    async def publish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_days:
            await interaction.response.send_message("Wybierz przynajmniej jeden dzień.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        ch_id = db.get_config_int("poll_channel_id")
        if not ch_id:
            await interaction.followup.send(
                "Brak kanału ankiet. Ustaw: `/setup-ankiety` (albo w `/setup-all` jeśli dodane).",
                ephemeral=True,
            )
            return
        channel = await bot.get_channel_safe(ch_id)
        if channel is None:
            await interaction.followup.send("Nie mogę otworzyć kanału ankiet.", ephemeral=True)
            return
        # preserve order Mon-Sun
        order_keys = [k for k, _ in WEEKDAYS_PL]
        days = [k for k in order_keys if k in self.selected_days]
        labels = [dict(WEEKDAYS_PL)[k] for k in days]
        pid = _next_training_id()
        data = {
            "id": pid,
            "phase": "days",
            "day_keys": days,
            "options": labels,
            "votes": {},
            "closed": False,
            "question": "Którego dnia robimy trening? (jeden wybór)",
            "channel_id": channel.id,
            "guild_id": interaction.guild.id if interaction.guild else None,
            "created_by": interaction.user.id,
            "hours_options": list(DEFAULT_HOURS),
        }
        content = None
        try:
            role_ids = [int(x) for x in cfg_json_list("poll_role_ids")]
            if role_ids:
                content = " ".join(f"<@&{r}>" for r in role_ids)
        except Exception:
            pass
        emb = training_embed(data)
        msg = await channel.send(content=content, embed=emb, view=training_view(pid, data))
        data["message_id"] = msg.id
        _save_training(pid, data)
        await interaction.followup.send(
            f"✅ Ankieta dni **#{pid}** na {channel.mention}.\n"
            f"Po głosowaniu kliknij **Dalej: godziny** (sztab).",
            ephemeral=True,
        )


class TreningDaySelect(discord.ui.Select):
    def __init__(self, parent: "TreningSetupView"):
        options = [
            discord.SelectOption(label=label, value=key, description="Włącz ten dzień w ankiecie")
            for key, label in WEEKDAYS_PL
        ]
        super().__init__(
            placeholder="Wybierz dni do ankiety (1–7)",
            min_values=1,
            max_values=7,
            options=options,
            row=0,
        )
        self.parent_view = parent

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.selected_days = list(self.values)
        labels = [dict(WEEKDAYS_PL)[k] for k in self.parent_view.selected_days]
        await interaction.response.send_message(
            "Wybrane dni: **" + ", ".join(labels) + "**\nKliknij **Opublikuj ankietę dni**.",
            ephemeral=True,
        )


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


def _lineup_presets() -> dict[str, list[int]]:
    """Nazwane składy: {"Główny": [uid, ...], ...}"""
    try:
        raw = json.loads(db.get_config("lineup_presets") or "{}")
        out: dict[str, list[int]] = {}
        for k, v in raw.items():
            name = str(k).strip()[:32]
            if not name:
                continue
            ids = []
            for x in v or []:
                try:
                    ids.append(int(x))
                except (TypeError, ValueError):
                    pass
            out[name] = list(dict.fromkeys(ids))[:7]
        return out
    except Exception:
        return {}


def _save_lineup_presets(presets: dict[str, list[int]]) -> None:
    db.set_config(
        "lineup_presets",
        json.dumps({k: v for k, v in presets.items()}, ensure_ascii=False),
    )


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


def _sklad_preview_embed(m: dict, mid: int, selected_ids: list[int]) -> discord.Embed:
    """Embed panelu składu (interfejs)."""
    opp = _match_opponent(m)
    when = _when_text(m)
    nicks = _player_nicks()
    presets = _lineup_presets()
    preset_info = f" · zapisane składy: **{len(presets)}**" if presets else ""
    emb = discord.Embed(
        title="👥 Panel składu",
        description=(
            f"**vs {opp}** · {when}\n"
            f"Mecz `#{mid}`{preset_info}\n\n"
            f"Wybierz graczy → **Zapisz na mecz** / **Zapisz + DM**.\n"
            f"Albo **Zapisz jako…** (osobny skład) / wczytaj z listy."
        ),
        color=0x5865F2,
    )
    if selected_ids:
        lines = []
        for i, uid in enumerate(selected_ids, 1):
            nick = nicks.get(uid)
            extra = f" · `{nick}`" if nick else ""
            lines.append(f"{i}. <@{uid}>{extra}")
        emb.add_field(name=f"Wybrany skład ({len(selected_ids)}/7)", value="\n".join(lines), inline=False)
    else:
        emb.add_field(name="Wybrany skład", value="_pusto – wybierz graczy_", inline=False)
    # status potwierdzeń jeśli już coś zapisane
    try:
        saved = [int(x) for x in json.loads(db.get_config(f"lineup_{mid}") or "[]")]
    except Exception:
        saved = []
    if saved:
        _, yes, no, pending = _lineup_status_lists(mid)
        emb.add_field(
            name="Ostatnie potwierdzenia",
            value=f"✅ {len(yes)} · ❌ {len(no)} · ⏳ {len(pending)}",
            inline=False,
        )
    emb.set_footer(text="Panel wygasa po 5 min · tylko właściciel")
    return emb


async def _sklad_send_confirmation_dms(m: dict, mid: int, ids: list[int]) -> tuple[list[str], list[str]]:
    """Wyślij DM z prośbą o potwierdzenie. Zwraca (ok_mentions, fail_mentions)."""
    opp = _match_opponent(m)
    when = _when_text(m)
    dm_ok, dm_fail = [], []
    for uid in ids:
        user = bot.get_user(uid)
        if user is None:
            try:
                user = await bot.fetch_user(uid)
            except Exception:
                dm_fail.append(f"<@{uid}>")
                continue
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
            await user.send(embed=emb, view=sklad_confirm_view(mid))
            dm_ok.append(f"<@{uid}>")
        except Exception:
            dm_fail.append(f"<@{uid}>")
    return dm_ok, dm_fail


class SkladPanelView(discord.ui.View):
    """Interfejs składu: wielu graczy, zapis na mecz, wiele nazwanych składów."""

    def __init__(self, mid: int, match: dict, owner_id: int, selected_ids: list[int] | None = None):
        super().__init__(timeout=360)
        self.mid = mid
        self.match = match
        self.owner_id = owner_id
        self.selected_ids = list(dict.fromkeys(selected_ids or []))[:7]
        self._rebuild_items()

    def _rebuild_items(self):
        self.clear_items()
        self.add_item(SkladUserSelect(self))
        presets = _lineup_presets()
        if presets:
            opts = [
                discord.SelectOption(
                    label=name[:100],
                    value=name,
                    description=f"{len(ids)} graczy"[:100],
                )
                for name, ids in list(presets.items())[:25]
            ]
            self.add_item(SkladPresetSelect(self, opts))
        # buttons row 2-3
        self.add_item(SkladBtnSaveMatch(self))
        self.add_item(SkladBtnSaveDm(self))
        self.add_item(SkladBtnSaveAs(self))
        self.add_item(SkladBtnClear(self))
        self.add_item(SkladBtnStatus(self))

    def build_embed(self) -> discord.Embed:
        emb = _sklad_preview_embed(self.match, self.mid, self.selected_ids)
        presets = _lineup_presets()
        if presets:
            lines = [f"**{n}** ({len(ids)}): " + ", ".join(f"<@{i}>" for i in ids[:7]) for n, ids in list(presets.items())[:8]]
            emb.add_field(name="Zapisane składy", value="\n".join(lines)[:1024], inline=False)
        return emb

    def _persist_match(self) -> list[int]:
        ids = list(dict.fromkeys(self.selected_ids))[:7]
        db.set_config(f"lineup_{self.mid}", json.dumps(ids))
        if ids:
            _set_lineup_confirms(self.mid, {str(i): "pending" for i in ids})
        else:
            _set_lineup_confirms(self.mid, {})
        print(f"[sklad] mecz mid={self.mid} ids={ids}")
        return ids

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not bot.is_staff(interaction):
            await interaction.response.send_message("Tylko właściciel, kapitan, vicekapitan lub coach.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class SkladUserSelect(discord.ui.UserSelect):
    def __init__(self, panel: "SkladPanelView"):
        super().__init__(
            placeholder="Wybierz graczy do składu (max 7)…",
            min_values=1,
            max_values=7,
            row=0,
        )
        self.panel = panel

    async def callback(self, interaction: discord.Interaction):
        ids = [int(u.id) for u in self.values if not getattr(u, "bot", False)]
        self.panel.selected_ids = list(dict.fromkeys(ids))[:7]
        await interaction.response.edit_message(embed=self.panel.build_embed(), view=self.panel)


class SkladPresetSelect(discord.ui.Select):
    def __init__(self, panel: "SkladPanelView", options: list):
        super().__init__(
            placeholder="Wczytaj lub usuń zapisany skład…",
            min_values=1,
            max_values=1,
            options=options,
            row=1,
        )
        self.panel = panel

    async def callback(self, interaction: discord.Interaction):
        name = self.values[0]
        presets = _lineup_presets()
        ids = presets.get(name, [])
        self.panel.selected_ids = list(ids)[:7]
        await interaction.response.edit_message(embed=self.panel.build_embed(), view=self.panel)
        await interaction.followup.send(
            f"Wczytano skład **{name}** ({len(ids)} os.). Zapisz na mecz przyciskiem **Zapisz na mecz**.",
            ephemeral=True,
        )


class SkladBtnSaveMatch(discord.ui.Button):
    def __init__(self, panel: "SkladPanelView"):
        super().__init__(label="Zapisz na mecz", style=discord.ButtonStyle.primary, emoji="💾", row=2)
        self.panel = panel

    async def callback(self, interaction: discord.Interaction):
        if not self.panel.selected_ids:
            await interaction.response.send_message("Wybierz graczy albo wczytaj zapisany skład.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        ids = self.panel._persist_match()
        emb = embeds.lineup_embed(self.panel.match, ids, _player_nicks())
        await interaction.edit_original_response(embed=emb, view=self.panel)
        role_note = ""
        try:
            a, r = await bot.sync_active_lineup_roles(interaction.guild, ids, mid=self.panel.mid)
            if active_lineup_role_id():
                role_note = f" · rola składu: +{a}/−{r}"
        except Exception as e:
            log("sklad-rola", f"save: {e}")
        await interaction.followup.send(
            f"✅ Skład na mecz zapisany ({len(ids)} os.): " + ", ".join(f"<@{i}>" for i in ids) + role_note,
            ephemeral=True,
        )
        try:
            await bot.event_check.coro(bot)
        except Exception as e:
            print(f"[sklad] event: {e}")


class SkladBtnSaveDm(discord.ui.Button):
    def __init__(self, panel: "SkladPanelView"):
        super().__init__(label="Zapisz + DM", style=discord.ButtonStyle.success, emoji="📨", row=2)
        self.panel = panel

    async def callback(self, interaction: discord.Interaction):
        if not self.panel.selected_ids:
            await interaction.response.send_message("Wybierz graczy najpierw.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        ids = self.panel._persist_match()
        try:
            await bot.sync_active_lineup_roles(interaction.guild, ids, mid=self.panel.mid)
        except Exception as e:
            log("sklad-rola", f"save+dm: {e}")
        emb = embeds.lineup_embed(self.panel.match, ids, _player_nicks())
        await interaction.edit_original_response(embed=emb, view=self.panel)
        dm_ok, dm_fail = await _sklad_send_confirmation_dms(self.panel.match, self.panel.mid, ids)
        parts = [f"✅ Zapisano na mecz ({len(ids)} os.)"]
        if dm_ok:
            parts.append(f"DM: {', '.join(dm_ok)}")
        if dm_fail:
            parts.append(f"Bez PW: {', '.join(dm_fail)}")
        await interaction.followup.send("\n".join(parts), ephemeral=True)
        try:
            await bot.event_check.coro(bot)
        except Exception as e:
            print(f"[sklad] event: {e}")


class SkladBtnSaveAs(discord.ui.Button):
    def __init__(self, panel: "SkladPanelView"):
        super().__init__(label="Zapisz jako…", style=discord.ButtonStyle.secondary, emoji="📁", row=2)
        self.panel = panel

    async def callback(self, interaction: discord.Interaction):
        if not self.panel.selected_ids:
            await interaction.response.send_message("Wybierz graczy, żeby zapisać skład pod nazwą.", ephemeral=True)
            return
        await interaction.response.send_modal(SkladNameModal(self.panel))


class SkladBtnClear(discord.ui.Button):
    def __init__(self, panel: "SkladPanelView"):
        super().__init__(label="Wyczyść", style=discord.ButtonStyle.danger, emoji="🧹", row=3)
        self.panel = panel

    async def callback(self, interaction: discord.Interaction):
        self.panel.selected_ids = []
        await interaction.response.edit_message(embed=self.panel.build_embed(), view=self.panel)


class SkladBtnStatus(discord.ui.Button):
    def __init__(self, panel: "SkladPanelView"):
        super().__init__(label="Status", style=discord.ButtonStyle.secondary, emoji="📋", row=3)
        self.panel = panel

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=_lineup_status_embed(self.panel.match, self.panel.mid),
            ephemeral=True,
        )


class SkladNameModal(discord.ui.Modal, title="Nazwa składu"):
    name = discord.ui.TextInput(
        label="Nazwa składu",
        placeholder="np. Główny, Rezerwa, Scrim",
        max_length=32,
        required=True,
    )

    def __init__(self, panel: "SkladPanelView"):
        super().__init__()
        self.panel = panel

    async def on_submit(self, interaction: discord.Interaction):
        name = str(self.name.value).strip()[:32]
        if not name:
            await interaction.response.send_message("Podaj nazwę.", ephemeral=True)
            return
        presets = _lineup_presets()
        presets[name] = list(dict.fromkeys(self.panel.selected_ids))[:7]
        _save_lineup_presets(presets)
        self.panel._rebuild_items()
        await interaction.response.edit_message(embed=self.panel.build_embed(), view=self.panel)
        await interaction.followup.send(
            f"✅ Zapisano skład **{name}** ({len(presets[name])} os.). Możesz go potem wczytać z listy.",
            ephemeral=True,
        )




class SetupPanelView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.main_id: int | None = db.get_config_int("main_channel_id")
        self.live_id: int | None = db.get_config_int("live_channel_id")
        self.table_id: int | None = db.get_config_int("table_channel_id")
        self.announce_id: int | None = db.get_config_int("announce_channel_id")
        self.add_item(SetupChannelSelect(self, "main", "Kanał główny (wyniki)", 0))
        self.add_item(SetupChannelSelect(self, "live", "Kanał LIVE", 1))
        self.add_item(SetupChannelSelect(self, "table", "Kanał tabeli", 2))
        self.add_item(SetupChannelSelect(self, "announce", "Kanał ogłoszeń", 3))

    def build_embed(self) -> discord.Embed:
        def ch(cid):
            return f"<#{cid}>" if cid else "_nie ustawiono_"
        emb = discord.Embed(title="⚙️ Setup kanałów", description="Wybierz kanały, potem **Zapisz**.", color=0x5865F2)
        emb.add_field(name="Główny", value=ch(self.main_id), inline=True)
        emb.add_field(name="LIVE", value=ch(self.live_id), inline=True)
        emb.add_field(name="Tabela", value=ch(self.table_id), inline=True)
        emb.add_field(name="Ogłoszenia", value=ch(self.announce_id), inline=True)
        emb.set_footer(text="Ogłoszenia: tylko treningi")
        return emb

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Tylko właściciel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Zapisz", style=discord.ButtonStyle.success, emoji="💾", row=3)
    async def btn_save(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (self.main_id and self.live_id and self.table_id):
            await interaction.response.send_message("Ustaw wszystkie trzy kanały.", ephemeral=True)
            return
        db.set_config("main_channel_id", str(self.main_id))
        db.set_config("live_channel_id", str(self.live_id))
        db.set_config("table_channel_id", str(self.table_id))
        if getattr(self, "announce_id", None):
            db.set_config("announce_channel_id", str(self.announce_id))
        await interaction.response.defer(ephemeral=True)
        note = ""
        try:
            table = (await asyncio.to_thread(bot.api.get_division6_table))
            if table and interaction.guild:
                ch = interaction.guild.get_channel(self.table_id)
                if ch:
                    emb = embeds.standings_embed(table, changes=bot._rank_changes(table))
                    msg = await ch.send(embed=emb, view=refresh_view("tabela"))
                    db.set_config("msg_table_id", str(msg.id))
                    db.set_config("msg_table_ch", str(self.table_id))
                    note = "\nTabela wysłana."
        except Exception as e:
            note = f"\nTabela: {e}"
        await interaction.followup.send(
            f"**Setup OK**\nGłówny: <#{self.main_id}>\nLIVE: <#{self.live_id}>\nTabela: <#{self.table_id}>{note}",
            ephemeral=True,
        )


class SetupChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, panel: "SetupPanelView", kind: str, placeholder: str, row: int):
        super().__init__(placeholder=placeholder, channel_types=[discord.ChannelType.text], min_values=1, max_values=1, row=row)
        self.panel = panel
        self.kind = kind

    async def callback(self, interaction: discord.Interaction):
        ch = self.values[0]
        cid = getattr(ch, "id", int(ch))
        if self.kind == "main":
            self.panel.main_id = cid
        elif self.kind == "live":
            self.panel.live_id = cid
        elif self.kind == "table":
            self.panel.table_id = cid
        else:
            self.panel.announce_id = cid
        await interaction.response.edit_message(embed=self.panel.build_embed(), view=self.panel)


class PolaczPanelView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.selected_user = None
        self.add_item(PolaczUserSelect(self))

    def build_embed(self) -> discord.Embed:
        nicks = _player_nicks()
        emb = discord.Embed(title="🔗 Powiązanie z nickiem", description="Wybierz osobę → **Ustaw nick** / **Usuń**.", color=0x5865F2)
        if self.selected_user:
            uid = self.selected_user.id
            cur = nicks.get(uid)
            emb.add_field(name="Osoba", value=f"{self.selected_user.mention}" + (f" → `{cur}`" if cur else " _(brak)_"), inline=False)
        else:
            emb.add_field(name="Osoba", value="_nie wybrano_", inline=False)
        if nicks:
            lines = [f"<@{u}> → `{n}`" for u, n in list(nicks.items())[:15]]
            emb.add_field(name="Lista", value="\n".join(lines), inline=False)
        return emb

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not bot.is_staff(interaction):
            await interaction.response.send_message("Tylko właściciel, kapitan, vicekapitan lub coach.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Ustaw nick", style=discord.ButtonStyle.primary, emoji="✏️", row=1)
    async def btn_set(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_user:
            await interaction.response.send_message("Najpierw wybierz osobę.", ephemeral=True)
            return
        await interaction.response.send_modal(PolaczNickModal(self.selected_user.id, self))

    @discord.ui.button(label="Usuń powiązanie", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def btn_del(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_user:
            await interaction.response.send_message("Najpierw wybierz osobę.", ephemeral=True)
            return
        nicks = _player_nicks()
        nicks.pop(self.selected_user.id, None)
        db.set_config("player_links", json.dumps({str(k): v for k, v in nicks.items()}))
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class PolaczUserSelect(discord.ui.UserSelect):
    def __init__(self, panel: "PolaczPanelView"):
        super().__init__(placeholder="Wybierz osobę…", min_values=1, max_values=1, row=0)
        self.panel = panel

    async def callback(self, interaction: discord.Interaction):
        self.panel.selected_user = self.values[0]
        await interaction.response.edit_message(embed=self.panel.build_embed(), view=self.panel)


class PolaczNickModal(discord.ui.Modal, title="Nick w lidze"):
    nick = discord.ui.TextInput(label="Nick gracza", placeholder="np. PlayerOne", max_length=32)

    def __init__(self, user_id: int, panel: "PolaczPanelView"):
        super().__init__()
        self.user_id = user_id
        self.panel = panel

    async def on_submit(self, interaction: discord.Interaction):
        nicks = _player_nicks()
        nicks[self.user_id] = str(self.nick.value).strip()
        db.set_config("player_links", json.dumps({str(k): v for k, v in nicks.items()}))
        await interaction.response.edit_message(embed=self.panel.build_embed(), view=self.panel)
        await interaction.followup.send(f"Zapisano: <@{self.user_id}> → `{str(self.nick.value).strip()}`", ephemeral=True)


class AnkietaRoleView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        try:
            self.role_ids = [int(x) for x in cfg_json_list("poll_role_ids")]
        except Exception:
            self.role_ids = []
        self.add_item(AnkietaRoleSelect(self))

    def build_embed(self) -> discord.Embed:
        emb = discord.Embed(title="📣 Role do ankiet", description="Wybierz do 5 ról, potem **Zapisz**.", color=0x5865F2)
        emb.add_field(name="Wybrane", value=", ".join(f"<@&{r}>" for r in self.role_ids) or "_brak_", inline=False)
        return emb

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Tylko właściciel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Zapisz", style=discord.ButtonStyle.success, row=1)
    async def btn_save(self, interaction: discord.Interaction, button: discord.ui.Button):
        db.set_config("poll_role_ids", json.dumps(self.role_ids))
        await interaction.response.edit_message(embed=self.build_embed(), view=None)
        await interaction.followup.send("Zapisano role: " + (", ".join(f"<@&{r}>" for r in self.role_ids) or "brak"), ephemeral=True)

    @discord.ui.button(label="Wyczyść", style=discord.ButtonStyle.danger, row=1)
    async def btn_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.role_ids = []
        db.set_config("poll_role_ids", "[]")
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class AnkietaRoleSelect(discord.ui.RoleSelect):
    def __init__(self, panel: "AnkietaRoleView"):
        super().__init__(placeholder="Wybierz role…", min_values=0, max_values=5, row=0)
        self.panel = panel

    async def callback(self, interaction: discord.Interaction):
        self.panel.role_ids = [r.id for r in self.values][:5]
        await interaction.response.edit_message(embed=self.panel.build_embed(), view=self.panel)


class GifListaView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        gifs = _win_gifs()
        options = [discord.SelectOption(label=f"#{i} {g[:80]}"[:100], value=str(i)) for i, g in enumerate(gifs[:25], 1)]
        if options:
            self.add_item(GifRemoveSelect(self, options))

    def build_embed(self) -> discord.Embed:
        gifs = _win_gifs()
        emb = embeds._base("🎞️ GIF-y po wygranej", embeds.C_INFO)
        emb.description = ("\n".join(f"**{i}.** {g[:70]}" for i, g in enumerate(gifs, 1))[:4000] if gifs else "Brak GIF-ów. Dodaj `/gif-dodaj`.")
        if gifs:
            emb.set_footer(text="Wybierz pozycję, aby usunąć")
        return emb

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Tylko właściciel.", ephemeral=True)
            return False
        return True


class GifRemoveSelect(discord.ui.Select):
    def __init__(self, panel: "GifListaView", options: list):
        super().__init__(placeholder="Usuń GIF…", min_values=1, max_values=1, options=options, row=0)
        self.panel = panel

    async def callback(self, interaction: discord.Interaction):
        numer = int(self.values[0])
        gifs = _win_gifs()
        if numer < 1 or numer > len(gifs):
            await interaction.response.send_message("Zły numer.", ephemeral=True)
            return
        removed = gifs.pop(numer - 1)
        db.set_config("win_gifs", json.dumps(gifs))
        db.set_config("win_gif_last", None)
        new_view = GifListaView(self.panel.owner_id)
        await interaction.response.edit_message(embed=new_view.build_embed(), view=new_view if gifs else None)
        await interaction.followup.send(f"Usunięto #{numer}: `{removed[:80]}`", ephemeral=True)


class CaptainPanelView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=300)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not bot.is_staff(interaction):
            await interaction.response.send_message("Tylko właściciel, kapitan, vicekapitan lub coach.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Odśwież", style=discord.ButtonStyle.primary, emoji="🔄", row=0)
    async def btn_refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await interaction.edit_original_response(embed=await _build_captain_panel_embed(), view=self)

    @discord.ui.button(label="Status składu", style=discord.ButtonStyle.secondary, emoji="📋", row=0)
    async def btn_sklad(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            upcoming = await asyncio.to_thread(bot.api.get_pindolz_upcoming)
        except Exception as e:
            await interaction.followup.send(f"Błąd API: {e}", ephemeral=True)
            return
        nxt = bot._next_match(upcoming)
        if not nxt:
            await interaction.followup.send("Brak nadchodzącego meczu.", ephemeral=True)
            return
        _, m = nxt
        await interaction.followup.send(embed=_lineup_status_embed(m, int(m["id"])), ephemeral=True)

    @discord.ui.button(label="Ping skład", style=discord.ButtonStyle.secondary, emoji="🔔", row=0)
    async def btn_ping(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            upcoming = await asyncio.to_thread(bot.api.get_pindolz_upcoming)
        except Exception as e:
            await interaction.followup.send(f"Błąd API: {e}", ephemeral=True)
            return
        nxt = bot._next_match(upcoming)
        if not nxt:
            await interaction.followup.send("Brak nadchodzącego meczu.", ephemeral=True)
            return
        _, m = nxt
        mid = int(m["id"])
        roster, _, _, _ = _lineup_status_lists(mid)
        data = _lineup_confirms(mid)
        pending_ids = [pid for pid in roster if data.get(str(pid)) not in ("yes", "no")]
        if not pending_ids:
            await interaction.followup.send("Wszyscy już odpowiedzieli.", ephemeral=True)
            return
        dm_ok, dm_fail = await _sklad_send_confirmation_dms(m, mid, pending_ids)
        parts = []
        if dm_ok:
            parts.append(f"Wysłano: {', '.join(dm_ok)}")
        if dm_fail:
            parts.append(f"Błąd PW: {', '.join(dm_fail)}")
        await interaction.followup.send("\n".join(parts) or "OK", ephemeral=True)


async def _build_captain_panel_embed() -> discord.Embed:
    api_ok, api_msg = True, "OK"
    try:
        await asyncio.to_thread(bot.api.get_pindolz_upcoming)
    except Exception as e:
        api_ok, api_msg = False, str(e)[:120]
    try:
        upcoming = await asyncio.to_thread(bot.api.get_pindolz_upcoming)
    except Exception:
        upcoming = []
    nxt = bot._next_match(upcoming) if upcoming else None
    emb = discord.Embed(title="📌 Panel kapitana", color=0x5865F2 if api_ok else 0xED4245)
    emb.add_field(name="API", value=("✅ " + api_msg) if api_ok else ("❌ " + api_msg), inline=False)
    main_ch, live_ch, table_ch = bot._main_channel_id(), bot._live_channel_id(), bot._table_channel_id()
    emb.add_field(
        name="Kanały",
        value=f"Główny: {f'<#{main_ch}>' if main_ch else '—'}\nLIVE: {f'<#{live_ch}>' if live_ch else '—'}\nTabela: {f'<#{table_ch}>' if table_ch else '—'}",
        inline=False,
    )
    if not nxt:
        emb.add_field(name="Najbliższy mecz", value="Brak w terminarzu", inline=False)
    else:
        _, m = nxt
        mid = int(m["id"])
        opp, when = _match_opponent(m), _when_text(m)
        roster, yes, no, pending = _lineup_status_lists(mid)
        emb.add_field(name="Najbliższy mecz", value=f"**vs {opp}** · {when}\nSkład: {len(roster)} · ✅{len(yes)} · ❌{len(no)} · ⏳{len(pending)}", inline=False)
    emb.set_footer(text=f"Wersja {BOT_VERSION}")
    return emb



def _match_opponent(m: dict) -> str:
    try:
        t1, t2 = m.get("team1") or {}, m.get("team2") or {}
        n1, n2 = t1.get("name") or "?", t2.get("name") or "?"
        return n2 if "pindolz" in n1.lower() else n1
    except Exception:
        return "?"


def _lineup_status_lists(mid: int) -> tuple[list[int], list[str], list[str], list[str]]:
    """Zwraca (roster_ids, yes_mentions, no_mentions, pending_mentions)."""
    try:
        roster = [int(x) for x in json.loads(db.get_config(f"lineup_{mid}") or "[]")]
    except Exception:
        roster = []
    data = _lineup_confirms(mid)
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
    return roster, yes, no, pending


def _lineup_status_embed(m: dict, mid: int) -> discord.Embed:
    roster, yes, no, pending = _lineup_status_lists(mid)
    opp = _match_opponent(m)
    when = _when_text(m)
    emb = discord.Embed(
        title="📋 Status składu",
        description=f"**vs {opp}** · {when}\nMecz `#{mid}`",
        color=0x5865F2,
    )
    emb.add_field(name=f"✅ Gram ({len(yes)})", value=", ".join(yes) or "—", inline=False)
    emb.add_field(name=f"❌ Nie mogą ({len(no)})", value=", ".join(no) or "—", inline=False)
    emb.add_field(name=f"⏳ Brak odpowiedzi ({len(pending)})", value=", ".join(pending) or "—", inline=False)
    emb.set_footer(text=f"W składzie: {len(roster)} osób")
    return emb





class PindolzBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.api = StarterLeagueClient()
        self.api.on_division = embeds.set_division
        self._upcoming_cache: tuple[datetime, list] | None = None
        self._live_lock = asyncio.Lock()
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
            self.add_dynamic_items(RemindButton, PollButton, GGButton, SkladConfirmButton, TreningButton, TreningStaffButton, TreningRateButton, TreningRateStaffButton, MvpButton)
        except Exception as e:
            print(f"[start] dynamic items: {e}")
        asyncio.create_task(self._soft_start_tasks())
        asyncio.create_task(self._reschedule_training_polls())



    async def _reschedule_training_polls(self):
        """Po restarcie domknij lub wznow odliczanie ankiet treningu."""
        await asyncio.sleep(20)
        try:
            # skan sekwencji wstecz – max 50 ostatnich
            seq = int(db.get_config("training_poll_seq") or "1")
            now = int(datetime.now(TZ).timestamp())
            for pid in range(max(1, seq - 50), seq):
                data = _load_training(pid)
                if not data or data.get("closed"):
                    continue
                closes = int(data.get("closes_at") or 0)
                if closes and closes <= now:
                    await _close_training_poll(pid)
                elif closes:
                    asyncio.create_task(_schedule_training_close(pid, closes))
                    print(f"[trening] wznowiono timer #{pid}")
        except Exception as e:
            print(f"[trening] reschedule: {e}")

    BOOT_LABELS = (
        ("live", "LIVE"),
        ("prematch", "Przypomnienia"),
        ("daily", "Daily"),
        ("commands", "Komendy slash"),
        ("table", "Tabela"),
        ("status", "Status"),
        ("poll", "Ankiety"),
        ("api", "API watch"),
        ("event", "Eventy"),
        ("cleanup", "Cleanup"),
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
        """Mecz → komendy → tło → utrzymanie (łącznie ~90 s)."""
        await self.wait_until_ready()
        print("[start] soft-start (~90 s) · zaplanuj/mvp/quiet…")
        done: set[str] = set()

        async def run_step(key: str, wait: float, action):
            await self._boot_set_progress(done, current=key)
            if wait > 0:
                await asyncio.sleep(wait)
            await action()
            done.add(key)
            await self._boot_set_progress(done)
            print(f"[start] {key}")

        async def start_live():
            if not self.live_check.is_running():
                self.live_check.start()

        async def start_prematch():
            if not self.prematch_check.is_running():
                self.prematch_check.start()

        async def start_daily():
            if not self.daily_check.is_running():
                self.daily_check.start()

        async def start_commands():
            # 1 po drugiej: UI co COMMAND_START_GAP s, na końcu pełny sync
            total = len(COMMAND_START_ORDER)
            cmd_done: list[str] = []
            for name in COMMAND_START_ORDER:
                idx = len(cmd_done) + 1
                try:
                    msg = getattr(self, "_boot_msg", None)
                    if msg:
                        emb = self._boot_progress_embed(done, current="commands")
                        emb.title = f"🚀 Start bota · komendy {idx}/{total}"
                        emb.description = (
                            f"Wersja **`{BOT_VERSION}`** · ładuję komendy "
                            f"**{idx}/{total}** · teraz **`/{name}`**"
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
                            name=f"Komendy ({idx}/{total})",
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
                print(f"[start] komenda /{name} ({idx}/{total})")

            # Najpierw global, potem kopia na każdy serwer – komendy widać od razu
            try:
                synced = await self.tree.sync()
                names = [c.name for c in synced]
                print(f"[sync] global: {len(synced)} komend -> {names}")
            except Exception as e:
                print(f"[sync] global blad: {e}")
                names = []
            for guild in self.guilds:
                try:
                    self.tree.copy_global_to(guild=guild)
                    synced = await self.tree.sync(guild=guild)
                    print(f"[sync] {guild.name}: {len(synced)} komend (guild)")
                except Exception as e:
                    print(f"[sync] guild {guild.id}: {e}")

        async def start_table():
            if not self.table_update.is_running():
                self.table_update.start()

        async def start_status():
            if not self.status_loop.is_running():
                self.status_loop.start()

        async def start_poll():
            if not self.poll_check.is_running():
                self.poll_check.start()

        async def start_api():
            if not self.api_watch.is_running():
                self.api_watch.start()

        async def start_event():
            if not self.event_check.is_running():
                self.event_check.start()

        async def start_cleanup():
            if not self.cleanup_task.is_running():
                self.cleanup_task.start()

        async def start_update():
            if not self.update_check.is_running():
                self.update_check.start()

        async def start_weekly():
            if not self.weekly_summary.is_running():
                self.weekly_summary.start()

        async def start_scheduled():
            if not self.scheduled_messages_loop.is_running():
                self.scheduled_messages_loop.start()

        # Faza 1 – mecz
        await run_step("live", START_DELAY_LIVE, start_live)
        await run_step("prematch", START_DELAY_PREMATCH - START_DELAY_LIVE, start_prematch)
        await run_step("daily", START_DELAY_DAILY - START_DELAY_PREMATCH, start_daily)
        # Faza 2 – komendy
        await run_step("commands", START_DELAY_COMMANDS - START_DELAY_DAILY, start_commands)
        # Faza 3 – tło
        await run_step("table", START_DELAY_TABLE - START_DELAY_COMMANDS, start_table)
        await run_step("status", START_DELAY_STATUS - START_DELAY_TABLE, start_status)
        await run_step("poll", START_DELAY_POLL - START_DELAY_STATUS, start_poll)
        await run_step("api", START_DELAY_API - START_DELAY_POLL, start_api)
        await run_step("event", START_DELAY_EVENT - START_DELAY_API, start_event)
        # Faza 4 – utrzymanie
        await run_step("cleanup", START_DELAY_CLEANUP - START_DELAY_EVENT, start_cleanup)
        await run_step("update", START_DELAY_UPDATE - START_DELAY_CLEANUP, start_update)
        await run_step("scheduled", 0, start_scheduled)
        await run_step("weekly", START_DELAY_WEEKLY - START_DELAY_UPDATE, start_weekly)

        if not self.loop_watchdog.is_running():
            self.loop_watchdog.start()
        print("[start] soft-start zakończony")

    def is_owner(self, interaction: discord.Interaction) -> bool:
        uid = interaction.user.id
        if interaction.guild:
            return uid == interaction.guild.owner_id
        for g in self.guilds:
            if g.owner_id == uid:
                return True
        return False

    def captain_id(self) -> int | None:
        return db.get_config_int("captain_id")

    def vice_captain_id(self) -> int | None:
        return db.get_config_int("vice_captain_id")

    def coach_id(self) -> int | None:
        return db.get_config_int("coach_id")

    def is_captain(self, interaction: discord.Interaction) -> bool:
        """Właściciel serwera lub kapitan."""
        if self.is_owner(interaction):
            return True
        cid = self.captain_id()
        return bool(cid and interaction.user.id == cid)

    def is_staff(self, interaction: discord.Interaction) -> bool:
        """Właściciel, kapitan, vicekapitan lub coach."""
        if self.is_owner(interaction):
            return True
        uid = interaction.user.id
        return uid in {x for x in (self.captain_id(), self.vice_captain_id(), self.coach_id()) if x}

    def _owner_guild(self, user_id: int) -> discord.Guild | None:
        for g in self.guilds:
            if g.owner_id == user_id:
                return g
        return None

    async def get_channel_safe(self, channel_id: int | None):
        if not channel_id:
            return None
        try:
            return self.get_channel(channel_id) or await self.fetch_channel(channel_id)
        except Exception:
            return None


    async def api_call(self, fn, *args, err_tag: str = "api", **kwargs):
        """asyncio.to_thread + log błędu; zwraca None przy awarii."""
        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        except Exception as e:
            log(err_tag, f"{getattr(fn, '__name__', fn)}: {type(e).__name__}: {e}")
            return None

    def _main_channel_id(self) -> int | None:
        return db.get_config_int("main_channel_id")

    def _live_channel_id(self) -> int | None:
        return db.get_config_int("live_channel_id")

    def _table_channel_id(self) -> int | None:
        return db.get_config_int("table_channel_id")

    def _poll_channel_id(self) -> int | None:
        return db.get_config_int("poll_channel_id")

    def _announce_channel_id(self) -> int | None:

        """Kanał ogłoszeń; jeśli brak – kanał główny."""
        return db.get_config_int("announce_channel_id") or self._main_channel_id()

    async def send_announcement(
        self,
        content: str | None = None,
        embed: discord.Embed | None = None,
        *,
        fallback_channel=None,
    ):
        """Wysyła na kanał ogłoszeń (lub fallback / główny)."""
        ch = await self.get_channel_safe(self._announce_channel_id())
        if not ch and fallback_channel is not None:
            ch = fallback_channel
        if not ch:
            ch = await self.get_channel_safe(self._main_channel_id())
        if not ch:
            print("[ogloszenia] brak kanału")
            return None
        try:
            return await ch.send(content=content, embed=embed)
        except Exception as e:
            print(f"[ogloszenia] send: {e}")
            return None

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
        """Edytuj istniejącą wiadomość albo wyślij nową. Zwraca (msg_id, ch_id) lub (None, None)."""
        if msg_id and ch_id:
            try:
                ch = await self.get_channel_safe(int(ch_id)) or channel
                if ch:
                    msg = await ch.fetch_message(int(msg_id))
                    await msg.edit(embed=embed, view=view)
                    return msg.id, ch.id
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
            except Exception as e:
                log("edit", f"edit_or_send: {e}")
        if not channel:
            return None, None
        try:
            msg = await channel.send(embed=embed, view=view)
            return msg.id, channel.id
        except Exception as e:
            log("edit", f"send: {e}")
            return None, None

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
    @guarded
    async def table_update(self):
        if quiet_now():
            return
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
    @guarded
    async def daily_check(self):
        if quiet_now():
            return
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
            standing = (await asyncio.to_thread(self.api.get_pindolz_standing))
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
                    msg_id, ch_id = await self._edit_or_send(channel, embeds.result_embed(m, form=form, standing=standing), row.get("msg_result_id"), row.get("msg_result_ch"), view=gg_view(mid))
                    db.upsert_match(mid, score_team1=new_s1, score_team2=new_s2, winner_team_id=m.get("winnerTeamId"), msg_result_id=msg_id, msg_result_ch=ch_id, status="finished")
                continue
            msg_id, ch_id = await self._edit_or_send(channel, embeds.result_embed(m, form=form, standing=standing), None, None, view=gg_view(mid))
            await self._react_result(ch_id, msg_id, m)
            await self._post_win_gif(ch_id, m)
            db.upsert_match(mid, match_date=m.get("matchDate"), match_time=m.get("matchTime"), division=m.get("division"), opponent=self._opponent(m), status="finished", score_team1=score.get("team1"), score_team2=score.get("team2"), winner_team_id=m.get("winnerTeamId"), finished_at=datetime.utcnow().isoformat(), notified_result=1, msg_result_id=msg_id, msg_result_ch=ch_id)
            await self._start_mvp_vote(channel, m)
            try:
                await self.clear_active_lineup_roles(getattr(channel, "guild", None), mid=mid)
            except Exception as e:
                log("sklad-rola", f"po meczu: {e}")
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
                            await channel.send(
                            content="⚠️ **Zmiana terminu meczu!**",
                            embed=embeds.schedule_changed_embed(m, row.get("match_date"), row.get("match_time")),
                        )

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
    @guarded
    async def prematch_check(self):
        if quiet_now():
            return
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
                table = (await asyncio.to_thread(self.api.get_division6_table))
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
    @guarded
    async def live_check(self):
        if self._live_lock.locked():
            return
        async with self._live_lock:
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
                    standing = (await asyncio.to_thread(self.api.get_pindolz_standing))
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

    async def _start_mvp_vote(self, channel, match: dict):
        """Po meczu: głosowanie MVP – do 5 osób ze składu / powiązań."""
        mid = match.get("id")
        if mid is None or not channel:
            return
        if db.get_config(_mvp_key(mid)):
            return  # już było
        players: list[tuple[int, str]] = []
        try:
            ids = [int(x) for x in json.loads(db.get_config(f"lineup_{mid}") or "[]")]
        except Exception:
            ids = []
        nicks = _player_nicks()
        for uid in ids[:5]:
            players.append((uid, nicks.get(uid) or f"Gracz"))
        if len(players) < 2:
            # uzupełnij z powiązań
            for uid, nick in list(nicks.items()):
                if uid not in {p[0] for p in players}:
                    players.append((uid, nick))
                if len(players) >= 5:
                    break
        if len(players) < 2:
            return
        players = players[:5]
        data = {
            "players": [{"id": u, "nick": n} for u, n in players],
            "votes": {},
            "closed": False,
        }
        db.set_config(_mvp_key(mid), json.dumps(data, ensure_ascii=False))
        emb = discord.Embed(
            title="⭐ MVP meczu – głosowanie",
            description=f"PINDOLZ vs **{self._opponent(match)}**\nWybierz 1 z {len(players)} (głosujesz raz).",
            color=0xF1C40F,
        )
        for i, (uid, nick) in enumerate(players):
            emb.add_field(name=f"{i+1}. {nick}", value=f"<@{uid}>", inline=True)
        view = discord.ui.View(timeout=None)
        for i, (uid, nick) in enumerate(players):
            view.add_item(MvpButton(int(mid), i, label=f"{i+1}. {nick[:60]}"))
        try:
            msg = await channel.send(embed=emb, view=view)
            data["message_id"] = msg.id
            data["channel_id"] = channel.id
            db.set_config(_mvp_key(mid), json.dumps(data, ensure_ascii=False))
            asyncio.create_task(self._close_mvp_later(int(mid), 30 * 60))
        except Exception as e:
            print(f"[mvp] start: {e}")

    async def _handle_mvp_vote(self, interaction: discord.Interaction, mid: int, idx: int):
        try:
            data = json.loads(db.get_config(_mvp_key(mid)) or "{}")
        except Exception:
            data = {}
        if data.get("closed"):
            await interaction.response.send_message("Głosowanie zakończone.", ephemeral=True)
            return
        players = data.get("players") or []
        if idx < 0 or idx >= len(players):
            await interaction.response.send_message("Nieprawidłowy wybór.", ephemeral=True)
            return
        votes = data.setdefault("votes", {})
        votes[str(interaction.user.id)] = idx
        data["votes"] = votes
        db.set_config(_mvp_key(mid), json.dumps(data, ensure_ascii=False))
        # update counts on embed
        counts = [0] * len(players)
        for v in votes.values():
            try:
                vi = int(v)
                if 0 <= vi < len(counts):
                    counts[vi] += 1
            except Exception:
                pass
        emb = discord.Embed(
            title="⭐ MVP meczu – głosowanie",
            description=f"Oddano **{len(votes)}** głosów. Wybierz 1 osobę.",
            color=0xF1C40F,
        )
        for i, p in enumerate(players):
            emb.add_field(
                name=f"{i+1}. {p.get('nick')} ({counts[i]})",
                value=f"<@{p.get('id')}>",
                inline=True,
            )
        view = discord.ui.View(timeout=None)
        for i, p in enumerate(players):
            view.add_item(MvpButton(mid, i, label=f"{i+1}. {str(p.get('nick'))[:60]}"))
        try:
            await interaction.response.edit_message(embed=emb, view=view)
        except Exception:
            await interaction.response.send_message(
                f"Głos na **{players[idx].get('nick')}** zapisany.", ephemeral=True
            )

    async def _close_mvp_later(self, mid: int, delay: int):
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        await self._close_mvp(mid)

    async def _close_mvp(self, mid: int):
        try:
            data = json.loads(db.get_config(_mvp_key(mid)) or "{}")
        except Exception:
            return
        if data.get("closed"):
            return
        data["closed"] = True
        players = data.get("players") or []
        votes = data.get("votes") or {}
        counts = [0] * len(players)
        for v in votes.values():
            try:
                vi = int(v)
                if 0 <= vi < len(counts):
                    counts[vi] += 1
            except Exception:
                pass
        db.set_config(_mvp_key(mid), json.dumps(data, ensure_ascii=False))
        ch_id, msg_id = data.get("channel_id"), data.get("message_id")
        if not players:
            return
        best = max(range(len(players)), key=lambda i: counts[i]) if players else 0
        winner = players[best]
        emb = discord.Embed(
            title="⭐ MVP meczu",
            description=f"**{winner.get('nick')}** (<@{winner.get('id')}>) · {counts[best]} głosów",
            color=0xF1C40F,
        )
        try:
            if ch_id and msg_id:
                ch = await self.get_channel_safe(int(ch_id))
                if ch:
                    msg = await ch.fetch_message(int(msg_id))
                    await msg.edit(embed=emb, view=None)
                    await ch.send(f"⭐ MVP: **{winner.get('nick')}** (<@{winner.get('id')}>)")
        except Exception as e:
            print(f"[mvp] close: {e}")

    @tasks.loop(seconds=30)
    @guarded
    async def scheduled_messages_loop(self):
        """Wysyła zaplanowane wiadomości (/zaplanuj)."""
        now = int(datetime.now(TZ).timestamp())
        try:
            seq = int(db.get_config("sched_msg_seq") or "1")
        except Exception:
            return
        for sid in range(max(1, seq - 100), seq):
            data = _load_sched(sid)
            if not data or data.get("sent"):
                continue
            when = int(data.get("when") or 0)
            if when > now:
                continue
            ch_id = data.get("channel_id")
            content = (data.get("content") or "").strip()
            if not ch_id or not content:
                data["sent"] = True
                _save_sched(sid, data)
                continue
            try:
                ch = await self.get_channel_safe(int(ch_id))
                if not ch:
                    print(f"[zaplanuj] #{sid}: brak kanału {ch_id}")
                    continue
                ping = (data.get("ping") or "").strip()
                text = f"{ping} {content}".strip() if ping else content
                await ch.send(text[:2000])
                data["sent"] = True
                _save_sched(sid, data)
                log("zaplanuj", f"wysłano #{sid} → {ch_id}")
            except Exception as e:
                log("zaplanuj", f"#{sid}: {e}")


    async def _trening_advance_to_hours(self, interaction: discord.Interaction, pid: int, data: dict):
        if data.get("phase") != "days":
            await interaction.response.send_message("Ta ankieta nie jest w fazie dni.", ephemeral=True)
            return
        opts = data.get("options") or []
        votes = data.get("votes") or {}
        if not opts:
            await interaction.response.send_message("Brak opcji.", ephemeral=True)
            return
        counts = [0] * len(opts)
        for v in votes.values():
            try:
                vi = int(v)
                if 0 <= vi < len(counts):
                    counts[vi] += 1
            except Exception:
                pass
        best = max(range(len(opts)), key=lambda i: counts[i])
        if counts[best] == 0:
            await interaction.response.send_message("Nikt jeszcze nie zagłosował.", ephemeral=True)
            return
        day_keys = data.get("day_keys") or []
        winning_key = day_keys[best] if best < len(day_keys) else None
        winning_label = opts[best]
        hours = data.get("hours_options") or list(DEFAULT_HOURS)
        data["phase"] = "hours"
        data["winning_day_key"] = winning_key
        data["winning_day_label"] = winning_label
        data["options"] = list(hours)
        data["votes"] = {}
        data["question"] = f"Dzień: **{winning_label}** – o której godzinie?"
        _save_training(pid, data)
        emb = training_embed(data)
        try:
            await interaction.response.edit_message(embed=emb, view=training_view(pid, data))
        except Exception:
            await interaction.response.send_message("Przeszedłem do fazy godzin.", ephemeral=True)
            ch = await self.get_channel_safe(data.get("channel_id"))
            if ch and data.get("message_id"):
                try:
                    msg = await ch.fetch_message(int(data["message_id"]))
                    await msg.edit(embed=emb, view=training_view(pid, data))
                except Exception:
                    pass
        # announce
        try:
            await self.send_announcement(
                f"📅 Wybrany dzień treningu: **{winning_label}** ({counts[best]} głosów). "
                f"Głosujcie na **godzinę** w ankiecie."
            )
        except Exception:
            pass

    async def _trening_create_event(self, interaction: discord.Interaction, pid: int, data: dict):
        if data.get("phase") != "hours":
            await interaction.response.send_message("Najpierw zakończ wybór dnia (Dalej: godziny).", ephemeral=True)
            return
        opts = data.get("options") or []
        votes = data.get("votes") or {}
        if not opts:
            await interaction.response.send_message("Brak godzin.", ephemeral=True)
            return
        counts = [0] * len(opts)
        for v in votes.values():
            try:
                vi = int(v)
                if 0 <= vi < len(counts):
                    counts[vi] += 1
            except Exception:
                pass
        best = max(range(len(opts)), key=lambda i: counts[i])
        if counts[best] == 0:
            await interaction.response.send_message("Nikt nie zagłosował na godzinę.", ephemeral=True)
            return
        hour_s = opts[best]
        try:
            hh, mm = hour_s.split(":")
            hour_i, min_i = int(hh), int(mm)
        except Exception:
            await interaction.response.send_message("Zła godzina.", ephemeral=True)
            return
        day_key = data.get("winning_day_key")
        day_label = data.get("winning_day_label") or "?"
        if day_key not in WEEKDAY_INDEX:
            await interaction.response.send_message("Brak wybranego dnia.", ephemeral=True)
            return
        start_dt = _next_weekday_dt(WEEKDAY_INDEX[day_key], hour_i, min_i)
        end_dt = start_dt + timedelta(hours=2)
        guild = interaction.guild
        if not guild and data.get("guild_id"):
            guild = self.get_guild(int(data["guild_id"]))
        if not guild:
            await interaction.response.send_message("Brak serwera.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        # create event
        ev = None
        try:
            ev = await guild.create_scheduled_event(
                name=f"Trening PINDOLZ · {day_label} {hour_s}",
                start_time=start_dt.astimezone(ZoneInfo("UTC")),
                end_time=end_dt.astimezone(ZoneInfo("UTC")),
                description=f"Trening ustalony ankietą #{pid}.\nDzień: {day_label}\nGodzina: {hour_s} (Europe/Warsaw)",
                location="Online / VC drużyny",
                entity_type=discord.EntityType.external,
                privacy_level=discord.PrivacyLevel.guild_only,
            )
        except Exception as e1:
            try:
                # fallback bez external
                ev = await guild.create_scheduled_event(
                    name=f"Trening PINDOLZ · {day_label} {hour_s}",
                    start_time=start_dt,
                    end_time=end_dt,
                    description=f"Trening #{pid} · {day_label} {hour_s}",
                    location="Online",
                )
            except Exception as e2:
                await interaction.followup.send(f"Nie udało się utworzyć wydarzenia: {e2}", ephemeral=True)
                print(f"[trening] event error: {e1} / {e2}")
                return
        result = (
            f"**{day_label}** o **{hour_s}**\n"
            f"🗓 <t:{int(start_dt.timestamp())}:F> · <t:{int(start_dt.timestamp())}:R>"
        )
        if ev:
            result += f"\n📎 Wydarzenie: {ev.url}" if getattr(ev, "url", None) else f"\n📎 Wydarzenie ID: {ev.id}"
        data["phase"] = "done"
        data["closed"] = True
        data["result_text"] = result
        data["event_id"] = getattr(ev, "id", None)
        data["start_ts"] = int(start_dt.timestamp())
        _save_training(pid, data)
        emb = training_embed(data, closed=True)
        ch = await self.get_channel_safe(data.get("channel_id"))
        if ch and data.get("message_id"):
            try:
                msg = await ch.fetch_message(int(data["message_id"]))
                await msg.edit(embed=emb, view=None)
            except Exception:
                pass
        # ogłoszenie na kanale ogłoszeń
        announce = (
            f"🏋️ **Trening ustalony!**\n"
            f"{result}\n"
            f"Do zobaczenia na VC."
        )
        try:
            role_ids = [int(x) for x in cfg_json_list("poll_role_ids")]
            if role_ids:
                announce = " ".join(f"<@&{r}>" for r in role_ids) + "\n" + announce
        except Exception:
            pass
        await self.send_announcement(announce, fallback_channel=ch)
        # Ocena treningu 1–5 (wyniki tylko dla sztabu)
        try:
            rate_ch = await self.get_channel_safe(db.get_config_int("poll_channel_id"))
            if not rate_ch:
                rate_ch = ch
            if rate_ch:
                remb = discord.Embed(
                    title="⭐ Oceń trening",
                    description=(
                        f"{day_label} · {hour_s}\n"
                        f"Kliknij ocenę **1–5**. Wyniki widzi tylko sztab."
                    ),
                    color=0xF1C40F,
                )
                rmsg = await rate_ch.send(embed=remb, view=training_rate_view(pid))
                data["rate_message_id"] = rmsg.id
                data["rate_channel_id"] = rate_ch.id
                data["ratings"] = data.get("ratings") or {}
                _save_training(pid, data)
        except Exception as e:
            log("trening", f"ocena: {e}")
        await interaction.followup.send(f"✅ Wydarzenie utworzone.\n{result}", ephemeral=True)
        print(f"[trening] event #{pid} {day_label} {hour_s} ts={start_dt}")


    async def sync_active_lineup_roles(self, guild: discord.Guild | None, member_ids: list[int], *, mid: int | None = None) -> tuple[int, int]:
        """Nadaje rolę aktywnego składu wybranym; zdejmuje z poprzedniego składu.
        Zwraca (nadano, zdjęto)."""
        role_id = active_lineup_role_id()
        if not guild or not role_id:
            return 0, 0
        role = guild.get_role(int(role_id))
        if not role:
            log("sklad-rola", f"brak roli {role_id}")
            return 0, 0
        want = set(int(x) for x in member_ids)
        prev_mid = db.get_config_int("active_lineup_mid")
        prev_ids: set[int] = set()
        if prev_mid:
            try:
                prev_ids = {int(x) for x in json.loads(db.get_config(f"lineup_{prev_mid}") or "[]")}
            except Exception:
                prev_ids = set()
        # also anyone currently with the role who shouldn't keep it
        to_remove = (prev_ids - want) if prev_ids else set()
        added = removed = 0
        for uid in to_remove:
            try:
                member = guild.get_member(uid) or await guild.fetch_member(uid)
                if member and role in member.roles:
                    await member.remove_roles(role, reason="Zmiana składu meczowego")
                    removed += 1
            except Exception as e:
                log("sklad-rola", f"remove {uid}: {e}")
        for uid in want:
            try:
                member = guild.get_member(uid) or await guild.fetch_member(uid)
                if member and role not in member.roles:
                    await member.add_roles(role, reason="Skład na mecz")
                    added += 1
            except Exception as e:
                log("sklad-rola", f"add {uid}: {e}")
        if mid is not None:
            db.set_config("active_lineup_mid", str(mid))
        log("sklad-rola", f"mid={mid} +{added} -{removed}")
        return added, removed

    async def clear_active_lineup_roles(self, guild: discord.Guild | None = None, mid: int | None = None) -> int:
        """Zdejmuje rolę aktywnego składu po meczu."""
        role_id = active_lineup_role_id()
        if not role_id:
            return 0
        active_mid = mid or db.get_config_int("active_lineup_mid")
        ids: list[int] = []
        if active_mid:
            try:
                ids = [int(x) for x in json.loads(db.get_config(f"lineup_{active_mid}") or "[]")]
            except Exception:
                ids = []
        if not guild and active_mid:
            # spróbuj z main channel
            ch = await self.get_channel_safe(self._main_channel_id())
            guild = getattr(ch, "guild", None) if ch else None
        if not guild:
            for g in self.guilds:
                guild = g
                break
        if not guild:
            return 0
        role = guild.get_role(int(role_id))
        if not role:
            return 0
        removed = 0
        for uid in ids:
            try:
                member = guild.get_member(uid) or await guild.fetch_member(uid)
                if member and role in member.roles:
                    await member.remove_roles(role, reason="Koniec meczu – zdjęcie aktywnego składu")
                    removed += 1
            except Exception as e:
                log("sklad-rola", f"clear {uid}: {e}")
        db.set_config("active_lineup_mid", None)
        log("sklad-rola", f"wyczyszczono mid={active_mid} -{removed}")
        return removed

    @tasks.loop(time=time(20, 0, tzinfo=TZ))
    @guarded
    async def weekly_summary(self):
        if datetime.now(TZ).weekday() != 6:
            return
        channel = await self.get_channel_safe(self._main_channel_id())
        if not channel:
            return
        try:
            history = (await asyncio.to_thread(self.api.get_pindolz_history))
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
            standing = (await asyncio.to_thread(self.api.get_pindolz_standing))
        except Exception:
            pass
        await channel.send(embed=embeds.weekly_summary_embed(week_matches, wins, losses, standing))
        print("[weekly] wysłano podsumowanie tygodnia")
        # 12 – DM do kapitana
        try:
            cid = self.captain_id()
            if cid:
                user = self.get_user(cid) or await self.fetch_user(cid)
                if user:
                    emb = embeds.weekly_summary_embed(week_matches, wins, losses, standing)
                    emb.title = (emb.title or "Podsumowanie tygodnia") + " · DM kapitana"
                    # frekwencja z lineupów z tygodnia
                    freq: dict[int, int] = {}
                    for m in week_matches:
                        mid = m.get("id")
                        if mid is None:
                            continue
                        try:
                            ids = json.loads(db.get_config(f"lineup_{mid}") or "[]")
                            for uid in ids:
                                freq[int(uid)] = freq.get(int(uid), 0) + 1
                        except Exception:
                            pass
                    if freq:
                        lines = [f"<@{u}> · {c}×" for u, c in sorted(freq.items(), key=lambda x: -x[1])[:15]]
                        emb.add_field(name="Frekwencja (skład)", value="\n".join(lines), inline=False)
                    await user.send(embed=emb)
                    print(f"[weekly] DM do kapitana {cid}")
        except Exception as e:
            print(f"[weekly] DM kapitana: {e}")

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
    @guarded
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
    @guarded
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
    @guarded
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

    @tasks.loop(hours=1)
    @guarded
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

    # ---------- ALERT O AWARII API ----------
    async def _report_loop_error(self, name: str, err: Exception):
        """DM do właściciela o błędzie w zadaniu w tle (max raz na 30 min dla danego zadania)."""
        last = self.__dict__.setdefault("_loop_err_last", {})
        now = datetime.now(TZ).timestamp()
        if now - last.get(name, 0) < 1800:
            return
        last[name] = now
        await self._dm_owner(
            f"⚠️ Zadanie w tle **{name}** zgłosiło błąd: `{type(err).__name__}: {str(err)[:300]}`\n"
            "Bot działa dalej. Jeśli to się powtarza, sprawdź uprawnienia bota na kanałach i log serwera."
        )

    @tasks.loop(minutes=2)
    @guarded
    async def loop_watchdog(self):
        """Wznawia zadania w tle, które mimo osłony się zatrzymały."""
        for name in LOOP_NAMES:
            lp = getattr(self, name, None)
            if lp is not None and lp.failed():
                print(f"[watchdog] zadanie {name} się zatrzymało, restartuję")
                try:
                    lp.restart()
                except Exception as e:
                    print(f"[watchdog] nie udało się zrestartować {name}: {e}")
                await self._report_loop_error(name, RuntimeError("zadanie zatrzymało się i zostało wznowione przez watchdog"))

    @loop_watchdog.before_loop
    async def before_loop_watchdog(self):
        await self.wait_until_ready()

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
    @guarded
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
    @guarded
    async def cleanup_task(self):
        try:
            n = db.cleanup_old(30)
            if n:
                print(f"[cleanup] usunięto {n} starych rekordów")
            c = db.cleanup_config(PER_MATCH_CONFIG_PREFIXES, 60)
            if c:
                print(f"[cleanup] usunięto {c} nieaktualnych kluczy konfiguracji")
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
        upcoming = (await asyncio.to_thread(bot.api.get_pindolz_upcoming))
        history = (await asyncio.to_thread(bot.api.get_pindolz_history))
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    await interaction.followup.send(embeds=[embeds.upcoming_embed(upcoming), embeds.history_embed(history)])


@bot.tree.command(name="live", description="Czy PINDOLZ gra teraz?")
async def cmd_live(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        lives = (await asyncio.to_thread(bot.api.get_pindolz_live))
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
        history = (await asyncio.to_thread(bot.api.get_pindolz_history))
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    await interaction.followup.send(embed=embeds.history_embed(history), view=refresh_view("wyniki"))


@bot.tree.command(name="nadchodzace", description="Nadchodzące mecze PINDOLZ")
async def cmd_nadchodzace(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        upcoming = (await asyncio.to_thread(bot.api.get_pindolz_upcoming))
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    await interaction.followup.send(embed=embeds.upcoming_embed(upcoming))


@bot.tree.command(name="tabela", description="Tabela dywizji PINDOLZ")
async def cmd_tabela(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        table = (await asyncio.to_thread(bot.api.get_division6_table))
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    await interaction.followup.send(embed=embeds.standings_embed(table, changes=bot._rank_changes(table)), view=refresh_view("tabela"))


@bot.tree.command(name="pomoc", description="Lista komend i automatów bota")
async def cmd_pomoc(interaction: discord.Interaction):
    if interaction.guild is None:
        emb = discord.Embed(
            title="📬 Komendy w DM",
            description="Te komendy działają w prywatnej rozmowie z botem:",
            color=0x5865F2,
        )
        emb.add_field(
            name="Dla kapitana / właściciela",
            value=(
                "`/panel` – najbliższy mecz, skład, API\n"
                "`/sklad-status` – kto Gram / Nie może / cisza\n"
                "`/ping-sklad` – ponów DM do osób bez odpowiedzi"
            ),
            inline=False,
        )
        emb.add_field(
            name="Dla graczy",
            value="`/moj-status` – czy jesteś w składzie i co odpisałeś",
            inline=False,
        )
        emb.add_field(
            name="Inne",
            value="`/pomoc` · `/wersja` · `/nastepny` (jeśli dostępne na serwerze też działają tu)",
            inline=False,
        )
        emb.set_footer(text="Wymagany wspólny serwer z botem · DM od bota tylko jeśli możesz otrzymywać PW")
        await interaction.response.send_message(embed=emb)
        return
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


@bot.tree.command(name="setup-all", description="Panel ustawiania kanałów (interfejs; właściciel)")
async def cmd_setup_all(interaction: discord.Interaction):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    if interaction.guild is None:
        await interaction.response.send_message("Użyj na serwerze.", ephemeral=True)
        return
    view = SetupPanelView(interaction.user.id)
    await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)


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
        table = (await asyncio.to_thread(bot.api.get_division6_table))
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


@bot.tree.command(name="setup-ankiety", description="Ustaw kanał na wszystkie ankiety: dostępność + trening (właściciel)")
@app_commands.describe(kanal="Kanał ankiet (dostępność, trening)")
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




@bot.tree.command(name="setup-rola-sklad", description="Ustaw rolę nadawaną aktywnemu składowi (właściciel)")
@app_commands.describe(rola="Rola dla graczy w składzie na mecz (puste = wyłącz)")
async def cmd_setup_rola_sklad(interaction: discord.Interaction, rola: Optional[discord.Role] = None):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    if rola is None:
        db.set_config("active_lineup_role_id", None)
        await interaction.response.send_message("Rola aktywnego składu **wyłączona**.", ephemeral=True)
        return
    if rola.is_default() or rola.managed:
        await interaction.response.send_message("Wybierz zwykłą rolę serwera (nie @everyone / nie role bota).", ephemeral=True)
        return
    db.set_config("active_lineup_role_id", str(rola.id))
    await interaction.response.send_message(
        f"Rola aktywnego składu: {rola.mention}\n"
        f"Nadawana przy **Zapisz na mecz** / **Zapisz + DM**, zdejmowana po wyniku meczu.\n"
        f"Upewnij się, że rola bota jest **wyżej** na liście ról niż ta rola.",
        ephemeral=True,
    )


@bot.tree.command(name="setup-ogloszenia", description="Ustaw kanał ogłoszeń (właściciel)")
@app_commands.describe(kanal="Kanał na ogłoszenia treningów")
async def cmd_setup_ogloszenia(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    db.set_config("announce_channel_id", str(kanal.id))
    await interaction.response.send_message(
        f"Kanał ogłoszeń: {kanal.mention}\nTam bot pisze tylko o treningach (ankiety i ustalony termin).",
        ephemeral=True,
    )


@bot.tree.command(name="ankieta-role", description="Panel ról do ankiet (interfejs; właściciel)")
async def cmd_ankieta_role(interaction: discord.Interaction):
    if not bot.is_staff(interaction):
        await interaction.response.send_message("Tylko właściciel, kapitan, vicekapitan lub coach.", ephemeral=True)
        return
    if interaction.guild is None:
        await interaction.response.send_message("Użyj na serwerze.", ephemeral=True)
        return
    view = AnkietaRoleView(interaction.user.id)
    await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)


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


@bot.tree.command(name="sklad", description="Panel składu na najbliższy mecz (interfejs; właściciel)")
async def cmd_sklad(interaction: discord.Interaction):
    if not bot.is_staff(interaction):
        await interaction.response.send_message("Tylko właściciel, kapitan, vicekapitan lub coach.", ephemeral=True)
        return
    if interaction.guild is None:
        await interaction.response.send_message(
            "Panel składu działa na serwerze (wybór graczy). Użyj `/sklad` na kanale drużyny.",
            ephemeral=True,
        )
        return
    await interaction.response.defer(ephemeral=True)
    try:
        upcoming = await asyncio.to_thread(bot.api.get_pindolz_upcoming)
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}", ephemeral=True)
        return
    nxt = bot._next_match(upcoming)
    if not nxt:
        await interaction.followup.send(
            "Brak nadchodzącego meczu z ustaloną datą – nie ma dla czego ustawić składu.",
            ephemeral=True,
        )
        return
    _, m = nxt
    mid = int(m["id"])
    try:
        current = [int(x) for x in json.loads(db.get_config(f"lineup_{mid}") or "[]")]
    except Exception:
        current = []
    view = SkladPanelView(mid, m, interaction.user.id, selected_ids=current)
    await interaction.followup.send(embed=view.build_embed(), view=view, ephemeral=True)


@bot.tree.command(name="polacz", description="Panel powiązań gracz ↔ nick (interfejs; właściciel)")
async def cmd_polacz(interaction: discord.Interaction):
    if not bot.is_staff(interaction):
        await interaction.response.send_message("Tylko właściciel, kapitan, vicekapitan lub coach.", ephemeral=True)
        return
    if interaction.guild is None:
        await interaction.response.send_message("Użyj na serwerze.", ephemeral=True)
        return
    view = PolaczPanelView(interaction.user.id)
    await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)


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


@bot.tree.command(name="gif-lista", description="Lista GIF-ów z usuwaniem (interfejs; właściciel)")
async def cmd_gif_lista(interaction: discord.Interaction):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może to użyć.", ephemeral=True)
        return
    view = GifListaView(interaction.user.id)
    gifs = _win_gifs()
    await interaction.response.send_message(embed=view.build_embed(), view=view if gifs else None, ephemeral=True)


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



@bot.tree.command(name="panel", description="Panel kapitana z przyciskami (też DM)")
async def cmd_panel(interaction: discord.Interaction):
    if not bot.is_staff(interaction):
        await interaction.response.send_message("Tylko właściciel, kapitan, vicekapitan lub coach.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=interaction.guild is not None)
    emb = await _build_captain_panel_embed()
    await interaction.followup.send(embed=emb, view=CaptainPanelView(interaction.user.id))


@bot.tree.command(name="sklad-status", description="DM: status potwierdzeń składu")
async def cmd_sklad_status(interaction: discord.Interaction):
    if not bot.is_staff(interaction):
        await interaction.response.send_message("Tylko właściciel, kapitan, vicekapitan lub coach.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=interaction.guild is not None)
    try:
        upcoming = await asyncio.to_thread(bot.api.get_pindolz_upcoming)
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    nxt = bot._next_match(upcoming)
    if not nxt:
        await interaction.followup.send("Brak nadchodzącego meczu.")
        return
    _, m = nxt
    mid = int(m["id"])
    await interaction.followup.send(embed=_lineup_status_embed(m, mid))


@bot.tree.command(name="ping-sklad", description="DM: ponów prośbę o potwierdzenie do osób bez odpowiedzi")
async def cmd_ping_sklad(interaction: discord.Interaction):
    if not bot.is_staff(interaction):
        await interaction.response.send_message("Tylko właściciel, kapitan, vicekapitan lub coach.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=interaction.guild is not None)
    try:
        upcoming = await asyncio.to_thread(bot.api.get_pindolz_upcoming)
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    nxt = bot._next_match(upcoming)
    if not nxt:
        await interaction.followup.send("Brak nadchodzącego meczu.")
        return
    _, m = nxt
    mid = int(m["id"])
    roster, yes, no, pending = _lineup_status_lists(mid)
    if not pending:
        await interaction.followup.send("Wszyscy z składu już odpowiedzieli.")
        return
    # pending mentions -> ids
    data = _lineup_confirms(mid)
    pending_ids = [pid for pid in roster if data.get(str(pid)) not in ("yes", "no")]
    opp = _match_opponent(m)
    when = _when_text(m)
    ok, fail = [], []
    for pid in pending_ids:
        user = bot.get_user(pid)
        if user is None:
            try:
                user = await bot.fetch_user(pid)
            except Exception:
                fail.append(f"<@{pid}>")
                continue
        try:
            emb = discord.Embed(
                title="🔔 Przypomnienie: potwierdź skład PINDOLZ",
                description=(
                    f"Nadal czekamy na Twoją odpowiedź.\n"
                    f"**Rywal:** {opp}\n"
                    f"**Termin:** {when}\n\n"
                    f"Czy możesz grać?"
                ),
                color=0xFEE75C,
            )
            emb.set_footer(text=f"Mecz #{mid}")
            await user.send(embed=emb, view=sklad_confirm_view(mid))
            ok.append(f"<@{pid}>")
        except Exception:
            fail.append(f"<@{pid}>")
    lines = [f"Wysłano ponownie do **{len(ok)}**: {', '.join(ok) or '—'}"]
    if fail:
        lines.append(f"Nie udało się (PW?): {', '.join(fail)}")
    await interaction.followup.send("\n".join(lines))


@bot.tree.command(name="moj-status", description="DM: czy jesteś w składzie i co odpisałeś")
async def cmd_moj_status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=interaction.guild is not None)
    try:
        upcoming = await asyncio.to_thread(bot.api.get_pindolz_upcoming)
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    nxt = bot._next_match(upcoming)
    if not nxt:
        await interaction.followup.send("Brak nadchodzącego meczu PINDOLZ.")
        return
    _, m = nxt
    mid = int(m["id"])
    try:
        roster = [int(x) for x in json.loads(db.get_config(f"lineup_{mid}") or "[]")]
    except Exception:
        roster = []
    uid = interaction.user.id
    opp = _match_opponent(m)
    when = _when_text(m)
    if uid not in roster:
        await interaction.followup.send(
            f"Nie jesteś w składzie na najbliższy mecz (**vs {opp}**, {when})."
        )
        return
    st = _lineup_confirms(mid).get(str(uid))
    if st == "yes":
        ans = "✅ **Gram**"
    elif st == "no":
        ans = "❌ **Nie mogę**"
    else:
        ans = "⏳ **Brak odpowiedzi** – sprawdź DM od bota lub poczekaj na ponowienie od kapitana"
    await interaction.followup.send(
        f"Mecz **vs {opp}** · {when}\n"
        f"Jesteś w składzie.\n"
        f"Twoja odpowiedź: {ans}"
    )



@bot.tree.command(name="kapitan", description="Ustaw lub usuń kapitana (tylko właściciel serwera)")
@app_commands.describe(osoba="Kapitan (puste = usuń)")
async def cmd_kapitan(interaction: discord.Interaction, osoba: Optional[discord.Member] = None):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel serwera może ustawić kapitana.", ephemeral=True)
        return
    if osoba is None:
        db.set_config("captain_id", None)
        await interaction.response.send_message("Kapitan **usunięty**.", ephemeral=True)
        return
    if osoba.bot:
        await interaction.response.send_message("Bot nie może być kapitanem.", ephemeral=True)
        return
    db.set_config("captain_id", str(osoba.id))
    # vice nie może być tym samym
    if bot.vice_captain_id() == osoba.id:
        db.set_config("vice_captain_id", None)
    await interaction.response.send_message(f"Kapitan: **{osoba.mention}**", ephemeral=True)


@bot.tree.command(name="vicekapitan", description="Ustaw lub usuń vicekapitana (właściciel lub kapitan)")
@app_commands.describe(osoba="Vicekapitan (puste = usuń)")
async def cmd_vicekapitan(interaction: discord.Interaction, osoba: Optional[discord.Member] = None):
    if not bot.is_captain(interaction):
        await interaction.response.send_message("Tylko właściciel lub kapitan może ustawić vicekapitana.", ephemeral=True)
        return
    if osoba is None:
        db.set_config("vice_captain_id", None)
        await interaction.response.send_message("Vicekapitan **usunięty**.", ephemeral=True)
        return
    if osoba.bot:
        await interaction.response.send_message("Bot nie może być vicekapitanem.", ephemeral=True)
        return
    if bot.captain_id() == osoba.id:
        await interaction.response.send_message("Ta osoba jest już kapitanem. Najpierw zmień kapitana.", ephemeral=True)
        return
    db.set_config("vice_captain_id", str(osoba.id))
    await interaction.response.send_message(f"Vicekapitan: **{osoba.mention}**", ephemeral=True)


@bot.tree.command(name="sztab", description="Pokaż kapitana, vicekapitana i coacha")
async def cmd_sztab(interaction: discord.Interaction):
    cid, vid, coach = bot.captain_id(), bot.vice_captain_id(), bot.coach_id()
    emb = discord.Embed(title="👔 Sztab drużyny", color=0x5865F2)
    emb.add_field(name="Kapitan", value=f"<@{cid}>" if cid else "_nie ustawiono_", inline=True)
    emb.add_field(name="Vicekapitan", value=f"<@{vid}>" if vid else "_nie ustawiono_", inline=True)
    emb.add_field(name="Coach", value=f"<@{coach}>" if coach else "_nie ustawiono_", inline=True)
    emb.add_field(
        name="Uprawnienia sztabu",
        value="`/sklad` · `/panel` · `/polacz` · `/ping-sklad` · `/sklad-status` · `/ankieta-role` · `/trening` · `/zaplanuj`",
        inline=False,
    )
    emb.set_footer(text="/kapitan · /vicekapitan · /coach")
    await interaction.response.send_message(embed=emb, ephemeral=True)



@bot.tree.command(name="trening", description="Ankieta treningu: dni → godziny → wydarzenie (sztab)")
async def cmd_trening(interaction: discord.Interaction):
    if not bot.is_staff(interaction):
        await interaction.response.send_message(
            "Tylko właściciel, kapitan, vicekapitan lub coach.", ephemeral=True
        )
        return
    if interaction.guild is None:
        await interaction.response.send_message("Użyj na serwerze.", ephemeral=True)
        return
    emb = discord.Embed(
        title="🏋️ Nowy trening – krok 1",
        description=(
            "1. Zaznacz **dni tygodnia**, które mają być w ankiecie\n"
            "2. Kliknij **Opublikuj ankietę dni**\n"
            "3. Po głosowaniu sztab klika **Dalej: godziny**\n"
            "4. Po głosowaniu na godzinę: **Utwórz wydarzenie**\n\n"
            "Bot ogłosi termin i utworzy wydarzenie na serwerze."
        ),
        color=0x5865F2,
    )
    view = TreningSetupView(interaction.user.id)
    await interaction.response.send_message(embed=emb, view=view, ephemeral=True)



@bot.tree.command(name="ogloszenie", description="Wyślij ogłoszenie (sztab) – treść lub szablon")
@app_commands.describe(
    tresc="Treść (opcjonalnie, jeśli używasz szablonu)",
    szablon="Nazwa zapisanego szablonu",
    ping_roli="Opcjonalny ping roli",
)
async def cmd_ogloszenie(
    interaction: discord.Interaction,
    tresc: Optional[str] = None,
    szablon: Optional[str] = None,
    ping_roli: Optional[discord.Role] = None,
):
    if not bot.is_staff(interaction):
        await interaction.response.send_message("Tylko sztab.", ephemeral=True)
        return
    text = (tresc or "").strip()
    tpl_name = (szablon or "").strip()
    if tpl_name:
        tpls = announce_templates()
        # case-insensitive match
        key = next((k for k in tpls if k.lower() == tpl_name.lower()), None)
        if not key:
            await interaction.response.send_message(
                f"Brak szablonu `{tpl_name}`. Lista: `/szablon-lista`",
                ephemeral=True,
            )
            return
        text = tpls[key]
    if not text:
        await interaction.response.send_message(
            "Podaj `tresc:` albo `szablon:`. Szablony: `/szablon-lista`",
            ephemeral=True,
        )
        return
    emb = discord.Embed(title="📢 Ogłoszenie", description=text[:4000], color=0x5865F2)
    if tpl_name:
        emb.set_footer(text=f"Szablon: {tpl_name} · od {interaction.user.display_name}")
    else:
        emb.set_footer(text=f"Od {interaction.user.display_name}")
    msg = await bot.send_announcement(
        content=ping_roli.mention if ping_roli else None,
        embed=emb,
    )
    if not msg:
        await interaction.response.send_message(
            "Brak kanału ogłoszeń. Ustaw: `/setup-ogloszenia`.",
            ephemeral=True,
        )
        return
    await interaction.response.send_message(f"✅ Wysłano na {msg.channel.mention}", ephemeral=True)



@cmd_ogloszenie.autocomplete("szablon")
async def ogloszenie_szablon_autocomplete(interaction: discord.Interaction, current: str):
    tpls = announce_templates()
    cur = (current or "").lower()
    names = [n for n in tpls if cur in n.lower()][:25]
    return [app_commands.Choice(name=n[:100], value=n[:100]) for n in names]


@bot.tree.command(name="szablon-dodaj", description="Zapisz szablon ogłoszenia (sztab)")
@app_commands.describe(nazwa="Krótka nazwa (np. scrim, trening, info)", tresc="Treść szablonu")
async def cmd_szablon_dodaj(interaction: discord.Interaction, nazwa: str, tresc: str):
    if not bot.is_staff(interaction):
        await interaction.response.send_message("Tylko sztab.", ephemeral=True)
        return
    name = (nazwa or "").strip()[:40]
    body = (tresc or "").strip()[:1900]
    if not name or not body:
        await interaction.response.send_message("Podaj nazwę i treść.", ephemeral=True)
        return
    tpls = announce_templates()
    tpls[name] = body
    save_announce_templates(tpls)
    await interaction.response.send_message(
        f"✅ Szablon **{name}** zapisany. Użycie: `/ogloszenie szablon:{name}`",
        ephemeral=True,
    )


@bot.tree.command(name="szablon-lista", description="Lista szablonów ogłoszeń")
async def cmd_szablon_lista(interaction: discord.Interaction):
    tpls = announce_templates()
    if not tpls:
        await interaction.response.send_message(
            "Brak szablonów. Dodaj: `/szablon-dodaj`.",
            ephemeral=True,
        )
        return
    lines = [f"**{n}** — {t[:80]}{'…' if len(t) > 80 else ''}" for n, t in sorted(tpls.items())]
    emb = discord.Embed(title="📋 Szablony ogłoszeń", description="\n".join(lines)[:4000], color=0x5865F2)
    emb.set_footer(text="/ogloszenie szablon:nazwa · /szablon-usun")
    await interaction.response.send_message(embed=emb, ephemeral=True)


@bot.tree.command(name="szablon-usun", description="Usuń szablon ogłoszenia (sztab)")
@app_commands.describe(nazwa="Nazwa szablonu")
async def cmd_szablon_usun(interaction: discord.Interaction, nazwa: str):
    if not bot.is_staff(interaction):
        await interaction.response.send_message("Tylko sztab.", ephemeral=True)
        return
    tpls = announce_templates()
    key = next((k for k in tpls if k.lower() == (nazwa or "").strip().lower()), None)
    if not key:
        await interaction.response.send_message("Nie ma takiego szablonu.", ephemeral=True)
        return
    del tpls[key]
    save_announce_templates(tpls)
    await interaction.response.send_message(f"Usunięto szablon **{key}**.", ephemeral=True)


@bot.tree.command(name="zaplanuj", description="Zaplanuj wiadomość na kanał (sztab)")
@app_commands.describe(
    data="Data YYYY-MM-DD (np. 2026-10-20)",
    godzina="Godzina HH:MM (np. 18:30)",
    tresc="Treść wiadomości",
    kanal="Kanał (domyślnie bieżący)",
    ping_roli="Opcjonalnie rola do wspomnienia",
)
async def cmd_zaplanuj(
    interaction: discord.Interaction,
    data: str,
    godzina: str,
    tresc: str,
    kanal: Optional[discord.TextChannel] = None,
    ping_roli: Optional[discord.Role] = None,
):
    if not bot.is_staff(interaction):
        await interaction.response.send_message(
            "Tylko właściciel, kapitan, vicekapitan lub coach.", ephemeral=True
        )
        return
    if interaction.guild is None:
        await interaction.response.send_message("Użyj na serwerze.", ephemeral=True)
        return
    data_s = data.strip().replace(".", "-").replace("/", "-")
    godzina_s = godzina.strip().replace(".", ":")
    try:
        parts = godzina_s.split(":")
        if len(parts) >= 2:
            godzina_s = f"{int(parts[0]):02d}:{int(parts[1]):02d}"
        dt = datetime.strptime(f"{data_s} {godzina_s}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
    except ValueError:
        try:
            dt = datetime.strptime(f"{data_s} {godzina_s}", "%d-%m-%Y %H:%M").replace(tzinfo=TZ)
        except ValueError:
            await interaction.response.send_message(
                "Zły format. Data: `YYYY-MM-DD`, godzina: `HH:MM` (np. `2026-10-20` i `18:30`).",
                ephemeral=True,
            )
            return
    if dt.timestamp() < datetime.now(TZ).timestamp() - 30:
        await interaction.response.send_message("Termin jest w przeszłości.", ephemeral=True)
        return
    ch = kanal if kanal is not None else interaction.channel
    if ch is None or not hasattr(ch, "id"):
        await interaction.response.send_message("Wybierz kanał tekstowy (`kanal:`).", ephemeral=True)
        return
    content = (tresc or "").strip()[:1900]
    if not content:
        await interaction.response.send_message("Treść nie może być pusta.", ephemeral=True)
        return
    try:
        sid = _next_sched_id()
        payload = {
            "id": sid,
            "when": int(dt.timestamp()),
            "channel_id": int(ch.id),
            "content": content,
            "ping": ping_roli.mention if ping_roli else "",
            "sent": False,
            "by": interaction.user.id,
        }
        _save_sched(sid, payload)
        if not _load_sched(sid):
            await interaction.response.send_message("Błąd zapisu do bazy.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"✅ Zaplanowano **#{sid}** na <#{ch.id}>\n"
            f"⏰ <t:{int(dt.timestamp())}:F> · <t:{int(dt.timestamp())}:R>\n"
            f"Wysyłka automatyczna (co 30 s).",
            ephemeral=True,
        )
        print(f"[zaplanuj] #{sid} when={payload['when']} ch={ch.id}")
    except Exception as e:
        print(f"[zaplanuj] błąd: {e}")
        if interaction.response.is_done():
            await interaction.followup.send(f"Błąd: {e}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Błąd: {e}", ephemeral=True)


@bot.tree.command(name="zaplanuj-lista", description="Lista zaplanowanych wiadomości (sztab)")
async def cmd_zaplanuj_lista(interaction: discord.Interaction):
    if not bot.is_staff(interaction):
        await interaction.response.send_message("Tylko sztab.", ephemeral=True)
        return
    try:
        seq = int(db.get_config("sched_msg_seq") or "1")
    except Exception:
        seq = 1
    lines = []
    now = int(datetime.now(TZ).timestamp())
    for sid in range(max(1, seq - 50), seq):
        data = _load_sched(sid)
        if not data:
            continue
        when = int(data.get("when") or 0)
        if data.get("sent"):
            status = "✅ wysłano"
        elif when > now:
            status = "⏳ czeka"
        else:
            status = "🔄 do wysłania"
        preview = (data.get("content") or "")[:40].replace("\n", " ")
        lines.append(f"**#{sid}** {status} · <t:{when}:f> · <#{data.get('channel_id')}> · {preview}")
    if not lines:
        await interaction.response.send_message("Brak zaplanowanych wiadomości.", ephemeral=True)
        return
    emb = discord.Embed(title="📋 Zaplanowane wiadomości", description="\n".join(lines[-25:]), color=0x5865F2)
    await interaction.response.send_message(embed=emb, ephemeral=True)


@bot.tree.command(name="coach", description="Ustaw lub usuń coacha (właściciel lub kapitan)")
@app_commands.describe(osoba="Coach (puste = usuń)")
async def cmd_coach(interaction: discord.Interaction, osoba: Optional[discord.Member] = None):
    if not bot.is_captain(interaction):
        await interaction.response.send_message("Tylko właściciel lub kapitan może ustawić coacha.", ephemeral=True)
        return
    if osoba is None:
        db.set_config("coach_id", None)
        await interaction.response.send_message("Coach **usunięty**.", ephemeral=True)
        return
    if osoba.bot:
        await interaction.response.send_message("Bot nie może być coachem.", ephemeral=True)
        return
    db.set_config("coach_id", str(osoba.id))
    await interaction.response.send_message(f"Coach: **{osoba.mention}**", ephemeral=True)



@bot.event
async def on_ready():
    log("ready", f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    log("ready", f"Wersja: {BOT_VERSION}")
    try:
        embeds.AUTHOR_ICON = str(bot.user.display_avatar.url)
    except Exception:
        pass
    print("Bot gotowy – soft-start ~90 s (komendy + sync w trakcie).")
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
