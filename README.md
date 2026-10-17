> **Wersja bota: `1.6.1`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** (5 s / 10 s) + lock przebiegów
- Soft-start **~90 s**, sync slash na guild od razu
- **Sztab**: kapitan, vice, coach
- **`/trening`**: dni → godziny → wydarzenie + ocena 1–5
- Ankiety → kanał ankiet · ogłoszenia treningów → kanał ogłoszeń
- **Szablony ogłoszeń** · rola **aktywnego składu**
- `/zaplanuj`, MVP, ciche godziny, panele UI

### 1.6.1
- Fix `/setup-all` (ChannelSelect + przycisk Zapisz – konflikt wiersza Discord UI)
- Fix brak `_close_training_poll` po restarcie

### 1.6.0
Wersja zbiorcza po cyklu 1.5.x

---

## Kanały

| Komenda | Kanał |
|---------|--------|
| `/setup` | Główny |
| `/setup-live` | LIVE |
| `/setup-tabela` | Tabela |
| `/setup-ankiety` | Ankiety + ocena treningu |
| `/setup-ogloszenia` | Ogłoszenia treningów |
| `/setup-rola-sklad` | Rola składu na mecz |
| `/setup-all` | Panel wszystkich kanałów |

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
