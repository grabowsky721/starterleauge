> **Wersja bota: `1.6.20`** · plik [`VERSION`](VERSION) · komenda `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID **869**) w [StarterLeague](https://starterleague.pl).

Przy każdej zmianie kodu aktualizuj **`VERSION`** i linię wersji na górze tego pliku.

---

## Struktura projektu

```
VERSION
README.md
requirements.txt
.env.example          # opcjonalnie
src/
  bot.py              # główny bot
  client.py           # StarterLeague Partner API
  db.py               # SQLite
  embeds.py           # karty Discord + loga drużyn
```

---

## Sekrety (GameHost / zmienne środowiskowe)

| Zmienna | Wymagane | Opis |
|---------|----------|------|
| `DISCORD_BOT_TOKEN` | tak | Token bota Discord |
| `STARTERLEAGUE_API_TOKEN` | tak | Token Partner API (`slp_…`) |
| `CLOUDFLARE_ACCOUNT_ID` | nie | Grafiki AI (Workers AI) |
| `CLOUDFLARE_API_TOKEN` | nie | Grafiki AI (Workers AI) |

**Cloudflare (opcjonalnie):** [Workers AI → REST API](https://dash.cloudflare.com/?to=/:account/ai/workers-ai)  
Bez CF bot działa normalnie — tylko bez automatycznych grafik.

**Nie commituj tokenów do repozytorium.**

---

## GameHost

| Pole | Wartość |
|------|--------|
| Git Repo | `https://github.com/grabowsky721/starterleauge` |
| Branch | `main` |
| Auto Update | `1` |
| Bot py file | `src/bot.py` |
| Requirements | `requirements.txt` |

Python 3.10+.

---

## Główne funkcje

### Mecze i liga
- Terminarz, wyniki, LIVE — **edycja** wiadomości zamiast spamu
- LIVE co kilka sekund w trakcie meczu
- Tabela dywizji (harmonogram: m.in. 08:00, 18:00, 20:00, 21:30, 23:00)
- Forma i pozycja przy wyniku, walkower, zmiana terminu
- Loga drużyn w embedach (`/api/teams/{id}` → `avatar`)
- Link do meczu na StarterLeague

### Prematch / zbiórka
- Przypomnienia **60 / 30 / 10 min** + **~24 h** przed meczem
- Zbiórka: DM do składu (Gram / Nie mogę), lista braków do kapitana (+ zastępca)
- Ping roli aktywnego składu

### Grafiki AI (Cloudflare Workers AI)
- **~24 h przed meczem** — zapowiedź (kanał główny)
- **Po wyniku** — grafika na kanał **LIVE**
- Model: `@cf/black-forest-labs/flux-1-schnell` (darmowy limit dzienny)

### Skład i sztab
- `/sklad` — składy, zapis, DM potwierdzeń
- Rola aktywnego składu po zapisie
- Kapitan / vice / coach / zastępstwo (DM zbiórki)
- `/trening`, szablony ogłoszeń, `/zaplanuj`

### Inne
- Soft-start (~35–90 s) — łagodniejsze CPU/RAM
- SQLite — stan po restarcie
- `/ustawienia` — włączanie funkcji
- Nowa wersja na GitHubie → **DM tylko do właściciela serwera** (co 1 h)
- Alert awarii API (DM)

---

## Komendy (skrót)

| Komenda | Opis |
|---------|------|
| `/pindolz` `/live` `/wyniki` `/nadchodzace` `/tabela` | Mecze i tabela |
| `/status` `/wersja` `/pomoc` | Status bota |
| `/setup` `/setup-live` `/setup-tabela` `/setup-all` … | Kanały (właściciel) |
| `/sklad` `/polacz` `/gracze` `/panel` | Skład i gracze |
| `/kapitan` `/vicekapitan` `/coach` `/sztab` | Sztab |
| `/zastepstwo` `/zastepstwo-koniec` | Zastępca pod DM zbiórki |
| `/trening` `/ogloszenie` `/zaplanuj` | Organizacja |
| `/gif-dodaj` `/gif-lista` `/gif-usun` | GIF po wygranej |
| `/ustawienia` `/pokaz-embedy` | Konfiguracja |

Pełna lista: `/pomoc` na Discordzie.

---

## Sztab

| Rola | Ustawia | Uprawnienia |
|------|---------|-------------|
| Właściciel serwera | — | wszystko |
| Kapitan | `/kapitan` | skład, panel, trening, vice… |
| Vicekapitan | `/vicekapitan` | jak kapitan (bez ustawiania vice) |
| Zastępca | `/zastepstwo` | tylko DM o brakach przy zbiórce |

---

## API

- Baza: `https://starterleague.pl/api/partners`
- Auth: `Authorization: Bearer slp_…`
- Drużyna: **869** (PINDOLZ)
- Loga publiczne: `GET https://starterleague.pl/api/teams/{id}`

---

## Wymagania Python

```
discord.py>=2.4,<3
requests>=2.31,<3
python-dotenv>=1.0,<2
```

---

Team **869** · [starterleague.pl/team/869](https://starterleague.pl/team/869)
