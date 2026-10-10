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
    embed.add_field(name="🏷️ Dywizja", value=match.get("division") or "-", inline=True)
    embed.add_field(name="🎯 Format", value=f"Bo{match.get('bestOf') or '?'}", inline=True)

    if standing and standing.get("rank") is not None:
        embed.add_field(
            name="📊 PINDOLZ",
            value=f"{standing.get('rank')}. miejsce · **{standing.get('points', '–')}** pkt",
            inline=True,
        )
    if opp_standing and opp_standing.get("rank") is not None:
        embed.add_field(
            name=f"📊 {opponent}",
            value=f"{opp_standing.get('rank')}. miejsce · **{opp_standing.get('points', '–')}** pkt",
            inline=True,
        )
    if form:
        embed.add_field(name="🔥 Forma PINDOLZ", value=_form_icons(form), inline=False)
    return embed


# ---------- historia i wyniki ----------
def history_embed(matches: list[dict], limit: int = 8) -> discord.Embed:
    embed = _base("📜 Ostatnie wyniki PINDOLZ", C_INFO)
    if not matches:
        embed.description = "Brak historii."
        return embed

    lines = []
    for m in matches[:limit]:
        lines.append(
            f"{_icon(_result(m))} `{m.get('matchDate') or '?'}`  "
            f"**{_team_name(m, 'team1')}** {_score_str(m)} **{_team_name(m, 'team2')}**"
        )
    embed.description = "\n".join(lines)
    return embed


def result_embed(
    match: dict,
    form: str | None = None,
    standing: dict | None = None,
) -> discord.Embed:
    t1 = _team_name(match, "team1")
    t2 = _team_name(match, "team2")
    res = _result(match)

    if res is True:
        title, color = "🏆 Zwycięstwo PINDOLZ!", C_WIN
    elif res is False:
        title, color = "💔 Porażka PINDOLZ", C_LOSS
    else:
        title, color = "📊 Wynik meczu PINDOLZ", C_NEUTRAL

    embed = _base(title, color, f"## {t1}  {_score_str(match)}  {t2}")
    embed.add_field(name="📅 Data", value=match.get("matchDate") or "-", inline=True)
    embed.add_field(name="🏷️ Dywizja", value=match.get("division") or "-", inline=True)

    if form:
        embed.add_field(name="🔥 Forma (ost. 5)", value=_form_icons(form), inline=False)

    if standing and standing.get("rank") is not None:
        pts = standing.get("points")
        embed.add_field(
            name="📊 Pozycja w tabeli",
            value=f"{_medal(standing.get('rank'))} **{standing.get('rank')}.** miejsce · **{pts if pts is not None else '–'}** pkt",
            inline=False,
        )
    return embed


# ---------- live ----------
def live_embed(match: dict) -> discord.Embed:
    t1 = _team_name(match, "team1")
    t2 = _team_name(match, "team2")
    current = match.get("currentMap") or {}
    map_name = current.get("name") or "?"
    map_score = current.get("score") or {}
    s1 = map_score.get("team1", 0)
    s2 = map_score.get("team2", 0)
    series = match.get("seriesScore") or {}

    embed = _base("🔴 LIVE · PINDOLZ gra teraz!", C_LOSS, f"## {t1}  vs  {t2}")
    embed.add_field(name="🗺️ Mapa", value=map_name, inline=True)
    embed.add_field(name="⚔️ Wynik mapy", value=f"**{s1}:{s2}**", inline=True)
    if series and series.get("team1") is not None:
        embed.add_field(
            name="📈 Seria",
            value=f"**{series.get('team1', 0)}:{series.get('team2', 0)}**",
            inline=True,
        )
    embed.set_footer(text=match.get("division") or FOOTER)
    return embed


def match_started_embed(match: dict) -> discord.Embed:
    embed = _base(
        "🟢 Mecz właśnie się zaczął",
        C_WIN,
        f"## PINDOLZ  ⚔️  {_opponent(match)}",
    )
    embed.add_field(name="🏷️ Dywizja", value=match.get("division") or "-", inline=True)
    embed.add_field(name="🎯 Format", value=f"Bo{match.get('bestOf') or '?'}", inline=True)
    return embed


def match_ended_embed(
    match: dict,
    form: str | None = None,
    standing: dict | None = None,
) -> discord.Embed:
    return result_embed(match, form=form, standing=standing)


# ---------- tabela ----------
def standings_embed(
    table: list[dict],
    division: str = "Starter Division 6",
    changes: dict | None = None,
) -> discord.Embed:
    embed = _base(f"🏆 Tabela · {division}", C_TABLE)
    if not table:
        embed.description = "Brak danych tabeli."
        return embed

    changes = changes or {}
    lines = [f" {'#':>2}  {'Drużyna':<14} {'W-L':>5} {'RD':>4} {'Pkt':>4}"]
    lines.append("─" * 35)
    for row in table[:16]:
        rank = row.get("rank") or "?"
        team = (row.get("team") or {}).get("name") or "???"
        is_us = team.upper() == "PINDOLZ"
        wl = f"{row.get('wins') or 0}-{row.get('losses') or 0}"
        pts = row.get("points")
        marker = "▶" if is_us else " "
        delta = changes.get(team.upper(), 0)
        arrow = "▲" if delta > 0 else "▼" if delta < 0 else " "
        lines.append(
            f"{marker}{str(rank):>2}{arrow} {team[:14]:<14} {wl:>5} "
            f"{_signed(row.get('roundDifference')):>4} {pts if pts is not None else '–':>4}"
        )

    embed.description = "```\n" + "\n".join(lines) + "\n```"
    embed.set_footer(text="▶ PINDOLZ • ▲▼ zmiana pozycji • RD = różnica rund")
    return embed


# ---------- podsumowanie tygodnia ----------
def weekly_summary_embed(
    matches: list[dict],
    wins: int,
    losses: int,
    standing: dict | None,
) -> discord.Embed:
    embed = _base("🗓️ Podsumowanie tygodnia · PINDOLZ", C_TEAM)
    embed.add_field(name="🎮 Mecze", value=f"**{len(matches)}**", inline=True)
    embed.add_field(name="⚖️ Bilans", value=f"**{wins}W – {losses}L**", inline=True)

    if standing and standing.get("rank") is not None:
        pts = standing.get("points")
        embed.add_field(
            name="📊 Pozycja",
            value=f"{_medal(standing.get('rank'))} **{standing.get('rank')}.** · {pts if pts is not None else '–'} pkt",
            inline=True,
        )

    if matches:
        lines = [
            f"{_icon(_result(m))} `{m.get('matchDate') or '?'}` "
            f"{_team_name(m, 'team1')} {_score_str(m)} {_team_name(m, 'team2')}"
            for m in matches[:10]
        ]
        embed.add_field(name="📜 Wyniki", value="\n".join(lines), inline=False)
    else:
        embed.description = "Brak meczów w tym tygodniu."
    return embed


# ---------- karta drużyny ----------
def team_embed(
    standing: dict | None,
    history: list[dict],
    upcoming: list[dict],
    form: str | None,
    table_size: int = 0,
    division: str = "Starter Division 6",
) -> discord.Embed:
    embed = _base("🛡️ PINDOLZ", C_TEAM, f"**{division}**")

    if standing:
        rank = standing.get("rank")
        wins = standing.get("wins") or 0
        losses = standing.get("losses") or 0
        pts = standing.get("points")
        total = wins + losses
        winrate = f"{round(wins / total * 100)}%" if total else "–"
        rank_str = f"{_medal(rank)} **{rank}.**" + (f" / {table_size}" if table_size else "")

        embed.add_field(name="📍 Miejsce", value=rank_str, inline=True)
        embed.add_field(name="⭐ Punkty", value=f"**{pts if pts is not None else '–'}**", inline=True)
        embed.add_field(name="📈 Winrate", value=f"**{winrate}**", inline=True)
        embed.add_field(name="⚖️ Bilans", value=f"**{wins}W – {losses}L**", inline=True)
        embed.add_field(name="🎯 Różnica rund", value=f"**{_signed(standing.get('roundDifference'))}**", inline=True)
        embed.add_field(name="🎮 Mecze", value=f"**{total}**", inline=True)
    else:
        embed.add_field(name="📍 Tabela", value="Brak danych", inline=False)

    embed.add_field(name="🔥 Forma (ost. 5)", value=_form_icons(form), inline=False)

    if history:
        last = history[0]
        embed.add_field(
            name="⏮️ Ostatni mecz",
            value=(
                f"{_icon(_result(last))} {_team_name(last, 'team1')} "
                f"**{_score_str(last)}** {_team_name(last, 'team2')}"
            ),
            inline=False,
        )

    future = [m for m in upcoming if _match_dt(m)]
    future.sort(key=lambda m: _match_dt(m))
    if future:
        nxt = future[0]
        embed.add_field(
            name="⏭️ Następny mecz",
            value=f"vs **{_opponent(nxt)}**\n{_ts(nxt, 'F')} · {_ts(nxt, 'R')}",
            inline=False,
        )
    return embed


# ---------- forma ----------
def form_embed(form: str | None, matches: list[dict]) -> discord.Embed:
    wins = (form or "").count("W")
    losses = (form or "").count("L")
    if wins > losses:
        color = C_WIN
    elif losses > wins:
        color = C_LOSS
    else:
        color = C_NEUTRAL

    embed = _base("🔥 Forma PINDOLZ", color)
    if not form:
        embed.description = "Brak rozegranych meczów."
        return embed

    embed.description = f"## {_form_icons(form)}\n**{wins}W – {losses}L** w ostatnich {len(form)} meczach"
    if matches:
        lines = [
            f"{_icon(_result(m))} `{m.get('matchDate') or '?'}` "
            f"{_team_name(m, 'team1')} **{_score_str(m)}** {_team_name(m, 'team2')}"
            for m in matches[:5]
        ]
        embed.add_field(name="📜 Ostatnie mecze", value="\n".join(lines), inline=False)
    return embed


# ---------- ping / pomoc / online ----------
def ping_embed(latency_ms: int, uptime: str) -> discord.Embed:
    embed = _base("🏓 Pong!", C_TABLE)
    embed.add_field(name="📶 Opóźnienie", value=f"**{latency_ms} ms**", inline=True)
    embed.add_field(name="⏱️ Działa od", value=f"**{uptime}**", inline=True)
    embed.add_field(name="✅ Status", value="Bot działa", inline=True)
    return embed


def online_embed() -> discord.Embed:
    embed = _base("✅ Bot online", C_TABLE, "PINDOLZ bot właśnie wystartował i działa.")
    embed.set_footer(text="Ta wiadomość zniknie za 5 minut")
    return embed


def help_embed() -> discord.Embed:
    embed = _base("📖 Komendy PINDOLZ bota", C_INFO)
    embed.add_field(
        name="📊 Mecze i tabela",
        value=(
            "`/pindolz` · najbliższe i ostatnie mecze\n"
            "`/nadchodzace` · nadchodzące mecze\n"
            "`/wyniki` · ostatnie wyniki\n"
            "`/live` · czy PINDOLZ gra teraz\n"
            "`/tabela` · tabela Division 6\n"
            "`/team` · karta drużyny\n"
            "`/forma` · forma z ostatnich 5 meczów"
        ),
        inline=False,
    )
    embed.add_field(
        name="🛠️ Inne",
        value="`/ping` · czy bot działa\n`/pomoc` · ta lista",
        inline=False,
    )
    embed.add_field(
        name="⚙️ Dla właściciela serwera",
        value=(
            "`/setup` · kanał wyników i przypomnień\n"
            "`/setup-live` · kanał LIVE\n"
            "`/setup-tabela` · kanał tabeli"
        ),
        inline=False,
    )
    embed.add_field(
        name="🤖 Automatycznie",
        value=(
            "⏰ przypomnienie 30 min przed meczem\n"
            "🔴 wyniki na żywo\n"
            "🏆 tabela o 08:00, 18:00, 20:00, 21:30, 23:00\n"
            "🗓️ podsumowanie tygodnia w niedzielę o 20:00"
        ),
        inline=False,
    )
    return embed
