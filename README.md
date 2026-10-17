> **Wersja bota: `1.6.7`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz / wyniki / LIVE · soft-start ~35 s
- **Rola aktywnego składu**: przy zapisie składu **oraz na start LIVE**, zdjęcie po wyniku
- Zbiórka 60/30/10 · ping roli na prematch · konflikt trening vs mecz
- `/trening`, szablony, sztab, panele UI

### 1.6.7
Nadawanie roli aktywnego składu także gdy mecz wchodzi w **LIVE**.

### 1.6.6
Zbiórka 60/30/10, ping składu, konflikt terminów.

---

## Rola aktywnego składu

1. `/setup-rola-sklad @rola`
2. Nadawana przy **Zapisz na mecz** / **Zapisz + DM**
3. Ponownie / uzupełniana gdy mecz idzie **LIVE**
4. Zdejmowana po **wyniku** meczu

Rola bota musi być wyżej na liście ról niż rola składu.

---

## GameHost

Git: `https://github.com/grabowsky721/starterleauge` · `src/bot.py` · Auto Update `1`

Sekrety: `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN` · Team **869**.
