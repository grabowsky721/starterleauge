import discord
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Warsaw")
PINDOLZ_ID = 869
TEAM_URL = "https://starterleague.pl/team/869"
FOOTER = "PINDOLZ • StarterLeague"
DIVISION = "Starter Division 6"
AUTHOR_ICON = None
C_WIN = 0x22C55E
C_LOSS = 0xEF4444
C_INFO = 0x3B82F6
C_UPCOMING = 0xF59E0B
C_NEUTRAL = 0x94A3B8
C_TABLE = 0x8B5CF6


def set_division(name):
    global DIVISION
    if name:
        DIVISION = name


def _base(title, color=C_INFO, desc=None):
    e = discord.Embed(title=title, color=color, description=desc, timestamp=datetime.now(TZ))
    e.set_footer(text=FOOTER)
    if AUTHOR_ICON:
        e.set_author(name="PINDOLZ", icon_url=AUTHOR_ICON, url=TEAM_URL)
    return e


def _match_dt(match):
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


def _team_name(match, side):
    t = match.get(side) or {}
    return (t.get("name") or "").strip() or "\u2014"


def _score_str(match):
    s = match.get("score") or {}
    a, b = s.get("team1"), s.get("team2")
    if a is None or b is None:
        return "\u2013:\u2013"
    return f"{a}:{b}"


def _is_walkover(match):
    return bool(match.get("walkover") or match.get("isWalkover"))


def _result(match):
    w = match.get("winnerTeamId")
    if w is None:
        return None
    return int(w) == PINDOLZ_ID


def live_embed(match):
    t1, t2 = _team_name(match, "team1"), _team_name(match, "team2")
    return _base("\U0001f534 LIVE", C_LOSS, f"**{t1}** vs **{t2}**")


def result_embed(match, form=None, standing=None):
    t1, t2 = _team_name(match, "team1"), _team_name(match, "team2")
    return _base("Wynik", C_WIN if _result(match) else C_LOSS, f"**{t1}** {_score_str(match)} **{t2}**")


def prematch_embed(match, form=None, standing=None, opp_standing=None, minutes=30, lineup=None, nicks=None):
    return _base(f"\u23f0 Mecz za ~{minutes} min", C_UPCOMING, f"vs **{_team_name(match, 'team2')}**")


def upcoming_embed(matches):
    e = _base("Nadchodz\u0105ce", C_UPCOMING)
    if not matches:
        e.description = "Brak mecz\u00f3w"
        return e
    for m in matches[:8]:
        e.add_field(
            name=_team_name(m, "team1") + " vs " + _team_name(m, "team2"),
            value=str(m.get("matchDate") or "nie ustalono terminu"),
            inline=False,
        )
    return e


def single_upcoming_embed(match):
    return _base(
        "Nadchodz\u0105cy mecz",
        C_UPCOMING,
        f"**{_team_name(match, 'team1')}** vs **{_team_name(match, 'team2')}**",
    )


def history_embed(matches):
    e = _base("Wyniki", C_INFO)
    for m in (matches or [])[:10]:
        e.add_field(
            name=_score_str(m),
            value=f"{_team_name(m, 'team1')} vs {_team_name(m, 'team2')}",
            inline=False,
        )
    return e


def standings_embed(table, changes=None):
    e = _base("Tabela", C_TABLE)
    lines = []
    for row in (table or [])[:15]:
        team = (row.get("team") or {}).get("name") or "?"
        lines.append(f"{row.get('rank', '?')}. {team}")
    e.description = "\n".join(lines) or "Brak danych"
    return e


def match_started_embed(match):
    return _base(
        "\U0001f7e2 Mecz startuje",
        C_WIN,
        f"**{_team_name(match, 'team1')}** vs **{_team_name(match, 'team2')}**",
    )


def match_ended_embed(match):
    return result_embed(match)


def schedule_changed_embed(match, old_date=None, old_time=None):
    return _base(
        "\U0001f4c5 Zmiana terminu",
        C_UPCOMING,
        f"**{_team_name(match, 'team1')}** vs **{_team_name(match, 'team2')}**",
    )


def rank_change_embed(old_rank, new_rank, points=None):
    return _base("\U0001f4c8 Tabela", C_INFO, f"Miejsce {old_rank} \u2192 {new_rank}")


def lineup_embed(match, ids, nicks=None):
    e = _base("Sk\u0142ad", C_INFO)
    e.description = ", ".join(f"<@{i}>" for i in ids) or "Pusty"
    return e


def players_embed(players):
    return _base("Gracze", C_INFO, "\n".join(str(p) for p in (players or [])[:20]) or "Brak")


def poll_embed(*a, **k):
    return _base("Ankieta", C_INFO)


def weekly_summary_embed(*a, **k):
    return _base("Tydzie\u0144", C_INFO)


def restart_embed(version, main_id=None, live_id=None, table_id=None):
    return _base(f"Bot online \u00b7 `{version}`", C_TABLE)


def help_embed():
    return _base("Pomoc", C_INFO, "Komendy slash \u2014 `/pomoc`")
