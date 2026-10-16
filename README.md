> **Wersja bota: `1.5.17`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** co **5 s** (mecz) / **10 s** (brak), bez nachodzących przebiegów (lock)
- Soft-start **~90 s** – błąd jednego kroku nie zatrzymuje reszty
- **Sync komend na serwer** (`copy_global_to`) – slash-e od razu widoczne
- **Sztab**: kapitan, vicekapitan, coach
- **`/trening`**: dni → godziny → wydarzenie Discord + ogłoszenie
- Ankiety na kanale **ankiet** (`/setup-ankiety`)
- Ogłoszenia treningów na kanale **ogłoszeń** (`/setup-ogloszenia`)
- **`/zaplanuj`**, **`/zaplanuj-lista`**, **`/ogloszenie`**
- MVP po meczu, ciche godziny, tygodniówka DM kapitana
- Panele UI, wiele składów, linki do meczów

### 1.5.17
Stabilność: odporny soft-start, twardsze `_edit_or_send`, lock LIVE, helpery `log` / `cfg_json` / `safe_ephemeral` / `api_call`.

### 1.5.16
Ankiety (w tym trening) tylko na kanale ankiet.

### 1.5.15
Kanał ogłoszeń tylko pod treningi.

---

## Soft-start (~90 s)

| Czas | Co |
|------|-----|
| 4–16 s | LIVE → prematch → daily → komendy + sync |
| 20–60 s | Tabela, status, ankiety, API, eventy |
| 70–90 s | Cleanup, update, zaplanowane, weekly |

---

## Kanały

| Setup | Przeznaczenie |
|-------|----------------|
| `/setup` | Główny – wyniki, nadchodzące, prematch |
| `/setup-live` | LIVE |
| `/setup-tabela` | Tabela |
| `/setup-ankiety` | Ankiety (dostępność + trening) |
| `/setup-ogloszenia` | Tylko ogłoszenia treningów |
| `/setup-all` | Panel wszystkich kanałów |

---

## Sztab

| Rola | Kto ustawia | Uprawnienia |
|------|-------------|-------------|
| **Właściciel** | — | wszystko |
| **Kapitan** | `/kapitan` | sztab + `/vicekapitan` + `/coach` |
| **Vicekapitan** | `/vicekapitan` | sztab |
| **Coach** | `/coach` | sztab |

---

## Komendy (skrót)

**Wszyscy:** `/pindolz` `/live` `/wyniki` `/nadchodzace` `/tabela` `/status` `/wersja` `/pomoc` `/gracze` `/moj-status` `/sztab`  
**Sztab:** `/sklad` `/panel` `/polacz` `/ping-sklad` `/sklad-status` `/ankieta-role` `/trening` `/zaplanuj` `/zaplanuj-lista` `/ogloszenie`  
**Kapitan+:** `/vicekapitan` `/coach`  
**Właściciel:** `/setup*` `/ustawienia` `/gif-*` `/pokaz-embedy` `/kapitan`

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
