# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** w lidze [StarterLeague](https://starterleague.pl).

## Funkcje

- Terminarz i wyniki (edycja zamiast spamu)
- LIVE co **10 sekund** – start / wynik mapy / koniec
- Automatyczna tabela **Starter Division 6** (+ zmiany pozycji)
- Forma ostatnich 5 meczów i pozycja w tabeli przy wyniku
- Przypomnienie **30 min** przed meczem
- Podsumowanie tygodnia (niedziela 20:00)
- Przycisk **Odśwież** przy tabeli i wynikach
- Reakcje pod wynikami (🎉 wygrana / 😢 porażka)
- SQLite – pamięta stan i ID wiadomości po restarcie

---

## Komendy

| Komenda | Opis | Kto |
|---------|------|-----|
| `/pindolz` | Najbliższe + ostatnie mecze | wszyscy |
| `/live` | Czy PINDOLZ gra teraz | wszyscy |
| `/wyniki` | Ostatnie wyniki (+ Odśwież) | wszyscy |
| `/nadchodzace` | Tylko przyszłe mecze | wszyscy |
| `/tabela` | Tabela Starter Division 6 (+ Odśwież) | wszyscy |
| `/setup` | Kanał główny (wyniki + nadchodzące) | właściciel serwera |
| `/setup-live` | Kanał LIVE | właściciel serwera |
| `/setup-tabela` | Kanał tabeli Division 6 | właściciel serwera |

---

## Harmonogram (Europe/Warsaw)

| Co | Kiedy | Kanał |
|----|-------|-------|
| Nowe wyniki + nadchodzące (24–48h) | **09:00**, **20:00** | główny |
| Przypomnienie przed meczem | **30 min** przed startem | główny |
| LIVE | co **10 s** | live |
| Tabela Division 6 | **08:00, 18:00, 20:00, 21:30, 23:00** | tabela |
| Podsumowanie tygodnia | **niedziela 20:00** | główny |
| Cleanup starych rekordów | **04:00** | – |

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
   - Permissions: Send Messages, Embed Links, Add Reactions, Read Message History, Use Application Commands
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
python -m src.bot
```

Albo:

```bash
python src/bot.py
```

(w `bot.py` jest poprawka `sys.path`, więc obie metody działają)

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

Tokeny bota ustaw w **Environment / Secrets** panelu (nie w parametrach startowych Gita).

Po zapisie **zrestartuj serwer**. Przy każdym restarcie Auto Update ściąga najnowszy kod z `main`.

### 6. Konfiguracja na Discordzie

Jako **właściciel serwera**:

```
/setup #kanał-wyniki
/setup-live #kanał-live
/setup-tabela #kanał-tabela
```

`/setup-tabela` od razu wysyła tabelę i od tej pory aktualizuje ją o wyznaczonych godzinach.

---

## Struktura projektu

```
├── .env.example
├── requirements.txt
├── README.md
└── src/
    ├── bot.py       # bot, komendy, schedulery, przyciski
    ├── client.py    # Partner API StarterLeague
    ├── db.py        # SQLite (mecze, config, ID wiadomości)
    ├── embeds.py    # wygląd embedów
    └── main.py      # stary CLI (opcjonalny)
```

Dane (SQLite + config) → katalog `data/`.

---

## Zależności

```
discord.py>=2.3.2
requests>=2.31.0
python-dotenv>=1.0.0
```
