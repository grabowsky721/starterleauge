"""Pełny kod bota (commit ed57ad1) + sync komend na serwery."""
import os
import urllib.request

URL = (
    "https://raw.githubusercontent.com/grabowsky721/starterleauge/"
    "ed57ad1bfd9730312f1b329db5d78e37076be66b/src/bot.py"
)

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
    "    print(\"Bot gotowy – taski wystartują stopniowo (~1 min 30 s).\")\n"
)

with urllib.request.urlopen(URL, timeout=45) as r:
    src = r.read().decode("utf-8")

if "class PindolzBot" not in src:
    raise SystemExit("Zrodlo bot.py uszkodzone")

if OLD_SETUP not in src or OLD_READY not in src:
    raise SystemExit("Nie pasuje wersja zrodla do patcha")

src = src.replace(OLD_SETUP, NEW_SETUP, 1).replace(OLD_READY, NEW_READY, 1)

ns = globals()
ns["__file__"] = os.path.abspath(__file__)
ns["__name__"] = __name__
exec(compile(src, ns["__file__"], "exec"), ns)
