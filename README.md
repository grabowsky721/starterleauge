> **Wersja bota: `1.6.0`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** (5 s / 10 s) + lock przebiegów
- Soft-start **~90 s**, sync slash na guild od razu
- **Sztab**: kapitan, vice, coach
- **`/trening`**: dni → godziny → wydarzenie + **ocena 1–5** (wyniki tylko sztab)
- Ankiety → kanał ankiet · ogłoszenia treningów → kanał ogłoszeń
- **Szablony ogłoszeń**: `/szablon-dodaj` · `/ogloszenie szablon:`
- Rola **aktywnego składu** przy zapisie składu, zdjęcie po meczu
- `/zaplanuj`, MVP, ciche godziny, panele UI, wiele składów

### 1.6.0
Wersja zbiorcza po cyklu 1.5.x (trening, szablony, rola składu, stabilność, kanały).

---

## Kanały

| Komenda | Kanał |
|---------|--------|
| `/setup` | Główny (wyniki, nadchodzące, prematch) |
| `/setup-live` | LIVE |
| `/setup-tabela` | Tabela |
| `/setup-ankiety` | Ankiety + ocena treningu |
| `/setup-ogloszenia` | Ogłoszenia treningów |
| `/setup-rola-sklad` | Rola przy składzie na mecz |
| `/setup-all` | Panel kanałów |

---

## Sztab

| Rola | Uprawnienia |
|------|-------------|
| Właściciel | wszystko + setup |
| Kapitan | sztab + vice + coach |
| Vice / Coach | sztab |

---

## Komendy (skrót)

**Wszyscy:** `/pindolz` `/live` `/wyniki` `/nadchodzace` `/tabela` `/status` `/wersja` `/pomoc` `/gracze` `/moj-status` `/sztab` `/szablon-lista`  
**Sztab:** `/sklad` `/panel` `/trening` `/ogloszenie` `/szablon-*` `/zaplanuj` …  
**Właściciel:** `/setup*` `/ustawienia` `/kapitan` `/setup-rola-sklad`

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

Team ID: **869**.
