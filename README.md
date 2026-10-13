> **Wersja bota: `1.4.10`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** co **5 s** podczas meczu / **10 s** gdy nie gra
- Soft-start w 4 fazach (~3 min) + wiadomość startowa z postępem
- Sync slash-komend **60 s** po starcie
- **`/sklad`** – skład + DM (Gram / Nie mogę) + raport do kapitana
- Komendy w **DM**: `/panel`, `/sklad-status`, `/ping-sklad`, `/moj-status`, `/pomoc`
- Tabela, prematch, ankiety, GIF, powiązania graczy
- Sprawdzanie nowej wersji na GitHubie **co 1 h**
- Cache API, SQLite, `/ustawienia`

---

## Komendy

### Wszyscy

| Komenda | Opis |
|---------|------|
| `/pindolz` | Najbliższe + ostatnie mecze |
| `/live` | Czy gra teraz |
| `/wyniki` | Ostatnie wyniki |
| `/nadchodzace` | Przyszłe mecze |
| `/tabela` | Tabela dywizji |
| `/status` | API, kanały, uptime |
| `/wersja` | Wersja bota |
| `/pomoc` | Lista komend (inna treść w DM) |
| `/gracze` | Powiązania Discord ↔ nick |
| `/moj-status` | Status w składzie |

### Właściciel

| Komenda | Opis |
|---------|------|
| `/setup` `/setup-live` `/setup-tabela` `/setup-ankiety` `/setup-all` | Kanały |
| `/ankieta-role` `/ustawienia` `/pokaz-embedy` | Konfiguracja |
| `/sklad` | Skład + DM potwierdzeń |
| `/polacz` | Nick w lidze |
| `/gif-dodaj` `/gif-lista` `/gif-usun` | GIF po wygranej |
| `/panel` `/sklad-status` `/ping-sklad` | Panel kapitana (też DM) |

---

## Soft-start (od `ready`)

| Czas | Co |
|------|-----|
| **15 s** | LIVE |
| **30 s** | Prematch |
| **45 s** | Daily |
| **60 s** | **Sync komend** |
| **75 s** | Tabela |
| **90 s** | Status |
| **105 s** | Ankiety |
| **120 s** | API watch |
| **135 s** | Eventy |
| **150 s** | Cleanup |
| **165 s** | Update GitHub (task start) |
| **180 s** | Weekly – koniec |

Potem update wersji z GitHuba **co 1 godzinę**.

---

## Harmonogram

| Co | Kiedy |
|----|-------|
| LIVE | 5 s / 10 s |
| Prematch | co 1 min |
| Daily | co 10 min |
| Tabela | 08:00, 18:00, 20:00, 21:30, 23:00 |
| Weekly | niedziela 20:00 |
| Cleanup | 04:00 |
| Update GitHub | **co 1 h** |

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
