> **Wersja bota: `1.6.16`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów **PINDOLZ** (ID 869).

## Logo drużyn (1.6.16)

Źródło: publiczne API `GET https://starterleague.pl/api/teams/{id}` → pole **`avatar`** (np. `uploads/….png`).

W embedzie: logo PINDOLZ (autor) + logo przeciwnika (miniatura). Cache 6 h.

## Struktura

`src/bot.py` · `client.py` · `db.py` · `embeds.py`

Sekrety: `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN` · Team **869**.
