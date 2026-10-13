> **Wersja bota: `1.5.4`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** co **5 s** podczas meczu / **10 s** gdy nie gra
- Soft-start (4 fazy) + wiadomość startowa z postępem
- Komendy slash od **60 s** (UI 1 po drugiej, potem sync)
- **Panele z interfejsem** (selecty, przyciski, modale)
- **`/sklad`** – panel składu, **wiele nazwanych składów**, zapis na mecz, DM Gram/Nie mogę
- Komendy w **DM**: `/panel`, `/sklad-status`, `/ping-sklad`, `/moj-status`, `/pomoc`
- Tabela, prematch, ankiety, GIF, powiązania nicków
- Update wersji z GitHuba **co 1 h**
- SQLite, cache API, `/ustawienia`

---

## Komendy

### Wszyscy

| Komenda | Opis |
|---------|------|
| `/pindolz` `/live` `/wyniki` `/nadchodzace` `/tabela` | Mecze i tabela |
| `/status` `/wersja` `/pomoc` `/gracze` | Info |
| `/moj-status` | Status w składzie (też DM) |

### Właściciel (część z UI)

| Komenda | Interfejs |
|---------|-----------|
| `/sklad` | Select graczy, zapis na mecz, **Zapisz jako…** (wiele składów), DM |
| `/setup-all` | Wybór 3 kanałów + Zapisz |
| `/polacz` | Osoba + modal nicku |
| `/ankieta-role` | Select ról |
| `/gif-lista` | Lista + usuwanie |
| `/panel` | Odśwież / status składu / ping |
| `/ustawienia` | Przyciski funkcji |
| `/setup` `/setup-live` `/setup-tabela` `/setup-ankiety` | Pojedyncze kanały |
| `/gif-dodaj` `/gif-usun` `/pokaz-embedy` | Pozostałe |
| `/sklad-status` `/ping-sklad` | Skład (też DM) |

---

## Skład – wiele zapisów

1. `/sklad` → wybierz graczy  
2. **Zapisz jako…** → nazwa (np. Główny, Rezerwa)  
3. Lista rozwijana → wczytaj skład  
4. **Zapisz na mecz** / **Zapisz + DM** → na najbliższy mecz  

Presety są w SQLite i przeżywają restart.

---

## Soft-start

| Czas | Co |
|------|-----|
| 15 s | LIVE |
| 30 s | Prematch |
| 45 s | Daily |
| 60 s | Komendy (UI) + sync |
| ~75 s+ | Tabela, status, ankiety, API, eventy |
| ~150 s+ | Cleanup, update, weekly |

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

---

## Zależności

```
discord.py>=2.3.2
requests>=2.31.0
python-dotenv>=1.0.0
```

Team ID: **869**. Wersja: zgodne `VERSION` + README + `/wersja`.
