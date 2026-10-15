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
- **`/trening`** – ankieta terminu treningu z auto-zamknięciem
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
| **Kapitan** | `/kapitan` (właściciel) | skład, panel, polacz, ping, ankiety, trening, `/vicekapitan` |
| **Vicekapitan** | `/vicekapitan` (właściciel/kapitan) | jak kapitan, bez ustawiania vice |

Komendy sztabu: `/sklad` · `/panel` · `/polacz` · `/ping-sklad` · `/sklad-status` · `/ankieta-role` · `/trening`

---

## Komendy (skrót)

**Wszyscy:** `/pindolz` `/live` `/wyniki` `/nadchodzace` `/tabela` `/status` `/wersja` `/pomoc` `/gracze` `/moj-status` `/sztab`  
**Sztab:** `/sklad` `/panel` `/polacz` `/ping-sklad` `/sklad-status` `/ankieta-role` `/trening` `/vicekapitan`  
**Właściciel:** `/setup*` `/ustawienia` `/gif-*` `/pokaz-embedy` `/kapitan`

### `/sklad` – wiele składów
1. Wybierz graczy  
2. **Zapisz jako…** → nazwa (Główny, Rezerwa…)  
3. Wczytaj z listy  
4. **Zapisz na mecz** / **Zapisz + DM**

### `/trening`
Ankieta terminu (2–4 opcje), auto-zamknięcie po 1–72 h, wynik na kanale.

---

## Harmonogram

| Co | Kiedy |
|----|-------|
| LIVE | 5 s / 10 s |
| Prematch | co 1 min |
| Daily | co 10 min |
| Tabela | 08:00, 18:00, 20:00, 21:30, 23:00 |
| Weekly | niedziela 20:00 |
| Cleanup | 04:00 |
| Update GitHub | co 1 h |

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

## Zależności

```
discord.py>=2.3.2
requests>=2.31.0
python-dotenv>=1.0.0
```

Team ID: **869**. Wersja: zgodne `VERSION` + README + `/wersja`.
