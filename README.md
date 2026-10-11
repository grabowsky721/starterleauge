> **Wersja bota: `1.3.2`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** co **5 s** podczas meczu / **10 s** gdy nie gra
- Przycisk **Kanał LIVE** pod startem meczu
- Automatyczna tabela **Starter Division 6** (+ strzałki zmian pozycji)
- Forma ostatnich 5 meczów i pozycja w tabeli przy wyniku
- Przypomnienie **30 min** przed meczem
- Powiadomienie o **zmianie terminu** meczu
- Osobny styl przy wyniku **walkowerem**
- Podsumowanie tygodnia (**niedziela 20:00**)
- Przycisk **Odśwież** przy tabeli i wynikach
- Reakcje pod wynikami (🎉 / 😢)
- Link do profilu PINDOLZ na StarterLeague w embedach
- Wiadomość po restarcie (wersja + kanały) – **znika po 10 min**
- Soft-start tasków (~**1 min 30 s**) – mniej skoku CPU/RAM
- Cache API + backoff przy błędach LIVE
- SQLite – stan i ID wiadomości po restarcie

---

## Komendy

| Komenda | Opis | Kto |
|---------|------|-----|
| `/pindolz` | Najbliższe + ostatnie mecze | wszyscy |
| `/live` | Czy PINDOLZ gra teraz | wszyscy |
| `/wyniki` | Ostatnie wyniki (+ Odśwież) | wszyscy |
| `/nadchodzace` | Tylko przyszłe mecze | wszyscy |
| `/tabela` | Tabela Starter Division 6 (+ Odśwież) | wszyscy |
| `/status` | API, kanały, uptime, task LIVE | wszyscy |
| `/wersja` | Wersja bota i uptime | wszyscy |
| `/pomoc` | Lista komend i automatów | wszyscy |
| `/setup` | Kanał główny (wyniki + nadchodzące) | właściciel serwera |
| `/setup-live` | Kanał LIVE | właściciel serwera |
| `/setup-tabela` | Kanał tabeli Division 6 | właściciel serwera |
| `/setup-all` | Wszystkie trzy kanały naraz | właściciel serwera |

---

## Harmonogram (Europe/Warsaw)

| Co | Kiedy | Kanał |
|----|-------|-------|
| Nowe wyniki + nadchodzące (24–48 h) | **09:00**, **20:00** | główny |
| Przypomnienie przed meczem | **30 min** przed startem | główny |
| Zmiana terminu | przy wykryciu w daily | główny |
| LIVE | **5 s** (mecz) / **10 s** (brak) | live |
| Tabela Division 6 | **08:00, 18:00, 20:00, 21:30, 23:00** | tabela |
| Podsumowanie tygodnia | **niedziela 20:00** | główny |
| Cleanup starych rekordów | **04:00** | – |
| Soft-start tasków po starcie | do ~**90 s** | – |

Bot **edytuje** istniejące wiadomości zamiast wysyłać nowe.

---

## Wymagania

- Python **3.10+**
- Token bota Discord
- Token Partner API StarterLeague (`slp_...`)

---

## Instalacja

### 1. Discord Bot

1. https://discord.com/developers/applications → **New Application**
2. **Bot** → **Reset Token** → skopiuj token
3. **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Permissions: Send Messages, Embed Links, Add Reactions, Read Message History, Use Application Commands, Manage Messages (opcjonalnie – usuwanie wiadomości restart)
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

### 4. Uruchomienie lokalne

```bash
git clone https://github.com/grabowsky721/starterleauge.git
cd starterleauge
pip install -r requirements.txt
python src/bot.py
```

Albo: `python -m src.bot`

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

albo osobno:

```
/setup #kanał-wyniki
/setup-live #kanał-live
/setup-tabela #kanał-tabela
```

`/setup-tabela` / `/setup-all` od razu wysyła tabelę i aktualizuje ją o wyznaczonych godzinach.

Sprawdzenie: `/status`, `/wersja`, `/pomoc`.

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

## Zależności

```
discord.py>=2.3.2
requests>=2.31.0
python-dotenv>=1.0.0
```

---

## Uwagi

- Tokenów **nie** trzymaj w repozytorium ani w kodzie JS po stronie przeglądarki.
- Filtr meczów PINDOLZ jest po stronie klienta (team id **869**).
- Nieznane pola JSON z API są ignorowane (stabilność przy zmianach kontraktu).
- **Wersja:** zawsze trzymaj zgodne `VERSION` + pierwsza linia README + `/wersja`.
