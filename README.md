> **Wersja bota: `1.5.0`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** co **5 s** podczas meczu / **10 s** gdy nie gra
- Soft-start w 4 fazach + wiadomość startowa (✅ / 🔄 / ⏳)
- Komendy slash: od **60 s** po starcie, w UI **1 po drugiej** (co 2 s), potem pełny sync
- **`/sklad`** – skład + DM Gram/Nie mogę + raport do kapitana
- Komendy w **DM**: `/panel`, `/sklad-status`, `/ping-sklad`, `/moj-status`, `/pomoc`
- Tabela dywizji, prematch 30 min / 1 h, ankiety, GIF po wygranej, `/polacz`
- Nowa wersja z GitHuba sprawdzana **co 1 h**
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
| `/moj-status` | Czy jesteś w składzie i co odpisałeś |

### Właściciel serwera

| Komenda | Opis |
|---------|------|
| `/setup` | Kanał główny |
| `/setup-live` | Kanał LIVE |
| `/setup-tabela` | Kanał tabeli |
| `/setup-ankiety` | Kanał ankiet |
| `/setup-all` | Wszystkie kanały |
| `/ankieta-role` | Role do ankiet |
| `/ustawienia` | Włącz / wyłącz funkcje |
| `/pokaz-embedy` | Podgląd kart |
| `/sklad` | Skład + DM potwierdzeń |
| `/polacz` | Nick w lidze |
| `/gif-dodaj` `/gif-lista` `/gif-usun` | GIF po wygranej |
| `/panel` | Panel kapitana (też DM) |
| `/sklad-status` | Status potwierdzeń składu |
| `/ping-sklad` | Ponów DM bez odpowiedzi |

---

## Soft-start (od `ready`)

| Czas | Co |
|------|-----|
| **15 s** | LIVE |
| **30 s** | Prematch |
| **45 s** | Daily |
| **60 s** | Komendy 1 po drugiej (UI) + **sync** |
| **~75 s+** | Tabela → Status → Ankiety → API → Eventy |
| **~150 s+** | Cleanup → Update GitHub → Weekly |

---

## Harmonogram (Europe/Warsaw)

| Co | Kiedy |
|----|-------|
| LIVE | 5 s (mecz) / 10 s (brak) |
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
| Git Repo Address | `https://github.com/grabowsky721/starterleauge` |
| Git Branch | `main` |
| Auto Update | `1` |
| Bot py file | **`src/bot.py`** |
| Requirements file | `requirements.txt` |

**Sekrety:** `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN`

Po starcie w logu: `[start] komenda /…`, potem `[sync] global: … komend`.

---

## Zależności

```
discord.py>=2.3.2
requests>=2.31.0
python-dotenv>=1.0.0
```

Team ID: **869**. Wersja: zgodne `VERSION` + README + `/wersja`.
