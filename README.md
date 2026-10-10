# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (StarterLeague).

## Funkcje

**Komendy:**
- `/pindolz` – najbliższe + ostatnie mecze
- `/live` – czy grają teraz
- `/wyniki` – ostatnie wyniki
- `/nadchodzace` – tylko przyszłe mecze
- `/tabela` – tabela Starter Division 6
- `/setup` – kanał główny (właściciel)
- `/setup-live` – kanał live (właściciel)

**Automat:**
- 09:00 i 20:00 (Europe/Warsaw) – nowe wyniki + nadchodzące (24–48h)
- LIVE co **10 sekund** – start / wynik mapy / koniec (edycja tej samej wiadomości)
- SQLite – pamięta ID wiadomości po restarcie
- Cleanup starych rekordów po 30 dniach

## Secrets

```env
DISCORD_BOT_TOKEN=
STARTERLEAGUE_API_TOKEN=
OWNER_ID=          # opcjonalne; bez tego działa właściciel serwera
```

## Uruchomienie

```bash
pip install -r requirements.txt
python -m src.bot
```

Potem na Discordzie:
1. `/setup #kanał-główny`
2. `/setup-live #kanał-live`
