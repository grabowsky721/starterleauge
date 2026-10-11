import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot_defs import *  # noqa: F401,F403

bot = PindolzBot()


@bot.tree.command(name="pindolz", description="Najbliższe i ostatnie mecze PINDOLZ")
async def cmd_pindolz(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        upcoming = bot.api.get_pindolz_upcoming()
        history = bot.api.get_pindolz_history()
    except Exception as e:
        await interaction.followup.send(f"Błąd API: {e}")
        return
    await interaction.followup.send(embeds=[embeds.upcoming_embed(upcoming), embeds.history_embed(history)])


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
    await interaction.followup.send(embed=embeds.history_embed(history), view=refresh_view("wyniki"))


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
        view=refresh_view("tabela"),
    )


@bot.tree.command(name="pomoc", description="Lista komend i automatów bota")
async def cmd_pomoc(interaction: discord.Interaction):
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
    main_id = bot._main_channel_id()
    live_id = bot._live_channel_id()
    table_id = bot._table_channel_id()

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
    emb.add_field(
        name="Kanały",
        value="\n".join([ch_line("Główny", main_id), ch_line("LIVE", live_id), ch_line("Tabela", table_id)]),
        inline=False,
    )
    await interaction.followup.send(embed=emb, ephemeral=True)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("Brak DISCORD_BOT_TOKEN")
    bot.run(TOKEN)
