> **Wersja bota: `1.7.8`** · plik [`VERSION`](VERSION) · komenda `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID **869**) w [StarterLeague](https://starterleague.pl).

Przy każdej zmianie kodu aktualizuj **`VERSION`** i linię wersji na górze tego pliku.

---

## Co nowego w 1.7.8

- Przywrócone **grafiki AI** (Cloudflare Workers AI / FLUX): zapowiedź meczu + wynik
- Env: `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` (opcjonalne)

### Wcześniej (1.7.4–1.7.7)
- **AREDL**: `/setup-aredl` (kanał + ping roli), `/aredl`, `/aredl nick:…`
- Alert o nowym zatwierdzonym recordzie klanu Pdlz (~12 min)
- Naprawa `get_form` / `daily_check` (`multiple values for limit`)
- Usunięte VC (poza zakresem funkcji)
- GIF-y osobno po wygranej i przegranej

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
- Zbiórka: DM do składu (Gram / Nie mogę)
- Ping roli aktywnego składu

### Grafiki AI (Cloudflare Workers AI)
- Opcjonalne plakaty: zapowiedź meczu + wynik (FLUX.1-schnell)

### AREDL (Geometry Dash)
- `/setup-aredl` — kanał alertów + ping roli
- `/aredl` — klan Pdlz · `/aredl nick:` — profil gracza
- Alert przy nowym zatwierdzonym recordzie klanu

### GIF-y
- Osobne listy po **wygranej** i **przegranej** (`/gif-dodaj` z typem)

### Skład / sztab / trening
- `/sklad`, rola aktywnego składu, kapitan / vice / coach
- `/trening`, ogłoszenia, szablony, `/zaplanuj`

---

## Komendy (skrót)

`/pindolz` · `/live` · `/wyniki` · `/nadchodzace` · `/tabela` · `/sklad` · `/panel` · `/aredl` · `/setup-aredl` · `/ustawienia` · `/wersja` · `/status` · `/pomoc`
