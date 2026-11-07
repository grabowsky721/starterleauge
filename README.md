> **Wersja bota: `1.9.0`** · plik [`VERSION`](VERSION) · komenda `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID **869**) w [StarterLeague](https://starterleague.pl).

Przy każdej zmianie kodu aktualizuj **`VERSION`** i linię wersji na górze tego pliku.

---

## Co nowego w 1.9.0

- Soft-start: losowe przerwy **3–8 s**, czas trwania na PV
- Rekordy **najkrótszy / najdłuższy** soft-start (PV właściciela przy nowym rekordzie)
- Kolejność: LIVE → … → Cleanup → GitHub → Tabela → **Status** (ostatni)

### 1.8.x (skrót)
- `handle_sklad_confirm`, wydarzenia Discord `entity_type`, soft-start tylko PV właściciela
- AREDL, `/aredl-top`, ciche godziny per funkcja, `/pomoc` kategorie

---

## GameHost

| Pole | Wartość |
|------|--------|
| Git Repo | `https://github.com/grabowsky721/starterleauge` |
| Branch | `main` |
| Bot py file | `src/bot.py` |
| Requirements | `requirements.txt` |

Python 3.10+.

**Nie commituj tokenów.**
