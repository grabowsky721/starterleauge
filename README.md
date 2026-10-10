# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** w lidze [StarterLeague](https://starterleague.pl).

- Terminarz i wyniki
- LIVE co 10 sekund (edycja tej samej wiadomości)
- Automatyczna tabela **Starter Division 6**
- SQLite – pamięta stan po restarcie

---

## Komendy

| Komenda | Opis | Kto |
|---------|------|-----|
| `/pindolz` | Najbliższe + ostatnie mecze | wszyscy |
| `/live` | Czy PINDOLZ gra teraz | wszyscy |
| `/wyniki` | Ostatnie wyniki | wszyscy |
| `/nadchodzace` | Tylko przyszłe mecze | wszyscy |
| `/tabela` | Tabela Starter Division 6 | wszyscy |
| `/setup` | Kanał główny (wyniki + nadchodzące) | właściciel serwera |
| `/setup-live` | Kanał LIVE | właściciel serwera |
| `/setup-tabela` | Kanał tabeli Division 6 | właściciel serwera |

---

## Automatyczne powiadomienia

| Co | Kiedy | Kanał |
|----|-------|-------|
| Nowe wyniki + nadchodzące (24–48h) | **09:00** i **20:00** | główny |
| LIVE – start / wynik mapy / koniec | co **10 sekund** | live |
| Tabela Division 6 | **08:00, 18:00, 20:00, 21:30, 23:00** | tabela |
| Cleanup starych rekordów | **04:00** | – |

Wszystkie godziny w strefie **Europe/Warsaw**.

Bot **edytuje** istniejące wiadomości zamiast spamować nowymi.

---

## Wymagania

- Python 3.10+
- Token bota Discord
- Token Partner API StarterLeague (`slp_...`)

---

## Instalacja

### 1. Discord Bot

1. https://discord.com/developers/applications → **New Application**
2. Zakładka **Bot** → **Reset Token** → skopiuj token
3. **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Permissions: Send Messages, Embed Links, Read Message History, Use Application Commands
4. Zaproś bota na serwer wygenerowanym linkiem

### 2. Token StarterLeague

1. Zaloguj się na https://starterleague.pl/api-partnerskie
2. Zaakceptuj regulamin
3. Skopiuj token zaczynający się od `slp_`

### 3. Hosting

Ustaw zmienne środowiskowe:

```env
DISCORD_BOT_TOKEN=twoj_token_bota
STARTERLEAGUE_API_TOKEN=slp_twoj_token
```

Sklonuj repo i uruchom:

```bash
git clone https://github.com/grabowsky721/starterleauge.git
cd starterleauge
pip install -r requirements.txt
python -m src.bot
```

Start command na panelu hostingu:

```
python -m src.bot
```

### 4. Konfiguracja na Discordzie

Po starcie bota (jako **właściciel serwera**):

```
/setup #kanał-wyniki
/setup-live #kanał-live
/setup-tabela #kanał-tabela
```

`/setup-tabela` od razu wysyła aktualną tabelę i od tej pory aktualizuje ją o wyznaczonych godzinach.

---

## Struktura projektu

```
├── .env.example
├── requirements.txt
├── README.md
└── src/
    ├── bot.py       # bot, komendy, schedulery
    ├── client.py    # Partner API StarterLeague
    ├── db.py        # SQLite (mecze, config, ID wiadomości)
    ├── embeds.py    # wygląd wiadomości
    └── main.py      # stary CLI (opcjonalny)
```

Dane (SQLite + config) zapisują się w katalogu `data/`.

---

## Zachowanie powiadomień

- **Nadchodzące** – tylko mecze w oknie 24–48h, jedno powiadomienie na mecz; przy zmianie terminu edytuje istniejącą wiadomość
- **Wyniki** – każdy wynik tylko raz; korekta wyniku = edycja wiadomości
- **LIVE** – jedna wiadomość na mecz; aktualizacja wyniku mapy przez edycję; po końcu ta sama wiadomość dostaje finalny wynik
- **Tabela** – jedna wiadomość na kanale, edytowana 5× dziennie
- Po restarcie bot odczytuje ID wiadomości z bazy i kontynuuje edycję

---

## Zależności

```
discord.py>=2.3.2
requests>=2.31.0
python-dotenv>=1.0.0
```
