> **Wersja bota: `1.5.10`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** co **5 s** (mecz) / **10 s** (brak)
- Soft-start **~90 s** + wiadomość startowa z postępem
- **Panele UI**: `/sklad`, `/setup-all`, `/polacz`, `/ankieta-role`, `/gif-lista`, `/panel`, `/ustawienia`
- **Wiele nazwanych składów** + zapis na mecz + DM Gram/Nie mogę
- **Sztab**: kapitan i vicekapitan
- **`/trening`** – ankieta terminu z auto-zamknięciem
- **`/zaplanuj`** – zaplanowana wiadomość (data + godzina + kanał)
- **Ciche godziny** (23–8) – w nocy tylko LIVE (`/ustawienia`)
- **MVP po meczu** – głosowanie 1 z 5 (auto, bez komendy)
- **Tygodniówka w DM kapitana** – wyniki + frekwencja (niedziela)
- Alert **zmiany terminu** meczu
- Link do meczu na StarterLeague w embedach
- Komendy w **DM**: `/panel`, `/sklad-status`, `/ping-sklad`, `/moj-status`, `/pomoc`
- Update wersji z GitHuba **co 1 h**

### Hotfix 1.5.10
Naprawiono crash startu: `AttributeError: 'function' object has no attribute 'before_loop'` (dekorator `@tasks.loop` na `weekly_summary`).

---

## Soft-start (~90 s)

| Czas | Co |
|------|-----|
| 4 s | LIVE |
| 8 s | Prematch |
| 12 s | Daily |
| 16 s | Komendy + sync |
| 20–60 s | Tabela, status, ankiety, API, eventy |
| 70–90 s | Cleanup, update, zaplanowane, weekly |

---

## Sztab

| Rola | Uprawnienia |
|------|-------------|
| **Właściciel** | wszystko |
| **Kapitan** | skład, panel, polacz, ping, ankiety, trening, zaplanuj, vice |
| **Vicekapitan** | jak kapitan, bez ustawiania vice |

---

## Komendy

**Wszyscy:** `/pindolz` `/live` `/wyniki` `/nadchodzace` `/tabela` `/status` `/wersja` `/pomoc` `/gracze` `/moj-status` `/sztab`  
**Sztab:** `/sklad` `/panel` `/polacz` `/ping-sklad` `/sklad-status` `/ankieta-role` `/trening` `/zaplanuj` `/vicekapitan`  
**Właściciel:** `/setup*` `/ustawienia` `/gif-*` `/pokaz-embedy` `/kapitan`

---

## Harmonogram

| Co | Kiedy |
|----|-------|
| LIVE | 5 s / 10 s |
| Prematch / Daily | poza cichymi godzinami |
| Tabela | 08:00, 18:00, 20:00, 21:30, 23:00 |
| Weekly + DM kapitana | niedziela 20:00 |
| Zaplanowane | co 30 s |
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

Team ID: **869**. Wersja: zgodne `VERSION` + README + `/wersja`.
