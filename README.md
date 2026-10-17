> **Wersja bota: `1.6.8`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz / wyniki / LIVE · soft-start ~35 s
- **Rola aktywnego składu** – tylko po **ustaleniu składu** (Zapisz na mecz / Zapisz + DM), zdjęcie po wyniku
- Zbiórka 60/30/10 · ping roli na prematch · konflikt trening vs mecz
- `/trening`, szablony, sztab, panele UI

### 1.6.8
Rola składu **nie** jest nadawana przy LIVE – tylko po zapisie składu.

### 1.6.6
Zbiórka 60/30/10, ping składu, konflikt terminów.

---

## Rola aktywnego składu

1. `/setup-rola-sklad @rola`
2. **Zapisz na mecz** lub **Zapisz + DM** → nadanie roli
3. Po **wyniku** meczu → zdjęcie roli

---

## GameHost

`src/bot.py` · Auto Update `1` · sekrety: `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN`

Team ID: **869**.
