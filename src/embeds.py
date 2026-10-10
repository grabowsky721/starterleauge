import discord
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Warsaw")
PINDOLZ_ID = 869
TEAM_URL = "https://starterleague.pl/team/869"
FOOTER = "PINDOLZ • StarterLeague"

C_WIN = 0x22C55E
C_LOSS = 0xEF4444
C_UPCOMING = 0xF59E0B
C_INFO = 0x3B82F6
C_TABLE = 0x10B981
C_TEAM = 0x6366F1
C_NEUTRAL = 0x8B5CF6


def _base(title: str, color: int, description: str | None = None) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(TZ),
    )
    embed.set_footer(text=FOOTER)
    return embed


def _add_links(embed: discord.Embed) -> discord.Embed:
    embed.add_field(
        name="🔗 Linki",
        value=f"[Profil PINDOLZ]({TEAM_URL})",
        inline=False,
    )
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


def _is_walkover(match: dict) -> bool:
    for key in ("isWalkover", "walkover", "isForfeit", "forfeit", "wo"):
        val = match.get(key)
        if val is True or (isinstance(val, str) and val.lower() in ("true", "1", "yes", "wo")):
            return True
    status = (match.get("status") or match.get("resultType") or "").lower()
    if "walkover" in status or status in ("wo", "forfeit"):
        return True
    note = str(match.get("note") or match.get("comment") or "").lower()
    if "walkover" in note or "walk over" in note or note == "wo":
        return True
    return False


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


def _signed(n: int | None) -> str:
    if n is None:
        return "–"
    return f"+{n}" if n > 0 else str(n)


def _medal(rank) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"`{rank}.`")


def upcoming_embed(matches: list[dict]) -> discord.Embed:
    embed = _base("Nadchodzące mecze PINDOLZ", C_UPCOMING)
    if not matches:
        embed.description = "Brak zaplanowanych meczów."
        return embed
    for m in matches[:8]:
        t1 = _team_name(m, "team1")
        t2 = _team_name(m, "team2")
        embed.add_field(
            name=_fmt_datetime(m),
            value=f"**{t1}** vs **{t2}**\n{m.get('division') or ''}",
            inline=False,
        )
    _add_links(embed)
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
    _add_links(embed)
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
    _add_links(embed)
    return embed


def history_embed(matches: list[dict], limit: int = 8) -> discord.Embed:
    embed = _base("Ostatnie wyniki PINDOLZ", C_INFO)
    if not matches:
        embed.description = "Brak historii."
        return embed
    for m in matches[:limit]:
        t1 = _team_name(m, "team1")
        t2 = _team_name(m, "team2")
        score = _score_str(m)
        date = m.get("matchDate") or "?"
        icon = _icon(_result(m))
        embed.add_field(
            name=f"{icon} {date} · {score}",
            value=f"**{t1}** vs **{t2}**\n{m.get('division') or ''}",
            inline=False,
        )
    _add_links(embed)
    return embed


def result_embed(
    match: dict,
    form: str | None = None,
    standing: dict | None = None,
) -> discord.Embed:
    t1 = _team_name(match, "team1")
    t2 = _team_name(match, "team2")
    res = _result(match)
    wo = _is_walkover(match)
    if wo and res is True:
        title, color = "🏳️ Walkower · zwycięstwo PINDOLZ", C_WIN
    elif wo and res is False:
        title, color = "🏳️ Walkower · porażka PINDOLZ", C_LOSS
    elif wo:
        title, color = "🏳️ Walkower", C_NEUTRAL
    elif res is True:
        title, color = "🏆 Zwycięstwo PINDOLZ!", C_WIN
    elif res is False:
        title, color = "💔 Porażka PINDOLZ", C_LOSS
    else:
        title, color = "📊 Wynik meczu PINDOLZ", C_NEUTRAL
    desc = f"## {t1}  {_score_str(match)}  {t2}"
    if wo:
        desc += "\n*Mecz rozstrzygnięty walkowerem*"
    embed = _base(title, color, desc)
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
    _add_links(embed)
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
    _add_links(embed)
    return embed


def match_started_embed(match: dict) -> discord.Embed:
    embed = _base(
        "🟢 Mecz właśnie się zaczął",
        C_WIN,
        f"## PINDOLZ  ⚔️  {_opponent(match)}",
    )
    embed.add_field(name="🏷️ Dywizja", value=match.get("division") or "-", inline=True)
    embed.add_field(name="🎯 Format", value=f"Bo{match.get('bestOf') or '?'}", inline=True)
    _add_links(embed)
    return embed


def match_ended_embed(
    match: dict,
    form: str | None = None,
    standing: dict | None = None,
) -> discord.Embed:
    return result_embed(match, form=form, standing=standing)


def schedule_changed_embed(match: dict, old_date: str | None, old_time: str | None) -> discord.Embed:
    opponent = _opponent(match)
    old_t = (old_time or "")[:5] if old_time else "?"
    old_d = old_date or "?"
    embed = _base(
        "📅 Zmiana terminu meczu",
        C_UPCOMING,
        f"## PINDOLZ  ⚔️  {opponent}",
    )
    embed.add_field(name="Było", value=f"`{old_d} {old_t}`", inline=True)
    embed.add_field(name="Jest", value=f"{_ts(match, 'F')}\n{_ts(match, 'R')}", inline=True)
    embed.add_field(name="🏷️ Dywizja", value=match.get("division") or "-", inline=False)
    _add_links(embed)
    return embed


def standings_embed(
    table: list[dict],
    division: str = "Starter Division 6",
    changes: dict | None = None,
) -> discord.Embed:
    embed = _base(f"🏆 Tabela · {division}", C_TABLE)
    if not table:
        embed.description = "Brak danych tabeli."
        return embed
    lines = []
    for row in table[:16]:
        rank = row.get("rank") or "?"
        team = (row.get("team") or {}).get("name") or "???"
        pts = row.get("points")
        w = row.get("wins") or 0
        l = row.get("losses") or 0
        rd = row.get("roundDifference")
        name = f"**{team}**" if team.upper() == "PINDOLZ" else team
        delta = ""
        if changes and team.upper() in changes:
            d = changes[team.upper()]
            if d > 0:
                delta = f" ▲{d}"
            elif d < 0:
                delta = f" ▼{abs(d)}"
        rank_label = _medal(rank) if isinstance(rank, int) else f"`{rank}.`"
        lines.append(
            f"{rank_label} {name}  ·  "
            f"{w}W {l}L  ·  RD {rd if rd is not None else '–'}  ·  "
            f"**{pts if pts is not None else '–'} pkt**{delta}"
        )
    embed.description = "\n".join(lines)
    _add_links(embed)
    return embed


def weekly_summary_embed(
    matches: list[dict],
    wins: int,
    losses: int,
    standing: dict | None,
) -> discord.Embed:
    embed = _base("Podsumowanie tygodnia · PINDOLZ", C_TEAM)
    embed.add_field(name="Mecze", value=str(len(matches)), inline=True)
    embed.add_field(name="Bilans", value=f"**{wins}W – {losses}L**", inline=True)
    if standing:
        embed.add_field(
            name="Pozycja",
            value=f"**{standing.get('rank')}.** · {standing.get('points', '–')} pkt",
            inline=True,
        )
    if matches:
        lines = [
            f"`{m.get('matchDate') or '?'}` {_team_name(m, 'team1')} {_score_str(m)} {_team_name(m, 'team2')}"
            for m in matches[:10]
        ]
        embed.add_field(name="Wyniki", value="\n".join(lines), inline=False)
    else:
        embed.description = "Brak meczów w tym tygodniu."
    _add_links(embed)
    return embed


def restart_embed(version: str, main_id: int | None, live_id: int | None, table_id: int | None) -> discord.Embed:
    def ch(cid):
        return f"<#{cid}>" if cid else "—"
    embed = _base("✅ Bot online", C_TABLE, f"Wersja **`{version}`** · taski startują stopniowo.")
    embed.add_field(
        name="Kanały",
        value=f"Główny: {ch(main_id)}\nLIVE: {ch(live_id)}\nTabela: {ch(table_id)}",
        inline=False,
    )
    embed.set_footer(text="Ta wiadomość zniknie za 10 minut")
    return embed


def help_embed() -> discord.Embed:
    embed = _base("📖 Komendy PINDOLZ bota", C_INFO)
    embed.add_field(
        name="📊 Mecze i tabela",
        value=(
            "`/pindolz` · najbliższe i ostatnie\n"
            "`/nadchodzace` · nadchodzące\n"
            "`/wyniki` · ostatnie wyniki\n"
            "`/live` · czy gra teraz\n"
            "`/tabela` · Division 6\n"
            "`/wersja` · wersja bota\n"
            "`/status` · API i kanały\n"
            "`/pomoc` · ta lista"
        ),
        inline=False,
    )
    embed.add_field(
        name="⚙️ Dla właściciela",
        value=(
            "`/setup` · kanał główny\n"
            "`/setup-live` · kanał LIVE\n"
            "`/setup-tabela` · kanał tabeli\n"
            "`/setup-all` · wszystkie kanały naraz"
        ),
        inline=False,
    )
    embed.add_field(
        name="🤖 Automatycznie",
        value=(
            "⏰ przypomnienie 30 min przed meczem\n"
            "🔴 LIVE co 5–10 s + przycisk kanału\n"
            "📅 zmiana terminu meczu\n"
            "🏳️ wynik walkowerem (osobny styl)\n"
            "🏆 tabela: 08:00, 18:00, 20:00, 21:30, 23:00\n"
            "🗓️ podsumowanie tygodnia (niedziela 20:00)"
        ),
        inline=False,
    )
    return embed
