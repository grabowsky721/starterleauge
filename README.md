> **Wersja bota: `1.6.8`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz / wyniki / LIVE · soft-start ~35 s
- **Rola aktywnego składu** – tylko gdy mecz jest **LIVE**, zdejmowana po wyniku (nie przy zapisie składu)
- Zbiórka 60/30/10 · ping roli na prematch · konflikt trening vs mecz
- `/trening`, szablony, sztab, panele UI

### 1.6.8
Rola składu **nie** jest nadawana przy zapisie składu – tylko na start **LIVE**.

### 1.6.7
Rola także na LIVE (wcześniej też przy zapisie).

### 1.6.6
Zbiórka 60/30/10, ping składu, konflikt terminów.

---

## Rola aktywnego składu

1. `/setup-rola-sklad @rola`
2. Skład zapisujesz jak zwykle (bez roli)
3. Gdy mecz wejdzie w **LIVE** → bot nadaje rolę zapisanemu składowi
4. Po **wyniku** → zdejmuje rolę

Rola bota wyżej na liście niż rola składu.

---

## GameHost

Git: `https://github.com/grabowsky721/starterleauge` · `src/bot.py` · Auto Update `1`

Sekrety: `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN` · Team **869**.
