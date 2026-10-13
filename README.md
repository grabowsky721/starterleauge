> **Wersja bota: `1.4.7`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** co **5 s** podczas meczu / **10 s** gdy nie gra
- Przycisk **Kanał LIVE** + opcjonalny wątek
- Tabela dywizji (+ zmiany pozycji) o stałych godzinach
- Przypomnienia **30 min** i **1 h** przed meczem
- Zmiana terminu, walkower, forma, reakcje, przycisk **GG**
- **`/sklad`** – skład na mecz + **DM do graczy** (Gram / Nie mogę) + raport do kapitana
- **Komendy w DM** – panel kapitana, status składu, ponowienie DM, status gracza
- GIF po wygranej, powiązania nicków (`/polacz`), ankiety, wydarzenia Discord
- Soft-start tasków + wiadomość startowa z postępem ładowania
- Sync slash-komend **od razu przy starcie** (global + serwer)
- Cache API, SQLite po restarcie, przełączniki w `/ustawienia`

---

## Komendy

### Wszyscy

| Komenda | Opis |
|---------|------|
| `/pindolz` | Najbliższe + ostatnie mecze |
| `/live` | Czy PINDOLZ gra teraz |
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
| `/setup-all` | Wszystkie kanały naraz |
| `/ankieta-role` | Role do pingu ankiet |
| `/ustawienia` | Włącz / wyłącz funkcje |
| `/pokaz-embedy` | Podgląd kart |
| `/sklad` | Skład + DM z prośbą o potwierdzenie |
| `/polacz` | Powiąż osobę z nickiem w lidze |
| `/gif-dodaj` / `/gif-lista` / `/gif-usun` | GIF-y po wygranej |
| `/panel` | Panel kapitana (wygodne w DM) |
| `/sklad-status` | Status potwierdzeń składu |
| `/ping-sklad` | Ponów DM do osób bez odpowiedzi |

---

## Komendy w DM

Napisz do bota prywatnie i użyj `/`:

| Komenda | Kto |
|---------|-----|
| `/panel` | właściciel |
| `/sklad-status` | właściciel |
| `/ping-sklad` | właściciel |
| `/moj-status` | każdy |
| `/pomoc` | każdy (lista pod DM) |

Bot może pisać pierwszy DM tylko do osób, które mogą otrzymywać PW (np. po wspólnym serwerze / otwartych wiadomościach).

---

## Soft-start (od `ready`)

| Czas | Co |
|------|-----|
| **0 s** | Login, SQLite, widoki, **sync komend** |
| **20 s** | LIVE |
| **35 s** | Prematch |
| **45 s** | Tabela |
| **60 s** | Daily |
| **80 s** | Cleanup |
| **100 s** | Status |
| **120 s** | Ankiety |
| **140 s** | API watch |
| **160 s** | Eventy |
| **180 s+** | Postęp komend w wiadomości startowej (UI) |
| **~200 s** | Update GitHub |
| **~220 s** | Weekly – koniec |

Wiadomość startowa pokazuje ✅ / 🔄 / ⏳ i znika po 10 min.

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
| Update GitHub | co 6 h |

---

## Instalacja (GameHost)

| Pole | Wartość |
|------|---------|
| Git Repo Address | `https://github.com/grabowsky721/starterleauge` |
| Git Branch | `main` |
| Auto Update | `1` |
| Bot py file | **`src/bot.py`** |
| Requirements file | `requirements.txt` |

**Sekrety:** `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN`

Po starcie w logu: `[sync] global: … komend` oraz `[sync] NazwaSerwera: …`.

Na Discordzie (właściciel):

```
/setup-all #wyniki #live #tabela
```

---

## Struktura

```
├── VERSION
├── requirements.txt
├── README.md
└── src/
    ├── bot.py
    ├── client.py
    ├── db.py
    ├── embeds.py
    └── main.py
```

Dane → katalog `data/` (SQLite).

---

## Zależności

```
discord.py>=2.3.2
requests>=2.31.0
python-dotenv>=1.0.0
```

---

## Uwagi

- Tokenów nie trzymaj w repozytorium.
- Team ID PINDOLZ: **869**.
- Wersja: zgodne `VERSION` + README + `/wersja`.
