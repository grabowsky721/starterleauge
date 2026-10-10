import os
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
OWNER_ID = int(os.getenv("OWNER_ID", "0") or "0")
TZ = ZoneInfo("Europe/Warsaw")


class PindolzBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.api = StarterLeagueClient()
        db.init_db()

    async def setup_hook(self):
        await self.tree.sync()
        self.daily_check.start()
        self.live_check.start()
        self.cleanup_task.start()

    def is_owner(self, interaction: discord.Interaction) -> bool:
        if OWNER_ID and interaction.user.id == OWNER_ID:
            return True
        if interaction.guild and interaction.user.id == interaction.guild.owner_id:
            return True
        return False

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
    ) -> tuple[int, int]:
        """Edytuj istniejącą wiadomość albo wyślij nową. Zwraca (message_id, channel_id)."""
        if msg_id and ch_id:
            try:
                ch = await self.get_channel_safe(ch_id) or channel
                msg = await ch.fetch_message(msg_id)
                await msg.edit(embed=embed)
                return msg.id, ch.id
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
        msg = await channel.send(embed=embed)
        return msg.id, channel.id  # type: ignore

    # ---------- DAILY: nadchodzące + wyniki ----------
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

        # --- wyniki ---
        for m in history:
            mid = m.get("id")
            if mid is None:
                continue
            row = db.get_match(mid)
            score = m.get("score") or {}
            if row and row.get("notified_result"):
                # ewentualna korekta wyniku
                old_s1, old_s2 = row.get("score_team1"), row.get("score_team2")
                new_s1, new_s2 = score.get("team1"), score.get("team2")
                if (old_s1, old_s2) != (new_s1, new_s2) and new_s1 is not None:
                    msg_id, ch_id = await self._edit_or_send(
                        channel,
                        embeds.result_embed(m),
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

            # nowy wynik
            msg_id, ch_id = await self._edit_or_send(
                channel, embeds.result_embed(m), None, None
            )
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

            # zaktualizuj też wiadomość LIVE jeśli była
            if row and row.get("msg_live_id"):
                try:
                    live_ch = await self.get_channel_safe(row.get("msg_live_ch"))
                    if live_ch:
                        await self._edit_or_send(
                            live_ch,
                            embeds.match_ended_embed(m),
                            row.get("msg_live_id"),
                            row.get("msg_live_ch"),
                        )
                except Exception:
                    pass

        # --- nadchodzące (24–48h) ---
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

            # tylko w oknie 48h
            if dt and not (now <= dt <= now + timedelta(hours=48)):
                continue

            row = db.get_match(mid)
            opponent = self._opponent(m)

            if row and row.get("notified_upcoming"):
                # zmiana terminu / przeciwnika?
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

            # nowe powiadomienie
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

    # ---------- LIVE co 10s ----------
    @tasks.loop(seconds=10)
    async def live_check(self):
        await self._run_live_check()

    @live_check.before_loop
    async def before_live(self):
        await self.wait_until_ready()

    async def _run_live_check(self):
        channel = await self.get_channel_safe(self._live_channel_id())
        if not channel:
            return

        try:
            lives = self.api.get_pindolz_live()
        except Exception as e:
            print(f"[live] API error: {e}")
            return

        current_ids = set()

        for m in lives:
            mid = m.get("id")
            if mid is None:
                continue
            current_ids.add(mid)
            row = db.get_match(mid)
            key = self._score_key(m)

            if not row or not row.get("msg_live_id"):
                # start meczu – jedna wiadomość (live embed)
                emb = embeds.live_embed(m)
                emb.title = "PINDOLZ gra teraz!"
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

            # aktualizacja tylko przy zmianie
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

        # zakończone – zniknęły z live
        known_live = db.get_live_matches()
        for row in known_live:
            mid = row["match_id"]
            if mid in current_ids:
                continue

            # spróbuj pobrać wynik z historii
            match_data = None
            try:
                history = self.api.get_pindolz_history()
                for h in history:
                    if h.get("id") == mid:
                        match_data = h
                        break
            except Exception:
                pass

            if match_data:
                emb = embeds.match_ended_embed(match_data)
                score = match_data.get("score") or {}
                await self._edit_or_send(
                    channel,
                    emb,
                    row.get("msg_live_id"),
                    row.get("msg_live_ch"),
                )
                # wynik na kanał główny jeśli jeszcze nie
                if not row.get("notified_result"):
                    main_ch = await self.get_channel_safe(self._main_channel_id())
                    if main_ch:
                        msg_id, ch_id = await self._edit_or_send(
                            main_ch, embeds.result_embed(match_data), None, None
                        )
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

    # ---------- cleanup raz dziennie ----------
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
    await interaction.followup.send(embed=embeds.history_embed(history))


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
    await interaction.followup.send(embed=embeds.standings_embed(table))


@bot.tree.command(name="setup", description="Ustaw kanał główny (wyniki + nadchodzące)")
@app_commands.describe(kanal="Kanał na wyniki i nadchodzące mecze")
async def cmd_setup(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel może to użyć.", ephemeral=True)
        return
    db.set_config("main_channel_id", str(kanal.id))
    await interaction.response.send_message(
        f"Kanał główny ustawiony na {kanal.mention}", ephemeral=True
    )


@bot.tree.command(name="setup-live", description="Ustaw kanał LIVE")
@app_commands.describe(kanal="Kanał na powiadomienia live")
async def cmd_setup_live(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not bot.is_owner(interaction):
        await interaction.response.send_message("Tylko właściciel może to użyć.", ephemeral=True)
        return
    db.set_config("live_channel_id", str(kanal.id))
    await interaction.response.send_message(
        f"Kanał live ustawiony na {kanal.mention}", ephemeral=True
    )


@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    print("Bot gotowy.")


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("Brak DISCORD_BOT_TOKEN")
    bot.run(TOKEN)
