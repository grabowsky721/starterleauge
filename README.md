> **Wersja bota: `1.4.0`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** co **5 s** podczas meczu / **10 s** gdy nie gra
- Przycisk **Kanał LIVE** pod startem meczu
- Tabela dywizji (kanał o stałych godzinach)
- Przypomnienia przed meczem (30 min / 1 h)
- Ankiety dostępności, skład, powiązania graczy
- GIF po wygranej, reakcje, status bota
- Soft-start tasków (stopniowe uruchamianie)
- SQLite – pamięć wiadomości po restarcie

---

## Komendy

| Komenda | Opis |
|---------|------|
| `/pindolz` | Najbliższe i ostatnie mecze |
| `/live` | Czy gra teraz |
| `/wyniki` | Ostatnie wyniki |
| `/nadchodzace` | Nadchodzące mecze |
| `/tabela` | Tabela dywizji |
| `/pomoc` | Lista komend |
| `/wersja` | Wersja bota |
| `/status` | Status API i kanałów |
| `/setup-all` | Ustaw wszystkie kanały |
| `/setup` | Kanał główny |
| `/setup-live` | Kanał LIVE |
| `/setup-tabela` | Kanał tabeli |
| `/setup-ankiety` | Kanał ankiet |
| `/ankieta-role` | Role do pingu ankiet |
| `/ustawienia` | Włącz/wyłącz funkcje |
| `/pokaz-embedy` | Podgląd kart |
| `/sklad` | Skład na mecz |
| `/polacz` | Powiąż gracza z nickiem |
| `/gracze` | Lista powiązań |
| `/gif-dodaj` | Dodaj GIF po wygranej |
| `/gif-lista` | Lista GIF-ów |
| `/gif-usun` | Usuń GIF |

---

## Uruchomienie (GameHost)

1. Repo: `https://github.com/grabowsky721/starterleauge`
2. Entry: `src/bot.py`
3. Auto Update: `1`
4. Sekrety: `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN`
5. Restart serwera

Po starcie w logu szukaj `[sync] ... komend` oraz soft-start tasków.

---

## Soft-start (kolejność)

| Czas od ready | Task |
|---------------|------|
| 20 s | LIVE |
| 35 s | Prematch |
| 45 s | Tabela |
| 60 s | Daily |
| 80 s | Cleanup |
| 100 s | Status |
| 120 s | Ankiety |
| 140 s | API watch |
| 160 s | Eventy |
| 180 s | Sync komend |
| 200 s | Update GitHub |
| 220 s | Weekly (koniec) |

---

## Wymagania

```
discord.py>=2.3.2
requests>=2.31.0
python-dotenv>=1.0.0
```
