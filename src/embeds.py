import discord
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Warsaw")
PINDOLZ_ID = 869
FOOTER = "PINDOLZ • StarterLeague"

C_WIN = 0x22C55E
C_LOSS = 0xEF4444
C_UPCOMING = 0xF59E0B
C_INFO = 0x3B82F6
C_TABLE = 0x10B981
C_TEAM = 0x6366F1
C_NEUTRAL = 0x8B5CF6


# ---------- helpery ----------
def _base(title: str, color: int, description: str | None = None) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(TZ),
    )
    embed.set_footer(text=FOOTER)
    return embed


def _team_name(match: dict, side: str) -> str:
    team = match.get(side) or {}
    return team.get("name") or "???"


def _score_str(match: dict) -> str:
    score = match.get("score") or {}
    s1 = score.get("team1")
    s2 = score.get("team2")
    if s1 is None or s2 is None:
        return "-:-"
    return f"{s1}:{s2}"


def _opponent(match: dict) -> str:
    t1 = match.get("team1") or {}
    t2 = match.get("team2") or {}
    if t1.get("id") == PINDOLZ_ID or (t1.get("name") or "").upper() == "PINDOLZ":
        return t2.get("name") or "???"
    return t1.get("name") or "???"


def _result(match: dict) -> bool | None:
    winner = match.get("winnerTeamId")
    if winner is None:
        return None
    return winner == PINDOLZ_ID


def _icon(result: bool | None) -> str:
    return {True: "🟩", False: "🟥", None: "⬜"}[result]


def _form_icons(form: str | None) -> str:
    if not form:
        return "–"
    return " ".join({"W": "🟩", "L": "🟥"}.get(c, "⬜") for c in form)


def _match_dt(match: dict) -> datetime | None:
    date = match.get("matchDate")
    if not date:
        return None
    time = (match.get("matchTime") or "00:00:00")[:8]
    if len(time) == 5:
        time += ":00"
    try:
        return datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)
    except Exception:
        return None


def _ts(match: dict, style: str = "F") -> str:
    dt = _match_dt(match)
    if not dt:
        return match.get("matchDate") or "?"
    return f"<t:{int(dt.timestamp())}:{style}>"


def _fmt_datetime(match: dict) -> str:
    date = match.get("matchDate") or "?"
    time = (match.get("matchTime") or "")[:5]
    return f"{date} {time}" if time else date


def _signed(value) -> str:
    try:
        return f"{int(value):+d}"
    except Exception:
        return "–"


def _medal(rank) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "🏅")


# ---------- nadchodzące ----------
def upcoming_embed(matches: list[dict]) -> discord.Embed:
    embed = _base("📅 Nadchodzące mecze PINDOLZ", C_UPCOMING)
    if not matches:
        embed.description = "Brak zaplanowanych meczów."
        return embed

    lines = []
    for m in matches[:8]:
        division = m.get("division") or ""
        lines.append(
            f"🕒 {_ts(m, 'F')} · {_ts(m, 'R')}\n"
            f"**{_team_name(m, 'team1')}** vs **{_team_name(m, 'team2')}**"
            + (f"\n*{division}*" if division else "")
        )
    embed.description = "\n\n".join(lines)
    return embed


def single_upcoming_embed(match: dict) -> discord.Embed:
    embed = _base(
        "📅 Nadchodzący mecz PINDOLZ",
        C_UPCOMING,
        f"## PINDOLZ  ⚔️  {_opponent(match)}",
    )
    embed.add_field(name="🕒 Termin", value=f"{_ts(match, 'F')}\n{_ts(match, 'R')}", inline=True)
    embed.add_field(name="🏷️ Dywizja", value=match.get("division") or "-", inline=True)
    embed.add_field(name="🎯 Format", value=f"Bo{match.get('bestOf') or '?'}", inline=True)
    return embed


def prematch_embed(
    match: dict,
    form: str | None = None,
    standing: dict | None = None,
    opp_standing: dict | None = None,
) -> discord.Embed:
    opponent = _opponent(match)
    embed = _base(
        "⏰ Mecz PINDOLZ już za chwilę!",
        C_UPCOMING,
        f"## PINDOLZ  ⚔️  {opponent}\nStart {_ts(match, 'R')}",
    )
    embed.add_field(name="🕒 Godzina", value=_ts(match, "t"), inline=True)
