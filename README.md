> **Wersja bota: `1.5.16`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** co **5 s** (mecz) / **10 s** (brak)
- Soft-start **~90 s** + wiadomość startowa z postępem
- **Sync komend na serwer** (`copy_global_to`) – slash-e od razu widoczne
- **Panele UI**, wiele składów, DM Gram/Nie mogę
- **Sztab**: kapitan, vicekapitan, **coach**
- **`/trening`** – ankieta terminu z auto-zamknięciem
- **`/zaplanuj`** + **`/zaplanuj-lista`**
- **Ciche godziny** (23–8) – w nocy tylko LIVE
- **MVP po meczu** – głosowanie 1 z 5
- **Tygodniówka w DM kapitana**
- Alert zmiany terminu, linki do meczów na StarterLeague

### 1.5.12
Natychmiastowy sync slash-komend na guild (naprawia brak `/zaplanuj` na liście).

### 1.5.11
`/coach`, poprawka `/zaplanuj`, `/zaplanuj-lista`

---

## Soft-start (~90 s)

| Czas | Co |
|------|-----|
| 4–16 s | LIVE → prematch → daily → komendy + sync |
| 20–60 s | Tabela, status, ankiety, API, eventy |
| 70–90 s | Cleanup, update, zaplanowane, weekly |

---

## Sztab

| Rola | Kto ustawia | Uprawnienia |
|------|-------------|-------------|
| **Właściciel** | — | wszystko |
| **Kapitan** | `/kapitan` | sztab + `/vicekapitan` + `/coach` |
| **Vicekapitan** | `/vicekapitan` | sztab |
| **Coach** | `/coach` | sztab |

---

## Komendy

**Wszyscy:** `/pindolz` `/live` `/wyniki` `/nadchodzace` `/tabela` `/status` `/wersja` `/pomoc` `/gracze` `/moj-status` `/sztab`  
**Sztab:** `/sklad` `/panel` `/polacz` `/ping-sklad` `/sklad-status` `/ankieta-role` `/trening` `/zaplanuj` `/zaplanuj-lista`  
**Kapitan+:** `/vicekapitan` `/coach`  
**Właściciel:** `/setup*` `/ustawienia` `/gif-*` `/pokaz-embedy` `/kapitan`

### `/zaplanuj`
`data:` YYYY-MM-DD · `godzina:` HH:MM · `tresc:` · opcjonalnie `kanal:` i `ping_roli:`  
Lista: `/zaplanuj-lista`

Po restarcie w logach powinno być m.in.:
`[sync] global: N komend` oraz `[sync] …: N komend (guild)`.

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
