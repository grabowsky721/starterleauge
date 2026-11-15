> **Wersja bota: `1.9.4`** · plik [`VERSION`](VERSION) · komenda `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID **869**) w [StarterLeague](https://starterleague.pl).

Przy każdej zmianie kodu aktualizuj **`VERSION`** i linię wersji na górze tego pliku.

---

## Co nowego w 1.9.4

- **Usunięte grafiki AI** (Cloudflare FLUX) – całkiem z kodu i `.env`

## Co nowego w 1.9.3

- **UI:** `/pindolz` (hub + menu), `/status`, `/nadchodzace`, `/aredl`, `/aredl-top` – przyciski Odśwież
- **`/mvp-czas`** – ustawienie długości ankiety MVP (1–168 h, domyślnie 24)

## Co nowego w 1.9.2

- Głosowanie MVP trwa **24 h** (wcześniej 30 min)

## Co nowego w 1.9.1

- **`/mvp`** — wynik / status głosowania (`mecz:`, `zamknij:` dla sztabu)

## Co nowego w 1.9.0

- Soft-start: losowe przerwy **3–8 s**, czas na PV
- Rekordy najkrótszy / najdłuższy soft-start (PV przy nowym rekordzie)
- Kolejność: LIVE → … → Cleanup → GitHub → Tabela → **Status**

### 1.8.x (skrót)
- `handle_sklad_confirm`, wydarzenia Discord `entity_type`, soft-start tylko PV właściciela
- AREDL, `/aredl-top`, ciche godziny per funkcja, `/pomoc` kategorie

---

## Główne funkcje

- Mecze: terminarze, wyniki, LIVE, tabela, prematch 60/30/10
- Skład: DM Gram/Nie mogę, panel, rola aktywnego składu
- MVP: głosowanie po meczu + `/mvp` + `/mvp-czas`
- AREDL: `/aredl`, `/aredl-top`, alerty recordów (~8 min)
- Soft-start na PV właściciela z postępem i czasem

---

## GameHost

| Pole | Wartość |
|------|--------|
| Git Repo | `https://github.com/grabowsky721/starterleauge` |
| Branch | `main` |
| Bot py file | `src/bot.py` |
| Requirements | `requirements.txt` |

| Zmienna | Wymagane |
|---------|----------|
| `DISCORD_BOT_TOKEN` | tak |
| `STARTERLEAGUE_API_TOKEN` | tak |

Python 3.10+. **Nie commituj tokenów.**
