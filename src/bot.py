"""Pełny bot (ed57ad1) + wolniejszy soft-start (~3 min) + sync komend na serwery."""
import os
import urllib.request

URL = (
    "https://raw.githubusercontent.com/grabowsky721/starterleauge/"
    "ed57ad1bfd9730312f1b329db5d78e37076be66b/src/bot.py"
)

REPLACEMENTS = [
    ("START_DELAY_LIVE = 15", "START_DELAY_LIVE = 30"),
    ("START_DELAY_PREMATCH = 30", "START_DELAY_PREMATCH = 60"),
    ("START_DELAY_TABLE = 45", "START_DELAY_TABLE = 90"),
    ("START_DELAY_DAILY = 60", "START_DELAY_DAILY = 120"),
    ("START_DELAY_WEEKLY = 75", "START_DELAY_WEEKLY = 150"),
    ("START_DELAY_CLEANUP = 90", "START_DELAY_CLEANUP = 180"),
    (
        'print("[start] soft-start tasków (~1 min 30 s)...")',
        'print("[start] soft-start tasków (~3 min)...")',
    ),
    (
        'print("Bot gotowy – taski wystartują stopniowo (~1 min 30 s).")',
        'print("Bot gotowy – taski wystartują stopniowo (~3 min).")',
    ),
]

OLD_SETUP = (
    "    async def setup_hook(self):\n"
    "        self.add_view(RefreshTabelaView())\n"
    "        self.add_view(RefreshWynikiView())\n"
    "        try:\n"
    "            self.add_dynamic_items(RemindButton, PollButton, GGButton)\n"
    "        except Exception as e:\n"
    "            print(f\"[start] dynamic items: {e}\")\n"
    "        await self.tree.sync()\n"
    "        asyncio.create_task(self._soft_start_tasks())\n"
)

NEW_SETUP = (
    "    async def setup_hook(self):\n"
    "        self.add_view(RefreshTabelaView())\n"
    "        self.add_view(RefreshWynikiView())\n"
    "        try:\n"
    "            self.add_dynamic_items(RemindButton, PollButton, GGButton)\n"
    "        except Exception as e:\n"
    "            print(f\"[start] dynamic items: {e}\")\n"
    "        try:\n"
    "            synced = await self.tree.sync()\n"
    "            print(f\"[sync] global: {len(synced)} komend\")\n"
    "        except Exception as e:\n"
    "            print(f\"[sync] blad: {e}\")\n"
    "        asyncio.create_task(self._soft_start_tasks())\n"
)

OLD_READY = (
    "async def on_ready():\n"
    "    print(f\"Zalogowano jako {bot.user} (ID: {bot.user.id})\")\n"
    "    print(f\"Wersja: {BOT_VERSION}\")\n"
    "    try:\n"
    "        embeds.AUTHOR_ICON = str(bot.user.display_avatar.url)\n"
    "    except Exception:\n"
    "        pass\n"
    "    print(\"Bot gotowy – taski wystartują stopniowo (~3 min).\")\n"
)

# on_ready still has old message until we replace delays first
OLD_READY_ORIG = (
    "async def on_ready():\n"
    "    print(f\"Zalogowano jako {bot.user} (ID: {bot.user.id})\")\n"
    "    print(f\"Wersja: {BOT_VERSION}\")\n"
    "    try:\n"
    "        embeds.AUTHOR_ICON = str(bot.user.display_avatar.url)\n"
    "    except Exception:\n"
    "        pass\n"
    "    print(\"Bot gotowy – taski wystartują stopniowo (~1 min 30 s).\")\n"
)

NEW_READY = (
    "async def on_ready():\n"
    "    print(f\"Zalogowano jako {bot.user} (ID: {bot.user.id})\")\n"
    "    print(f\"Wersja: {BOT_VERSION}\")\n"
    "    try:\n"
    "        embeds.AUTHOR_ICON = str(bot.user.display_avatar.url)\n"
    "    except Exception:\n"
    "        pass\n"
    "    try:\n"
    "        for guild in bot.guilds:\n"
    "            try:\n"
    "                synced = await bot.tree.sync(guild=guild)\n"
    "                print(f\"[sync] {guild.name}: {len(synced)} komend\")\n"
    "            except Exception as e:\n"
    "                print(f\"[sync] guild {guild.id}: {e}\")\n"
    "    except Exception as e:\n"
    "        print(f\"[sync] on_ready: {e}\")\n"
    "    print(\"Bot gotowy – taski wystartują stopniowo (~3 min).\")\n"
)

with urllib.request.urlopen(URL, timeout=45) as r:
    src = r.read().decode("utf-8")

if "class PindolzBot" not in src:
    raise SystemExit("Zrodlo bot.py uszkodzone")

for old, new in REPLACEMENTS:
    if old not in src:
        raise SystemExit(f"Brak fragmentu do podmiany: {old!r}")
    src = src.replace(old, new, 1)

if OLD_SETUP not in src:
    raise SystemExit("Brak setup_hook")
if OLD_READY_ORIG not in src and "taski wystartują stopniowo (~3 min)" not in src:
    # after REPLACEMENTS the ready message may already be ~3 min
    pass
src = src.replace(OLD_SETUP, NEW_SETUP, 1)

if OLD_READY_ORIG in src:
    src = src.replace(OLD_READY_ORIG, NEW_READY, 1)
elif OLD_READY in src:
    src = src.replace(OLD_READY, NEW_READY, 1)
else:
    # force inject guild sync before the ready print if structure drifted
    marker = 'print("Bot gotowy – taski wystartują stopniowo (~3 min).")'
    if marker in src and "for guild in bot.guilds" not in src:
        inject = (
            "    try:\n"
            "        for guild in bot.guilds:\n"
            "            try:\n"
            "                synced = await bot.tree.sync(guild=guild)\n"
            "                print(f\"[sync] {guild.name}: {len(synced)} komend\")\n"
            "            except Exception as e:\n"
            "                print(f\"[sync] guild {guild.id}: {e}\")\n"
            "    except Exception as e:\n"
            "        print(f\"[sync] on_ready: {e}\")\n"
            f"    {marker}\n"
        )
        src = src.replace(f"    {marker}\n", inject, 1)

ns = globals()
ns["__file__"] = os.path.abspath(__file__)
ns["__name__"] = __name__
exec(compile(src, ns["__file__"], "exec"), ns)
