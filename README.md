> **Wersja bota: `1.6.3`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** (5 s / 10 s) + lock przebiegów
- Soft-start **~35 s** – sync komend od razu (bez kolejki 1/39)
- Wiadomość startowa **usuwa się po 2 min**
- **Sztab**: kapitan, vice, coach
- **`/trening`**: dni → godziny → wydarzenie + ocena 1–5
- Ankiety → kanał ankiet · ogłoszenia treningów → kanał ogłoszeń
- Szablony ogłoszeń · rola aktywnego składu
- `/zaplanuj`, MVP, ciche godziny, panele UI

### 1.6.3
Soft-start ~35 s, bez sekwencyjnego ładowania komend, usuwanie wiadomości startu po 2 min.

### 1.6.1
Fix `/setup-all` (wiersze UI) + `_close_training_poll`.

### 1.6.0
Wersja zbiorcza po cyklu 1.5.x

---

## Soft-start (~35 s)

| s | Co |
|---|-----|
| 2–6 | LIVE, prematch, daily |
| 8 | Sync komend (global + guild) |
| 12–26 | Tabela, status, poll, API, eventy |
| 28–35 | Cleanup, update, weekly |

---

## Kanały

| Komenda | Kanał |
|---------|--------|
| `/setup` | Główny |
| `/setup-live` | LIVE |
| `/setup-tabela` | Tabela |
| `/setup-ankiety` | Ankiety |
| `/setup-ogloszenia` | Ogłoszenia treningów |
| `/setup-rola-sklad` | Rola składu |
| `/setup-all` | Panel kanałów |

---

## GameHost

| Pole | Wartość |
|------|---------|
| Git Repo | `https://github.com/grabowsky721/starterleauge` |
| Branch | `main` |
| Auto Update | `1` |
| Bot py file | `src/bot.py` |
| Requirements | `requirements.txt` |

Sekrety: `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN`

Team ID: **869**.
