"""Boot: pełny bot z commita 1.3.7 + natychmiastowy sync komend na serwery."""
import os
import urllib.request

FULL_BOT_URL = (
    "https://raw.githubusercontent.com/grabowsky721/starterleauge/"
    "ed57ad1bfd9730312f1b329db5d78e37076be66b/src/bot.py"
)

OLD_SETUP = '''    async def setup_hook(self):
        self.add_view(RefreshTabelaView())
        self.add_view(RefreshWynikiView())
        try:
            self.add_dynamic_items(RemindButton, PollButton, GGButton)
        except Exception as e:
            print(f"[start] dynamic items: {e}")
        await self.tree.sync()
        asyncio.create_task(self._soft_start_tasks())
'''

NEW_SETUP = '''    async def setup_hook(self):
        self.add_view(RefreshTabelaView())
        self.add_view(RefreshWynikiView())
        try:
            self.add_dynamic_items(RemindButton, PollButton, GGButton)
        except Exception as e:
            print(f"[start] dynamic items: {e}")
        try:
            guild_ids_env = os.getenv("DISCORD_GUILD_ID", "").strip()
            if guild_ids_env:
                for part in guild_ids_env.replace(";", ",").split(","):
                    part = part.strip()
                    if part.isdigit():
                        g = discord.Object(id=int(part))
                        synced = await self.tree.sync(guild=g)
                        print(f"[sync] guild {g.id}: {len(synced)} komend")
            synced = await self.tree.sync()
            print(f"[sync] global: {len(synced)} komend -> {[c.name for c in synced]}")
        except Exception as e:
            print(f"[sync] BŁĄD rejestracji komend: {e}")
        asyncio.create_task(self._soft_start_tasks())
'''

OLD_READY = '''async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    print(f"Wersja: {BOT_VERSION}")
    try:
        embeds.AUTHOR_ICON = str(bot.user.display_avatar.url)
    except Exception:
        pass
    print("Bot gotowy – taski wystartują stopniowo (~1 min 30 s).")
'''

NEW_READY = '''async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    print(f"Wersja: {BOT_VERSION}")
    try:
        embeds.AUTHOR_ICON = str(bot.user.display_avatar.url)
    except Exception:
        pass
    try:
        for guild in bot.guilds:
            try:
                synced = await bot.tree.sync(guild=guild)
                print(f"[sync] {guild.name} ({guild.id}): {len(synced)} komend")
            except Exception as e:
                print(f"[sync] blad guild {guild.id}: {e}")
    except Exception as e:
        print(f"[sync] on_ready: {e}")
    print("Bot gotowy – taski wystartują stopniowo (~1 min 30 s).")
'''

try:
    with urllib.request.urlopen(FULL_BOT_URL, timeout=45) as resp:
        src = resp.read().decode("utf-8")
except Exception as e:
    raise SystemExit(f"Nie udalo sie pobrac bot.py: {e}\nURL: {FULL_BOT_URL}") from e

if "class PindolzBot" not in src or "bot.run" not in src:
    raise SystemExit("Pobrany bot.py wyglada na uszkodzony.")

if OLD_SETUP not in src:
    raise SystemExit("Nie znaleziono setup_hook do podmiany – zla wersja zrodla.")
if OLD_READY not in src:
    raise SystemExit("Nie znaleziono on_ready do podmiany – zla wersja zrodla.")

src = src.replace(OLD_SETUP, NEW_SETUP, 1).replace(OLD_READY, NEW_READY, 1)

_ns = globals()
_ns["__file__"] = os.path.abspath(__file__)
_ns["__name__"] = __name__
exec(compile(src, _ns["__file__"], "exec"), _ns)
