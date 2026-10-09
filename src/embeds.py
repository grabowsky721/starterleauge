import discord
from datetime import datetime


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


def upcoming_embed(matches: list[dict]) -> discord.Embed:
    embed = discord.Embed(
        title="Nadchodzące mecze PINDOLZ",
        color=0xF59E0B,
        timestamp=datetime.utcnow(),
    )
    if not matches:
        embed.description = "Brak zaplanowanych meczów."
        return embed

    for m in matches[:8]:
        t1 = _team_name(m, "team1")
        t2 = _team_name(m, "team2")
        date = m.get("matchDate") or "?"
        time = (m.get("matchTime") or "")[:5]
        division = m.get("division") or ""
        embed.add_field(
            name=f"{date} {time}",
            value=f"**{t1}** vs **{t2}**\n{division}",
            inline=False,
        )
    return embed


def history_embed(matches: list[dict], limit: int = 8) -> discord.Embed:
    embed = discord.Embed(
        title="Ostatnie wyniki PINDOLZ",
        color=0x3B82F6,
        timestamp=datetime.utcnow(),
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
    if series:
        series_str = f"\nSeria: {series.get('team1', 0)}:{series.get('team2', 0)}"

    embed = discord.Embed(
        title="PINDOLZ gra teraz!",
        description=f"**{t1}** vs **{t2}**",
        color=0xEF4444,
        timestamp=datetime.utcnow(),
    )
    embed.add_field(name="Mapa", value=f"{map_name}\n**{s1}:{s2}**{series_str}", inline=False)
    embed.set_footer(text=match.get("division") or "")
    return embed


def match_started_embed(match: dict) -> discord.Embed:
    t1 = _team_name(match, "team1")
    t2 = _team_name(match, "team2")
    embed = discord.Embed(
        title="Mecz właśnie się zaczął",
        description=f"**PINDOLZ** zaczyna vs **{t2 if 'PINDOLZ' in t1 else t1}**",
        color=0x22C55E,
        timestamp=datetime.utcnow(),
    )
    embed.add_field(name="Dywizja", value=match.get("division") or "-", inline=True)
    embed.add_field(name="Best of", value=str(match.get("bestOf") or "?"), inline=True)
    return embed


def match_ended_embed(match: dict) -> discord.Embed:
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
        title="Mecz zakończony",
        description=f"**{t1}** {score} **{t2}**\nZwycięzca: **{winner}**",
        color=0x8B5CF6,
        timestamp=datetime.utcnow(),
    )
    embed.set_footer(text=match.get("division") or "")
    return embed
