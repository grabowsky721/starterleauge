> **Wersja bota: `1.6.15`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów **PINDOLZ** (ID 869) w [StarterLeague](https://starterleague.pl).

## Struktura

```
.env.example · README.md · VERSION · requirements.txt
src/bot.py · client.py · db.py · embeds.py
```

## 1.6.15

W embedach meczów (LIVE, wynik, prematch, start, nadchodzące):
- **logo PINDOLZ** przy autorze karty
- **logo przeciwnika** jako miniatura

Źródło: pola API drużyny albo strona `/team/{id}` (cache 6 h).

## GameHost

`src/bot.py` · sekrety: `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN`

Team **869**.
