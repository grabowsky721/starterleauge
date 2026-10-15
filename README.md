> **Wersja bota: `1.5.8`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** co **5 s** (mecz) / **10 s** (brak)
- Soft-start **~90 s** + wiadomość startowa z postępem
- Komendy w trakcie soft-startu (UI, potem sync)
- **Panele UI**: `/sklad`, `/setup-all`, `/polacz`, `/ankieta-role`, `/gif-lista`, `/panel`, `/ustawienia`
- **Wiele nazwanych składów** + zapis na mecz + DM Gram/Nie mogę
- **Sztab**: kapitan i vicekapitan (`/kapitan`, `/vicekapitan`, `/sztab`)
- **`/trening`** – ankieta terminu z auto-zamknięciem
- Link do meczu na StarterLeague w embedach
- Komendy w **DM**: `/panel`, `/sklad-status`, `/ping-sklad`, `/moj-status`, `/pomoc`
- Tabela, prematch, ankiety, GIF, powiązania nicków
- Update wersji z GitHuba **co 1 h**
- SQLite, cache API, `/ustawienia`

---

## Soft-start (~90 s)

| Czas | Co |
|------|-----|
| 4 s | LIVE |
| 8 s | Prematch |
| 12 s | Daily |
| 16 s | Komendy + sync |
| 20–60 s | Tabela, status, ankiety, API, eventy |
| 70–90 s | Cleanup, update GitHub, weekly |

---

## Sztab (uprawnienia)

| Rola | Kto ustawia | Uprawnienia |
|------|-------------|-------------|
| **Właściciel serwera** | — | wszystko (setup, ustawienia, GIF, `/kapitan`) |
| **Kapitan** | `/kapitan` (właściciel) | skład, panel, polacz, ping, ankiety, `/vicekapitan`, `/trening` |
| **Vicekapitan** | `/vicekapitan` (właściciel/kapitan) | jak kapitan, bez ustawiania vice |

---

## GameHost

| Pole | Wartość |
|------|---------|
| Git Repo | `https://github.com/grabowsky721/starterleauge` |
| Branch | `main` |
| Auto Update | `1` |
| Bot py file | `src/bot.py` |
| Requirements | `requirements.txt` |

Sekrety: `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN`

---

Team ID: **869**. Wersja: zgodne `VERSION` + README + `/wersja`.
