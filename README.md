> **Wersja bota: `1.5.12`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz, wyniki, LIVE, soft-start ~90 s
- Sztab: kapitan, vice, **coach** (`/coach`)
- **`/zaplanuj`** + **`/zaplanuj-lista`**
- `/trening`, MVP, ciche godziny, tygodniówka DM kapitana
- Panele UI, wiele składów, linki do meczów

### 1.5.12
Sync slash-komend: najpierw global, potem **`copy_global_to` na serwer** – komendy (m.in. `/zaplanuj`, `/coach`) pojawiają się od razu, bez czekania na propagację Discorda.

### 1.5.11
`/coach`, poprawka `/zaplanuj`, `/zaplanuj-lista`

---

## Komendy (skrót)

**Wszyscy:** `/pindolz` `/live` `/wyniki` `/nadchodzace` `/tabela` `/status` `/wersja` `/pomoc` `/gracze` `/moj-status` `/sztab`  
**Sztab:** `/sklad` `/panel` `/polacz` `/ping-sklad` `/sklad-status` `/ankieta-role` `/trening` `/zaplanuj` `/zaplanuj-lista`  
**Kapitan+:** `/vicekapitan` `/coach`  
**Właściciel:** `/setup*` `/ustawienia` `/gif-*` `/kapitan`

`/zaplanuj` – `data:` YYYY-MM-DD · `godzina:` HH:MM · `tresc:` · opcjonalnie kanał i rola

---

## GameHost

| Pole | Wartość |
|------|---------|
| Git Repo | `https://github.com/grabowsky721/starterleauge` |
| Bot py file | `src/bot.py` |
| Auto Update | `1` |

Sekrety: `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN`

Team ID: **869**.
