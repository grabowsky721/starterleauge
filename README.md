> **Wersja bota: `1.4.4`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** co **5 s** podczas meczu / **10 s** gdy nie gra
- Przycisk **Kanał LIVE** pod startem meczu + opcjonalny wątek LIVE
- Automatyczna tabela dywizji (+ strzałki zmian pozycji)
- Forma ostatnich meczów i pozycja w tabeli przy wyniku
- Przypomnienia **30 min** i **1 h** przed meczem
- Powiadomienie o **zmianie terminu** meczu
- Osobny styl przy wyniku **walkowerem**
- Podsumowanie tygodnia (**niedziela 20:00**)
- Przycisk **Odśwież** przy tabeli i wynikach
- Reakcje pod wynikami (🎉 / 😢) oraz przycisk **GG**
- **GIF po wygranej** (lista linków: `/gif-dodaj`)
- Powiązania graczy z nickami (`/polacz`, `/gracze`)
- Skład na najbliższy mecz (`/sklad`)
- Ankiety dostępności + role do pingu
- Wydarzenia Discord na mecz
- Alert o awarii API (DM)
- Powiadomienie o nowej wersji z GitHuba
- Wiadomość po restarcie – **znika po 10 min**
- Soft-start tasków (~**3 min 40 s**) – mniej skoku CPU/RAM
- Sync slash-komend na serwer (natychmiastowe pojawianie się)
- Cache API + backoff przy błędach LIVE
- SQLite – stan i ID wiadomości po restarcie
- Przełączniki funkcji w `/ustawienia` (13 opcji)

---

## Komendy

| Komenda | Opis | Kto |
|---------|------|-----|
| `/pindolz` | Najbliższe + ostatnie mecze | wszyscy |
| `/live` | Czy PINDOLZ gra teraz | wszyscy |
| `/wyniki` | Ostatnie wyniki (+ Odśwież) | wszyscy |
| `/nadchodzace` | Tylko przyszłe mecze | wszyscy |
| `/tabela` | Tabela dywizji (+ Odśwież) | wszyscy |
| `/status` | API, kanały, uptime, taski | wszyscy |
| `/wersja` | Wersja bota i uptime | wszyscy |
| `/pomoc` | Lista komend i automatów | wszyscy |
| `/gracze` | Lista powiązań gracz ↔ nick | wszyscy |
| `/setup` | Kanał główny (wyniki + nadchodzące) | właściciel |
| `/setup-live` | Kanał LIVE | właściciel |
| `/setup-tabela` | Kanał tabeli | właściciel |
| `/setup-ankiety` | Kanał ankiet dostępności | właściciel |
| `/setup-all` | Wszystkie kanały naraz | właściciel |
| `/ankieta-role` | Role pingowane przy ankiecie | właściciel |
| `/ustawienia` | Włącz / wyłącz funkcje bota | właściciel |
| `/pokaz-embedy` | Podgląd wszystkich kart (test) | właściciel |
| `/sklad` | Skład na najbliższy mecz | właściciel |
| `/polacz` | Powiąż osobę z nickiem w lidze | właściciel |
| `/gif-dodaj` | Dodaj GIF/obrazek po wygranej | właściciel |
| `/gif-lista` | Lista GIF-ów | właściciel |
| `/gif-usun` | Usuń GIF z listy | właściciel |

---

## Soft-start (od `ready`)

| Czas | Co się uruchamia |
|------|------------------|
| **0 s** | Login, SQLite, widoki przycisków |
| **20 s** | LIVE |
| **35 s** | Prematch (przypomnienia) |
| **45 s** | Tabela |
| **60 s** | Daily (wyniki / nadchodzące) |
| **80 s** | Cleanup SQLite |
| **100 s** | Status bota |
| **120 s** | Ankiety |
| **140 s** | API watch |
| **160 s** | Eventy Discord |
| **180 s** | **Sync komend** (slash) |
| **200 s** | Update GitHub |
| **220 s** | Weekly summary – koniec |

---

## Harmonogram (Europe/Warsaw)

| Co | Kiedy | Kanał |
|----|-------|-------|
| LIVE | **5 s** (mecz) / **10 s** (brak) | live |
| Status bota | co **30 s** | – |
| API watch | co **60 s** | – |
| Prematch | co **1 min** (okno 30 min / 1 h) | główny |
| Daily | co **10 min** | główny |
| Ankiety / eventy | co **5 min** | ankiety / – |
| Update GitHub | co **6 h** | główny |
| Tabela dywizji | **08:00, 18:00, 20:00, 21:30, 23:00** | tabela |
| Weekly | **niedziela 20:00** | główny |
| Cleanup | **04:00** | – |

Bot **edytuje** istniejące wiadomości zamiast wysyłać nowe.

---

## Wymagania

- Python **3.10+**
- `discord.py>=2.3.2`
- `requests>=2.31.0`
- `python-dotenv>=1.0.0`

---

## Instalacja

### 1. Bot Discord

1. [Discord Developer Portal](https://discord.com/developers/applications) → New Application
2. Bot → **Reset Token** → skopiuj token
3. **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Permissions: Send Messages, Embed Links, Add Reactions, Read Message History, Use Application Commands, Manage Messages (opcjonalnie)
4. Zaproś bota na serwer

### 2. Token StarterLeague

1. https://starterleague.pl/api-partnerskie
2. Zaakceptuj regulamin
3. Skopiuj token `slp_...`

### 3. Zmienne środowiskowe

```env
DISCORD_BOT_TOKEN=twoj_token_bota
STARTERLEAGUE_API_TOKEN=slp_twoj_token
```

Opcjonalnie: `DISCORD_GUILD_ID=id_serwera` (szybszy sync komend na jeden serwer).

### 4. Uruchomienie lokalne

```bash
git clone https://github.com/grabowsky721/starterleauge.git
cd starterleauge
pip install -r requirements.txt
python src/bot.py
```

### 5. GameHost / panel Discord Bot

| Pole | Wartość |
|------|---------|
| Git Repo Address | `https://github.com/grabowsky721/starterleauge` |
| Git Branch | `main` |
| Auto Update | `1` |
| Bot py file | **`src/bot.py`** |
| Requirements file | `requirements.txt` |
| User Uploaded Files | `0` |

Repo publiczne – **Git Username / Token nie są potrzebne**.

Tokeny ustaw w **Environment / Secrets** panelu (nie w kodzie ani w Gicie).

Po zapisie **zrestartuj serwer**. Auto Update przy restarcie ściąga `main`.

### 6. Konfiguracja na Discordzie

Jako **właściciel serwera**:

```
/setup-all #kanał-wyniki #kanał-live #kanał-tabela
```

albo osobno: `/setup`, `/setup-live`, `/setup-tabela`, `/setup-ankiety`.

Sprawdzenie: `/status`, `/wersja`, `/pomoc`.

W logu po starcie szukaj `[sync] ... komend` oraz linii `[start] ...` soft-startu.

---

## Struktura projektu

```
├── VERSION              # numer wersji (czytany przez /wersja)
├── .env.example
├── requirements.txt
├── README.md
└── src/
    ├── bot.py           # bot, komendy, taski, soft-start
    ├── client.py        # Partner API + cache
    ├── db.py            # SQLite (mecze, config, ID wiadomości)
    ├── embeds.py        # wygląd embedów
    └── main.py          # opcjonalny CLI
```

Dane (SQLite + config) → katalog `data/` (tworzy się sam).

---

## Uwagi

- Tokenów **nie** trzymaj w repozytorium ani w kodzie JS po stronie przeglądarki.
- Filtr meczów PINDOLZ jest po stronie klienta (team id **869**).
- Nieznane pola JSON z API są ignorowane (stabilność przy zmianach kontraktu).
- **Wersja:** zawsze trzymaj zgodne `VERSION` + pierwsza linia README + `/wersja`.
