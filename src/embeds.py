import discord
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Warsaw")


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
    if t1.get("name", "").upper() == "PINDOLZ":
        return t2.get("name") or "???"
    if t2.get("name", "").upper() == "PINDOLZ":
        return t1.get("name") or "???"
    # fallback po id
    if t1.get("id") == 869:
        return t2.get("name") or "???"
    return t1.get("name") or "???"


def _fmt_datetime(match: dict) -> str:
    date = match.get("matchDate") or "?"
    time = (match.get("matchTime") or "")[:5]
    if time:
        return f"{date} {time}"
    return date


def upcoming_embed(matches: list[dict]) -> discord.Embed:
    embed = discord.Embed(
        title="Nadchodzące mecze PINDOLZ",
        color=0xF59E0B,
        timestamp=datetime.now(TZ),
    )
    if not matches:
        embed.description = "Brak zaplanowanych meczów."
        return embed

    for m in matches[:8]:
        t1 = _team_name(m, "team1")
        t2 = _team_name(m, "team2")
        dt = _fmt_datetime(m)
        division = m.get("division") or ""
        embed.add_field(
            name=dt,
            value=f"**{t1}** vs **{t2}**\n{division}",
            inline=False,
        )
    return embed


def single_upcoming_embed(match: dict) -> discord.Embed:
    opponent = _opponent(match)
    dt = _fmt_datetime(match)
    division = match.get("division") or "-"
    embed = discord.Embed(
        title="Nadchodzący mecz PINDOLZ",
        description=f"**PINDOLZ** vs **{opponent}**",
        color=0xF59E0B,
        timestamp=datetime.now(TZ),
    )
    embed.add_field(name="Termin", value=dt, inline=True)
    embed.add_field(name="Dywizja", value=division, inline=True)
    embed.add_field(name="Best of", value=str(match.get("bestOf") or "?"), inline=True)
    return embed


def history_embed(matches: list[dict], limit: int = 8) -> discord.Embed:
    embed = discord.Embed(
        title="Ostatnie wyniki PINDOLZ",
        color=0x3B82F6,
        timestamp=datetime.now(TZ),
    )
    if not matches:
        embed.description = "Brak historii."
        return embed

    for m in matches[:limit]:
        t1 = _team_name(m, "team1")
        t2 = _team_name(m, "team2")
        score = _score_str(m)
        date = m.get("matchDate") or "?"
        division = m.get("division") or ""
        embed.add_field(
            name=f"{date} · {score}",
            value=f"**{t1}** vs **{t2}**\n{division}",
            inline=False,
        )
    return embed


def result_embed(match: dict) -> discord.Embed:
    t1 = _team_name(match, "team1")
    t2 = _team_name(match, "team2")
    score = _score_str(match)
    winner_id = match.get("winnerTeamId")
    winner = "Remis / brak"
    if winner_id:
        if (match.get("team1") or {}).get("id") == winner_id:
            winner = t1
        elif (match.get("team2") or {}).get("id") == winner_id:
            winner = t2

    embed = discord.Embed(
        title="Wynik meczu PINDOLZ",
        description=f"**{t1}** {score} **{t2}**\nZwycięzca: **{winner}**",
        color=0x8B5CF6,
        timestamp=datetime.now(TZ),
    )
    embed.add_field(name="Data", value=match.get("matchDate") or "-", inline=True)
    embed.add_field(name="Dywizja", value=match.get("division") or "-", inline=True)
    return embed


def live_embed(match: dict) -> discord.Embed:
    t1 = _team_name(match, "team1")
    t2 = _team_name(match, "team2")
    current = match.get("currentMap") or {}
    map_name = current.get("name") or "?"
    map_score = current.get("score") or {}
    s1 = map_score.get("team1", 0)
    s2 = map_score.get("team2", 0)
    series = match.get("seriesScore") or {}
    series_str = ""
    if series and series.get("team1") is not None:
        series_str = f"\nSeria: {series.get('team1', 0)}:{series.get('team2', 0)}"

    embed = discord.Embed(
        title="PINDOLZ gra teraz!",
        description=f"**{t1}** vs **{t2}**",
        color=0xEF4444,
        timestamp=datetime.now(TZ),
    )
    embed.add_field(name="Mapa", value=f"{map_name}\n**{s1}:{s2}**{series_str}", inline=False)
    embed.set_footer(text=match.get("division") or "")
    return embed


def match_started_embed(match: dict) -> discord.Embed:
    opponent = _opponent(match)
    embed = discord.Embed(
        title="Mecz właśnie się zaczął",
        description=f"**PINDOLZ** zaczyna vs **{opponent}**",
        color=0x22C55E,
        timestamp=datetime.now(TZ),
    )
    embed.add_field(name="Dywizja", value=match.get("division") or "-", inline=True)
    embed.add_field(name="Best of", value=str(match.get("bestOf") or "?"), inline=True)
    return embed


def match_ended_embed(match: dict) -> discord.Embed:
    return result_embed(match)


def standings_embed(table: list[dict], division: str = "Starter Division 6") -> discord.Embed:
    embed = discord.Embed(
        title=f"Tabela · {division}",
        color=0x10B981,
        timestamp=datetime.now(TZ),
    )
    if not table:
        embed.description = "Brak danych tabeli."
        return embed

    lines = []
    for row in table[:16]:
        rank = row.get("rank") or "?"
        team = (row.get("team") or {}).get("name") or "???"
        pts = row.get("points")
        mp = row.get("matchesPlayed")
        w = row.get("wins")
        l = row.get("losses")
        rd = row.get("roundDifference")
        form = row.get("recentForm") or []
        form_str = "".join(form[-5:]) if form else ""

        # podświetl PINDOLZ
        name = f"**{team}**" if team.upper() == "PINDOLZ" else team
        line = f"`{rank:>2}.` {name}  ·  {w or 0}W {l or 0}L  ·  RD {rd if rd is not None else '–'}  ·  **{pts if pts is not None else '–'} pkt**"
        if form_str:
            line += f"  ·  {form_str}"
        lines.append(line)

    embed.description = "\n".join(lines)
    return embed
