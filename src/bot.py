import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

from src import db, embeds
from src.client import StarterLeagueClient, PINDOLZ_TEAM_ID

load_dotenv()

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


# ---------- Przycisk Odśwież ----------
class RefreshView(discord.ui.View):
    def __init__(self, kind: str):
        super().__init__(timeout=None)
        self.kind = kind  # "tabela" | "wyniki"
        self.refresh.custom_id = f"pindolz_refresh_{kind}"

    @discord.ui.button(label="Odśwież", style=discord.ButtonStyle.secondary, custom_id="pindolz_refresh")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            if self.kind == "tabela":
                table = bot.api.get_division6_table()
                emb = embeds.standings_embed(table, changes=bot._rank_changes(table))
            else:
                history = bot.api.get_pindolz_history()
                emb = embeds.history_embed(history)
            await interaction.message.edit(embed=emb, view=self)
            await interaction.followup.send("Odświeżono.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Błąd: {e}", ephemeral=True)


class PindolzBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.api = StarterLeagueClient()
        self._upcoming_cache: tuple[datetime, list] | None = None
        self.started_at = datetime.now(TZ)
        self._announced = False
        db.init_db()

    async def setup_hook(self):
        self.add_view(RefreshView("tabela"))
        self.add_view(RefreshView("wyniki"))
        await self.tree.sync()
        self.daily_check.start()
        self.prematch_check.start()
        self.live_check.start()
        self.table_update.start()
        self.weekly_summary.start()
        self.cleanup_task.start()

    def is_owner(self, interaction: discord.Interaction) -> bool:
        return bool(
            interaction.guild and interaction.user.id == interaction.guild.owner_id
        )

    async def get_channel_safe(self, channel_id: int | None):
        if not channel_id:
            return None
        try:
            return self.get_channel(channel_id) or await self.fetch_channel(channel_id)
        except Exception:
            return None

    def _main_channel_id(self) -> int | None:
        val = db.get_config("main_channel_id")
        return int(val) if val else None

    def _live_channel_id(self) -> int | None:
        val = db.get_config("live_channel_id")
        return int(val) if val else None

    def _table_channel_id(self) -> int | None:
        val = db.get_config("table_channel_id")
        return int(val) if val else None

    def _table_msg(self) -> tuple[int | None, int | None]:
        mid = db.get_config("msg_table_id")
        cid = db.get_config("msg_table_ch")
        return (int(mid) if mid else None, int(cid) if cid else None)

    def _result_extras(self, match: dict | None = None):
        form = None
        standing = None
        try:
            history = self.api.get_pindolz_history()
            form = self.api.get_form(history, limit=5)
        except Exception:
            pass
        try:
            standing = self.api.get_pindolz_standing()
        except Exception:
            pass
        return form, standing

    @staticmethod
    def _score_key(match: dict) -> str:
        current = match.get("currentMap") or {}
        score = current.get("score") or {}
        series = match.get("seriesScore") or {}
        return (
            f"{score.get('team1')}-{score.get('team2')}|"
            f"{series.get('team1')}-{series.get('team2')}|"
            f"{current.get('name')}"
        )

    @staticmethod
    def _opponent(match: dict) -> str:
        t1 = match.get("team1") or {}
        t2 = match.get("team2") or {}
        if t1.get("id") == PINDOLZ_TEAM_ID:
            return t2.get("name") or "???"
        return t1.get("name") or "???"

    async def _edit_or_send(
        self,
        channel: discord.abc.Messageable,
        embed: discord.Embed,
        msg_id: int | None,
        ch_id: int | None,
        view: discord.ui.View | None = None,
    ) -> tuple[int, int]:
        if msg_id and ch_id:
            try:
                ch = await self.get_channel_safe(ch_id) or channel
                msg = await ch.fetch_message(msg_id)
                await msg.edit(embed=embed, view=view)
                return msg.id, ch.id
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
        msg = await channel.send(embed=embed, view=view)
        return msg.id, channel.id  # type: ignore

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
        changes: dict[str, int] = {}
        for row in table:
            name = ((row.get("team") or {}).get("name") or "").upper()
            rank = row.get("rank")
            old = prev.get(name)
            if name and isinstance(rank, int) and isinstance(old, int):
                changes[name] = old - rank
        return changes

    async def _react_result(self, ch_id: int | None, msg_id: int | None, match: dict):
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

    # ---------- TABELA ----------
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
            table = self.api.get_division6_table()
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
        new_msg_id, new_ch_id = await self._edit_or_send(
            channel, emb, msg_id, ch_id, view=RefreshView("tabela")
        )
        db.set_config("msg_table_id", str(new_msg_id))
        db.set_config("msg_table_ch", str(new_ch_id))
        print(f"[table] zaktualizowano o {datetime.now(TZ).strftime('%H:%M')}")

    # ---------- DAILY ----------
    @tasks.loop(time=[time(9, 0, tzinfo=TZ), time(20, 0, tzinfo=TZ)])
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
            history = self.api.get_pindolz_history()
            upcoming = self.api.get_pindolz_upcoming()
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

        for m in history:
            mid = m.get("id")
            if mid is None:
                continue
            row = db.get_match(mid)
            score = m.get("score") or {}
            if row and row.get("notified_result"):
                old_s1, old_s2 = row.get("score_team1"), row.get("score_team2")
                new_s1, new_s2 = score.get("team1"), score.get("team2")
                if (old_s1, old_s2) != (new_s1, new_s2) and new_s1 is not None:
                    msg_id, ch_id = await self._edit_or_send(
                        channel,
                        embeds.result_embed(m, form=form, standing=standing),
                        row.get("msg_result_id"),
                        row.get("msg_result_ch"),
                    )
                    db.upsert_match(
                        mid,
                        score_team1=new_s1,
                        score_team2=new_s2,
                        winner_team_id=m.get("winnerTeamId"),
                        msg_result_id=msg_id,
                        msg_result_ch=ch_id,
                        status="finished",
                    )
                continue

            msg_id, ch_id = await self._edit_or_send(
                channel,
                embeds.result_embed(m, form=form, standing=standing),
                None,
                None,
            )
            await self._react_result(ch_id, msg_id, m)
            db.upsert_match(
                mid,
                match_date=m.get("matchDate"),
                match_time=m.get("matchTime"),
                division=m.get("division"),
                opponent=self._opponent(m),
                status="finished",
                score_team1=score.get("team1"),
                score_team2=score.get("team2"),
                winner_team_id=m.get("winnerTeamId"),
                finished_at=datetime.utcnow().isoformat(),
                notified_result=1,
                msg_result_id=msg_id,
                msg_result_ch=ch_id,
            )

            if row and row.get("msg_live_id"):
                try:
                    live_ch = await self.get_channel_safe(row.get("msg_live_ch"))
                    if live_ch:
                        await self._edit_or_send(
                            live_ch,
                            embeds.match_ended_embed(m, form=form, standing=standing),
                            row.get("msg_live_id"),
                            row.get("msg_live_ch"),
                        )
                except Exception:
                    pass

        for m in upcoming:
            mid = m.get("id")
            if mid is None:
                continue
            match_date = m.get("matchDate")
            match_time = (m.get("matchTime") or "00:00:00")[:8]
            try:
                dt = datetime.strptime(
                    f"{match_date} {match_time}", "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=TZ)
            except Exception:
                dt = None
            if dt and not (now <= dt <= now + timedelta(hours=48)):
                continue

            row = db.get_match(mid)
            opponent = self._opponent(m)

            if row and row.get("notified_upcoming"):
                changed = (
                    row.get("match_date") != m.get("matchDate")
                    or (row.get("match_time") or "")[:5] != (m.get("matchTime") or "")[:5]
                    or row.get("opponent") != opponent
                )
                if changed:
                    msg_id, ch_id = await self._edit_or_send(
                        channel,
                        embeds.single_upcoming_embed(m),
                        row.get("msg_upcoming_id"),
                        row.get("msg_upcoming_ch"),
                    )
                    db.upsert_match(
                        mid,
                        match_date=m.get("matchDate"),
                        match_time=m.get("matchTime"),
                        division=m.get("division"),
                        opponent=opponent,
                        msg_upcoming_id=msg_id,
                        msg_upcoming_ch=ch_id,
                    )
                continue

            msg_id, ch_id = await self._edit_or_send(
                channel, embeds.single_upcoming_embed(m), None, None
            )
            db.upsert_match(
                mid,
                match_date=m.get("matchDate"),
                match_time=m.get("matchTime"),
                division=m.get("division"),
                opponent=opponent,
                status="scheduled",
                notified_upcoming=1,
                msg_upcoming_id=msg_id,
                msg_upcoming_ch=ch_id,
            )

    # ---------- PRZYPOMNIENIE PRZED MECZEM ----------
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
        if not channel:
            return
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
            if not (timedelta(0) < delta <= timedelta(minutes=self.PREMATCH_MINUTES)):
                continue
            key = f"prematch_{mid}"
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
            try:
                await channel.send(
                    embed=embeds.prematch_embed(
                        m, form=form, standing=standing, opp_standing=opp_standing
                    )
                )
                print(f"[prematch] wysłano przypomnienie o meczu {mid}")
            except Exception as e:
                db.set_config(key, None)
                print(f"[prematch] send error: {e}")

    @prematch_check.before_loop
    async def before_prematch(self):
        await self.wait_until_ready()

    # ---------- LIVE (5s gdy gra, 10s gdy nie) ----------
    @tasks.loop(seconds=LIVE_INTERVAL_IDLE)
    async def live_check(self):
        await self._run_live_check()

    @live_check.before_loop
    async def before_live(self):
        await self.wait_until_ready()

    async def _run_live_check(self):
        channel = await self.get_channel_safe(self._live_channel_id())
        if not channel:
            self.live_check.change_interval(seconds=LIVE_INTERVAL_IDLE)
            return

        try:
            lives = self.api.get_pindolz_live()
        except Exception as e:
            print(f"[live] API error: {e}")
            self.live_check.change_interval(seconds=LIVE_INTERVAL_IDLE)
            return

        # dynamiczny interwał
        if lives:
            self.live_check.change_interval(seconds=LIVE_INTERVAL_ACTIVE)
        else:
            self.live_check.change_interval(seconds=LIVE_INTERVAL_IDLE)

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
                msg = await channel.send(embed=emb)
                db.upsert_match(
                    mid,
                    match_date=m.get("matchDate"),
                    match_time=m.get("matchTime"),
                    division=m.get("division"),
                    opponent=self._opponent(m),
                    status="live",
                    updated_at=m.get("updatedAt"),
                    live_score_key=key,
                    msg_live_id=msg.id,
                    msg_live_ch=channel.id,
                )
                continue

            if key != row.get("live_score_key") or m.get("updatedAt") != row.get("updated_at"):
                msg_id, ch_id = await self._edit_or_send(
                    channel,
                    embeds.live_embed(m),
                    row.get("msg_live_id"),
                    row.get("msg_live_ch"),
                )
                db.upsert_match(
                    mid,
                    status="live",
                    updated_at=m.get("updatedAt"),
                    live_score_key=key,
                    msg_live_id=msg_id,
                    msg_live_ch=ch_id,
                )

        known_live = db.get_live_matches()
        for row in known_live:
            mid = row["match_id"]
            if mid in current_ids:
                continue

            match_data = None
            history = []
            try:
                history = self.api.get_pindolz_history()
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
                await self._edit_or_send(
                    channel,
                    embeds.match_ended_embed(match_data, form=form, standing=standing),
                    row.get("msg_live_id"),
                    row.get("msg_live_ch"),
                )
                if not row.get("notified_result"):
                    main_ch = await self.get_channel_safe(self._main_channel_id())
                    if main_ch:
                        msg_id, ch_id = await self._edit_or_send(
                            main_ch,
                            embeds.result_embed(match_data, form=form, standing=standing),
                            None,
                            None,
                        )
                        await self._react_result(ch_id, msg_id, match_data)
                        db.upsert_match(
                            mid,
                            notified_result=1,
                            msg_result_id=msg_id,
                            msg_result_ch=ch_id,
                        )
                db.upsert_match(
                    mid,
                    status="finished",
                    score_team1=score.get("team1"),
                    score_team2=score.get("team2"),
                    winner_team_id=match_data.get("winnerTeamId"),
                    finished_at=datetime.utcnow().isoformat(),
                )
            else:
                db.mark_finished(mid)

    # ---------- Podsumowanie tygodnia (niedziela 20:00) ----------
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
        week_matches = []
        wins = losses = 0
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

        emb = embeds.weekly_summary_embed(week_matches, wins, losses, standing)
        await channel.send(embed=emb)
        print("[weekly] wysłano podsumowanie tygodnia")

    @weekly_summary.before_loop
    async def before_weekly(self):
        await self.wait_until_ready()

    # ---------- cleanup ----------
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
    await interaction.followup.send(
        embeds=[embeds.upcoming_embed(upcoming), embeds.history_embed(history)]
    )


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
    await interaction.followup.send(
        embed=embeds.history_embed(history), view=RefreshView("wyniki")
    )


@bot.tree.command(name="nadchodzace", description="Nadchodzące mecze PINDOLZ")
async def cmd_nadchodzace(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        upcoming = bot.api.get_pindolz_upcoming()
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    await interaction.followup.send(embed=embeds.upcoming_embed(upcoming))


@bot.tree.command(name="tabela", description="Tabela Starter Division 6")
async def cmd_tabela(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        table = bot.api.get_division6_table()
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    await interaction.followup.send(
        embed=embeds.standings_embed(table, changes=bot._rank_changes(table)),
        view=RefreshView("tabela"),
    )


@bot.tree.command(name="setup", description="Ustaw kanał główny (wyniki + nadchodzące)")
@app_commands.describe(kanal="Kanał na wyniki i nadchodzące mecze")
async def cmd_setup(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not bot.is_owner(interaction):
        await interaction.response.send_message(
            "Tylko właściciel serwera może to użyć.", ephemeral=True
        )
        return
    db.set_config("main_channel_id", str(kanal.id))
    await interaction.response.send_message(
        f"Kanał główny ustawiony na {kanal.mention}", ephemeral=True
    )


@bot.tree.command(name="setup-live", description="Ustaw kanał LIVE")
@app_commands.describe(kanal="Kanał na powiadomienia live")
async def cmd_setup_live(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not bot.is_owner(interaction):
        await interaction.response.send_message(
            "Tylko właściciel serwera może to użyć.", ephemeral=True
        )
        return
    db.set_config("live_channel_id", str(kanal.id))
    await interaction.response.send_message(
        f"Kanał live ustawiony na {kanal.mention}", ephemeral=True
    )


@bot.tree.command(name="setup-tabela", description="Ustaw kanał tabeli Division 6")
@app_commands.describe(kanal="Kanał na automatyczną tabelę")
async def cmd_setup_tabela(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not bot.is_owner(interaction):
        await interaction.response.send_message(
            "Tylko właściciel serwera może to użyć.", ephemeral=True
        )
        return
    db.set_config("table_channel_id", str(kanal.id))
    await interaction.response.defer(ephemeral=True)
    try:
        table = bot.api.get_division6_table()
        if table:
            emb = embeds.standings_embed(table, changes=bot._rank_changes(table))
            msg = await kanal.send(embed=emb, view=RefreshView("tabela"))
            db.set_config("msg_table_id", str(msg.id))
            db.set_config("msg_table_ch", str(kanal.id))
            await interaction.followup.send(
                f"Kanał tabeli ustawiony na {kanal.mention}\n"
                f"Tabela będzie aktualizowana o: **08:00, 18:00, 20:00, 21:30, 23:00**",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"Kanał ustawiony na {kanal.mention}, ale tabela jest pusta (API).",
                ephemeral=True,
            )
    except Exception as e:
        await interaction.followup.send(
            f"Kanał ustawiony, ale nie udało się pobrać tabeli: {e}",
            ephemeral=True,
        )


@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    print("Bot gotowy.")


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("Brak DISCORD_BOT_TOKEN")
    bot.run(TOKEN)
