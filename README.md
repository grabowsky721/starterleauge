> **Wersja bota: `1.6.8`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Rola aktywnego składu

1. `/setup-rola-sklad @rola`
2. Po **Zapisz na mecz** lub **Zapisz + DM** → nadanie roli składowi
3. Po **wyniku** meczu → zdjęcie roli

*(Bez nadawania przy LIVE.)*

---

## Inne

- Soft-start ~35 s · start znika po 2 min
- Zbiórka 60/30/10 · ping roli na prematch
- Konflikt trening vs mecz · `/trening` · szablony

### 1.6.8
Rola tylko po ustaleniu składu (nie przy LIVE).

Team **869** · `src/bot.py` · sekrety: `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN`
