# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (StarterLeague).

## Funkcje

**Komendy:**
- `/pindolz` – najbliższe + ostatnie mecze
- `/live` – czy grają teraz
- `/wyniki` – ostatnie wyniki
- `/nadchodzące` – tylko przyszłe mecze
- `/setup` – ustawia kanał główny (tylko właściciel)
- `/setup-live` – ustawia kanał live (tylko właściciel)

**Automat:**
- 2× dziennie (09:00 i 20:00 Europe/Warsaw) sprawdza wyniki i nadchodzące → pisze na kanał główny
- Gdy jest mecz live → sprawdza co ~75 sekund
  - start meczu → wiadomość na kanał live
  - zmiana wyniku → aktualizacja wiadomości
  - koniec meczu → finalny wynik

## Secrets / zmienne środowiskowe

```env
DISCORD_BOT_TOKEN=
STARTERLEAGUE_API_TOKEN=
OWNER_ID=
```

## Instalacja na hostingu Discord Bot

1. Wgraj kod
2. Ustaw zmienne środowiskowe (tokeny + swoje User ID)
3. Zainstaluj zależności: `pip install -r requirements.txt`
4. Uruchom: `python -m src.bot`

## Uprawnienia bota

Bot potrzebuje:
- Send Messages
- Embed Links
- Use Application Commands
- Read Message History (opcjonalnie)
