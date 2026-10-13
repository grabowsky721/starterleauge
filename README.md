> **Wersja bota: `1.4.7`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** co **5 s** podczas meczu / **10 s** gdy nie gra
- Soft-start tasków + wiadomość startowa z postępem
- Sync slash-komend **od razu przy starcie**
- `/sklad` – skład + **DM z potwierdzeniem** (Gram / Nie mogę) + raport do kapitana
- Komendy w **DM**: `/panel`, `/sklad-status`, `/ping-sklad`, `/moj-status`, `/pomoc`
- Tabela, prematch, ankiety, GIF po wygranej, powiązania graczy
- SQLite – stan po restarcie

---

## Komendy (skrót)

**Wszyscy:** `/pindolz` `/live` `/wyniki` `/nadchodzace` `/tabela` `/status` `/wersja` `/pomoc` `/gracze` `/moj-status`  
**Właściciel:** `/setup*` `/sklad` `/polacz` `/ustawienia` `/gif-*` `/panel` `/sklad-status` `/ping-sklad`  

Szczegóły: `/pomoc` (na serwerze lub w DM).

---

## GameHost

| Pole | Wartość |
|------|---------|
| Git Repo | `https://github.com/grabowsky721/starterleauge` |
| Branch | `main` |
| Auto Update | `1` |
| Bot py file | `src/bot.py` |
| Requirements | `requirements.txt` |

Sekrety: `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN`.

---

## Wersja

Zawsze zgodne: `VERSION` + pierwsza linia README + `/wersja`.
