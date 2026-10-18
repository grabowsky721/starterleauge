> **Wersja bota: `1.6.13`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

---

## Struktura repo

```
.env.example
README.md
VERSION
requirements.txt
src/
  __init__.py
  bot.py          # start GameHost: src/bot.py
  client.py       # StarterLeague API
  db.py           # SQLite
  embeds.py       # karty Discord
```

## GameHost

| Pole | Wartość |
|------|---------|
| Bot py file | `src/bot.py` |
| Requirements | `requirements.txt` |
| Auto Update | `1` |

Sekrety: `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN`

Team ID: **869**.
