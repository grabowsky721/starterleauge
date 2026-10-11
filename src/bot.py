import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot_class import *  # noqa: F401,F403

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


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("Brak DISCORD_BOT_TOKEN")
    bot.run(TOKEN)
