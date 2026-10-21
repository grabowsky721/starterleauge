> **Wersja bota: `1.7.3`** · plik [`VERSION`](VERSION) · komenda `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID **869**) w [StarterLeague](https://starterleague.pl).

Przy każdej zmianie kodu aktualizuj **`VERSION`** i linię wersji na górze tego pliku.

---

## Struktura projektu

```
VERSION
README.md
requirements.txt
.env.example          # opcjonalnie
src/
  bot.py              # główny bot
  client.py           # StarterLeague Partner API
  db.py               # SQLite
  embeds.py           # karty Discord + loga drużyn
```

---

## Sekrety (GameHost / zmienne środowiskowe)

| Zmienna | Wymagane | Opis |
|---------|----------|------|
| `DISCORD_BOT_TOKEN` | tak | Token bota Discord |
| `CLOUDFLARE_ACCOUNT_ID` | nie | do grafik meczów (Workers AI) |
| `CLOUDFLARE_API_TOKEN` | nie | do grafik meczów |

---

## Uruchomienie na GameHost

1. Podłącz repo: `https://github.com/grabowsky721/starterleauge`
2. Branch: `main`
3. Start command: `python -m src.bot` lub `python src/bot.py` (zależnie od hosta)
4. Ustaw zmienne środowiskowe
5. Auto Update / Pull on restart – włączone

Bot soft-startuje zadania (kolejne taski z opóźnieniem), żeby nie przeciążyć API przy restarcie.

---

## Komendy (skrót)

- `/setup` – konfiguracja kanałów (owner)
- `/sklad` – potwierdzenie składu + role + DM
- `/zbiorka` – zbiórka
- `/trening` – ankiety treningowe → wydarzenia
- `/wersja` – aktualna wersja
- panel kapitana / vice

Pełna lista w `/help` (jeśli dostępne).

---

## Changelog (najnowsze)

### 1.7.3
- Naprawa `@tasks.loop` + `@guarded` na `prematch_check` (AttributeError: before_loop)
- Zachowanie cache tabeli/upcoming przy błędzie API
- Soft-start i throttling bez zmian funkcjonalnych

### 1.7.2
- Poprzednie poprawki
