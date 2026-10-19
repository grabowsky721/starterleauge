import discord
import random
import re
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Warsaw")
PINDOLZ_ID = 869
TEAM_URL = "https://starterleague.pl/team/869"
SITE = "https://starterleague.pl"
FOOTER = "PINDOLZ • StarterLeague"

# cache: team_id -> (logo_url|None, expires_at)
_logo_cache: dict[int, tuple[str | None, datetime]] = {}
_LOGO_TTL = timedelta(hours=6)


def _abs_media_url(path: str | None) -> str | None:
    if not path or not isinstance(path, str):
        return None
    path = path.strip()
    if path.startswith("https://") or path.startswith("http://"):
        return path
    if path.startswith("/"):
        return SITE + path
    return None


def _logo_from_team_dict(team: dict | None) -> str | None:
    if not isinstance(team, dict):
        return None
    for key in ("logo", "logoUrl", "logoURL", "image", "avatar", "icon", "badge"):
        val = team.get(key)
        if isinstance(val, str):
            u = _abs_media_url(val)
            if u:
                return u
        elif isinstance(val, dict):
            u = _abs_media_url(val.get("url") or val.get("src"))
            if u:
                return u
    return None


def _logo_from_team_page(team_id: int) -> str | None:
    """Fallback: logo z strony drużyny (og:image /uploads/)."""
    now = datetime.now(TZ)
    tid = int(team_id)
    hit = _logo_cache.get(tid)
    if hit and hit[1] > now:
        return hit[0]
    url = None
    try:
        req = urllib.request.Request(
            f"{SITE}/team/{tid}",
            headers={"User-Agent": "PINDOLZ-Bot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        m = re.search(
            r'property="og:image"\s+content="(https://starterleague\.pl/uploads/[^"]+)"',
            html,
        )
        if not m:
            m = re.search(
                r'content="(https://starterleague\.pl/uploads/[^"]+\.(?:png|jpg|webp))"',
                html,
            )
        if m:
            url = m.group(1)
        if not url:
            m = re.search(r'src="(/uploads/\d+\.(?:png|jpg|webp))"', html)
            if m:
                url = SITE + m.group(1)
    except Exception:
        url = None
    _logo_cache[tid] = (url, now + _LOGO_TTL)
    return url


def _team_logo(match: dict, side: str) -> str | None:
    team = match.get(side) or {}
    u = _logo_from_team_dict(team)
    if u:
        return u
    tid = team.get("id")
    if tid is None:
        return None
    try:
        return _logo_from_team_page(int(tid))
    except Exception:
        return None


def _pindolz_side(match: dict) -> str:
    t1 = match.get("team1") or {}
    try:
        if int(t1.get("id") or 0) == PINDOLZ_ID:
            return "team1"
    except Exception:
        pass
    name = (t1.get("name") or "").upper()
    if "PINDOL" in name:
        return "team1"
    return "team2"


def _attach_match_logos(embed: discord.Embed, match: dict) -> discord.Embed:
    """Logo PINDOLZ (author), logo przeciwnika (thumbnail)."""
    try:
        p_side = _pindolz_side(match)
        o_side = "team2" if p_side == "team1" else "team1"
        p_logo = _team_logo(match, p_side)
        o_logo = _team_logo(match, o_side)
        p_name = _team_name(match, p_side)
        if p_logo:
            embed.set_author(name=p_name or "PINDOLZ", icon_url=p_logo, url=TEAM_URL)
        if o_logo:
            embed.set_thumbnail(url=o_logo)
    except Exception:
        pass
    return embed

DIVISION = "Starter Division 6"  # aktualizowane automatycznie przez bota (wykrywanie dywizji)


def set_division(name: str | None) -> None:
    global DIVISION
    if name:
        DIVISION = name


# Komentarze pod wynikiem (59) – edytuj dowolnie. Dla danego meczu zawsze wybierany jest ten sam.
RESULT_COMMENTS_WIN = [
    "Czysta robota! 🔥",
    "GG WP, PINDOLZ! 🚩",
    "Tak się to robi! 💪",
    "Kolejne punkty na koncie 🏆",
    "Maszyna jedzie dalej 🚀",
    "Rywal nie miał szans 😎",
    "Zasłużona wygrana! 👏",
]
RESULT_COMMENTS_LOSS = [
    "Wracamy mocniejsi 💪",
    "Następnym razem będzie nasze 🚩",
    "To tylko jedna przegrana bitwa ⚔️",
    "Wyciągamy wnioski i jedziemy dalej 🧠",
    "Głowa do góry, PINDOLZ! 🚩",
    "Rewanż będzie słodki 😤",
]
AUTHOR_NAME = "PINDOLZ"
AUTHOR_ICON: str | None = None  # ustawiane przez bota po starcie (avatar bota)

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
    embed.set_author(name=AUTHOR_NAME, url=TEAM_URL, icon_url=AUTHOR_ICON)
    embed.set_footer(text=FOOTER)
    return embed


def match_url(match: dict | int | None) -> str | None:
    """Link do strony meczu na StarterLeague (np. /match/2558)."""
    if match is None:
        return None
    mid = match.get("id") if isinstance(match, dict) else match
    if mid is None:
        return None
    try:
        return f"https://starterleague.pl/match/{int(mid)}"
    except (TypeError, ValueError):
        return None


def _add_links(embed: discord.Embed, match: dict | int | None = None) -> discord.Embed:
    parts = [f"[Profil PINDOLZ]({TEAM_URL})"]
    url = match_url(match)
    if url:
        parts.append(f"[Szczegóły meczu]({url})")
    embed.add_field(name="🔗 Linki", value=" · ".join(parts), inline=False)
    return embed


def _team_name(match: dict, side: str) -> str:
    team = match.get(side) or {}
    return (team.get("name") or "").strip() or "—"


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
        # API: jak jest data, jest też godzina – brak daty = brak terminu
        return "nie ustalono terminu"
    return f"<t:{int(dt.timestamp())}:{style}>"


def _fmt_datetime(match: dict) -> str:
    date = match.get("matchDate")
    if not date:
        return "nie ustalono terminu"
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
    if matches:
        _attach_match_logos(embed, matches[0])
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
    _add_links(embed, match)
    return _attach_match_logos(embed, match)


def prematch_embed(
    match: dict,
    form: str | None = None,
    standing: dict | None = None,
    opp_standing: dict | None = None,
    minutes: int = 30,
    lineup: list[int] | None = None,
    nicks: dict[int, str] | None = None,
) -> discord.Embed:
    opponent = _opponent(match)
    if minutes >= 60:
        title = "⏰ Mecz PINDOLZ za ok. 1 godzinę!"
    else:
        title = "⏰ Mecz PINDOLZ już za chwilę!"
    embed = _base(
        title,
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
    if lineup:
        embed.add_field(name="👥 Skład", value="\n".join(_player_line(u, nicks) for u in lineup[:10]), inline=False)
    _add_links(embed, match)
    return _attach_match_logos(embed, match)


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
    elif res is not None:
        pool = RESULT_COMMENTS_WIN if res else RESULT_COMMENTS_LOSS
        if pool:
            seed = str(match.get("id") or match.get("matchDate") or "")
            desc += f"\n*{random.Random(seed).choice(pool)}*"
    embed = _base(title, color, desc)
    embed.add_field(name="📅 Data", value=match.get("matchDate") or "nie ustalono terminu", inline=True)
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
    _add_links(embed, match)
    return _attach_match_logos(embed, match)


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
    _add_links(embed, match)
    return _attach_match_logos(embed, match)


def match_started_embed(match: dict) -> discord.Embed:
    embed = _base(
        "🟢 Mecz właśnie się zaczął",
        C_WIN,
        f"## PINDOLZ  ⚔️  {_opponent(match)}",
    )
    embed.add_field(name="🏷️ Dywizja", value=match.get("division") or "-", inline=True)
    embed.add_field(name="🎯 Format", value=f"Bo{match.get('bestOf') or '?'}", inline=True)
    _add_links(embed, match)
    return _attach_match_logos(embed, match)


def match_ended_embed(
    match: dict,
    form: str | None = None,
    standing: dict | None = None,
) -> discord.Embed:
    return result_embed(match, form=form, standing=standing)


def schedule_changed_embed(match: dict, old_date: str | None, old_time: str | None) -> discord.Embed:
    opponent = _opponent(match)
    old_t = (old_time or "")[:5] if old_time else "?"
    old_d = old_date or "nie ustalono terminu"
    embed = _base(
        "📅 Zmiana terminu meczu",
        C_UPCOMING,
        f"## PINDOLZ  ⚔️  {opponent}",
    )
    embed.add_field(name="Było", value=f"`{old_d} {old_t}`", inline=True)
    embed.add_field(name="Jest", value=f"{_ts(match, 'F')}\n{_ts(match, 'R')}", inline=True)
    embed.add_field(name="🏷️ Dywizja", value=match.get("division") or "-", inline=False)
    _add_links(embed, match)
    return embed


def standings_embed(
    table: list[dict],
    division: str | None = None,
    changes: dict | None = None,
) -> discord.Embed:
    division = division or DIVISION
    embed = _base(f"🏆 Tabela · {division}", C_TABLE)
    if not table:
        embed.description = "Brak danych tabeli."
        return embed
    changes = changes or {}
    lines = [f" {'#':>2} {'Drużyna':<14} {'W-L':>5} {'RD':>4} {'Pkt':>3}"]
    lines.append("─" * 33)
    for row in table[:16]:
        rank = row.get("rank") or "?"
        team = (row.get("team") or {}).get("name") or "???"
        pts = row.get("points")
        w = row.get("wins") or 0
        l = row.get("losses") or 0
        marker = "▶" if team.upper() == "PINDOLZ" else " "
        d = changes.get(team.upper(), 0)
        delta = f" ▲{min(d, 9)}" if d > 0 else f" ▼{min(abs(d), 9)}" if d < 0 else ""
        lines.append(
            f"{marker}{str(rank):>2} {team[:14]:<14} {f'{w}-{l}':>5} "
            f"{_signed(row.get('roundDifference')):>4} {pts if pts is not None else '–':>3}{delta}"
        )
    embed.description = "```\n" + "\n".join(lines) + "\n```"
    embed.set_footer(
        text="▶ PINDOLZ • RD = różnica rund" + (" • ▲▼ zmiana pozycji" if changes else "")
    )
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
            f"`{m.get('matchDate') or 'nie ustalono terminu'}` {_team_name(m, 'team1')} {_score_str(m)} {_team_name(m, 'team2')}"
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
    embed.set_footer(text="Ta wiadomość zniknie za 2 minuty")
    return embed


def rank_change_embed(old_rank: int, new_rank: int, points=None) -> discord.Embed:
    up = new_rank < old_rank
    if up:
        title, color, arrow, verb = "📈 PINDOLZ awansował w tabeli!", C_WIN, "▲", "awansował"
    else:
        title, color, arrow, verb = "📉 PINDOLZ spadł w tabeli", C_LOSS, "▼", "spadł"
    embed = _base(title, color, f"## PINDOLZ {verb} na **{new_rank}. miejsce** {arrow}")
    embed.add_field(name="Było", value=f"{old_rank}. miejsce", inline=True)
    embed.add_field(name="Jest", value=f"{_medal(new_rank)} {new_rank}. miejsce", inline=True)
    if points is not None:
        embed.add_field(name="Punkty", value=f"**{points}**", inline=True)
    _add_links(embed)
    return embed


def poll_embed(info: dict, votes: dict, closed: bool = False) -> discord.Embed:
    ts = info.get("ts")
    when = f"<t:{ts}:F> · <t:{ts}:R>" if ts else "—"
    embed = _base(
        "🗳️ Ankieta: kto może grać?",
        C_NEUTRAL if closed else C_UPCOMING,
        f"## PINDOLZ  ⚔️  {info.get('opp') or '???'}\n🕒 {when}",
    )
    groups: dict[str, list[str]] = {"yes": [], "no": [], "maybe": []}
    for uid, vote in votes.items():
        if vote in groups:
            groups[vote].append(uid)
    labels = {"yes": "✅ Mogę grać", "no": "❌ Nie mogę", "maybe": "❔ Może"}
    for key in ("yes", "no", "maybe"):
        ids = groups[key]
        value = "\n".join(f"<@{u}>" for u in ids[:20]) or "—"
        if len(ids) > 20:
            value += f"\n… i {len(ids) - 20} więcej"
        embed.add_field(name=f"{labels[key]} ({len(ids)})", value=value, inline=True)
    if info.get("div"):
        embed.add_field(name="🏷️ Dywizja", value=info["div"], inline=True)
    if info.get("bo"):
        embed.add_field(name="🎯 Format", value=f"Bo{info['bo']}", inline=True)
    embed.set_footer(text="Ankieta zamknięta" if closed else "Kliknij ponownie ten sam przycisk, aby cofnąć głos")
    return embed


def _player_line(uid: int, nicks: dict[int, str] | None) -> str:
    nick = (nicks or {}).get(uid)
    return f"<@{uid}> · `{nick}`" if nick else f"<@{uid}>"


def players_embed(nicks: dict[int, str]) -> discord.Embed:
    embed = _base("🎮 Powiązani gracze", C_TEAM)
    if not nicks:
        embed.description = "Brak powiązań. Właściciel serwera może je dodać komendą `/polacz`."
        return embed
    items = list(nicks.items())
    lines = [f"<@{uid}> · `{nick}`" for uid, nick in items[:40]]
    if len(items) > 40:
        lines.append(f"… i {len(items) - 40} więcej")
    embed.description = "\n".join(lines)
    embed.set_footer(text=f"{FOOTER} • {len(items)} powiązań")
    return embed


def lineup_embed(match: dict, ids: list[int], nicks: dict[int, str] | None = None) -> discord.Embed:
    embed = _base(
        "👥 Skład na mecz",
        C_TEAM,
        f"## PINDOLZ  ⚔️  {_opponent(match)}\n🕒 {_ts(match, 'F')} · {_ts(match, 'R')}",
    )
    if ids:
        embed.add_field(
            name=f"Gracze ({len(ids)})",
            value="\n".join(f"{i}. {_player_line(u, nicks)}" for i, u in enumerate(ids, 1)),
            inline=False,
        )
    else:
        embed.add_field(name="Skład", value="Brak (skład wyczyszczony)", inline=False)
    _add_links(embed, match)
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
            "`/tabela` · tabela dywizji\n"
            "`/gracze` · powiązani gracze\n"
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
            "`/setup-all` · wszystkie kanały naraz\n"
            "`/setup-ankiety` · kanał ankiet dostępności\n"
            "`/ankieta-role` · role pingowane w ankiecie\n"
            "`/ustawienia` · włączanie i wyłączanie funkcji\n"
            "`/pokaz-embedy` · podgląd wszystkich kart\n"
            "`/sklad` · skład na najbliższy mecz\n"
            "`/polacz` · powiąż osobę z nickiem gracza\n"
            "`/gif-dodaj` · GIF-y po wygranej (też `/gif-lista`, `/gif-usun`)"
        ),
        inline=False,
    )
    embed.add_field(
        name="🤖 Automatycznie",
        value=(
            "⏰ przypomnienie 1 h i 30 min przed meczem\n"
            "🔴 LIVE co 5–10 s + przycisk kanału\n"
            "📅 zmiana terminu meczu\n"
            "🏳️ wynik walkowerem (osobny styl)\n"
            "💬 krótki komentarz pod wynikiem\n"
            "📆 wydarzenie serwera Discord dla najbliższego meczu\n"
            "👏 przycisk „GG” pod wynikiem\n"
            "🎞️ losowy GIF po wygranej\n"
            "🆕 powiadomienie o nowej wersji bota (DM)\n"
            "🏆 tabela: 08:00, 18:00, 20:00, 21:30, 23:00\n"
            "🗓️ podsumowanie tygodnia (niedziela 20:00)\n"
            "🗳️ ankieta „Kto może grać?” gdy termin jest ustalony\n"
            "🔔 przycisk „Przypomnij mi” pod kartą meczu (DM)\n"
            "🧵 wątek z relacją LIVE\n"
            "📈 awans lub spadek w tabeli\n"
            "🚨 alert o awarii API (DM do właściciela)"
        ),
        inline=False,
    )
    return embed
