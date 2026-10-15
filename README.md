> **Wersja bota: `1.5.10`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz i wyniki – **edycja** wiadomości zamiast spamu
- **LIVE** co **5 s** (mecz) / **10 s** (brak)
- Soft-start **~90 s**
- **`/zaplanuj`** – zaplanowana wiadomość
- **Ciche godziny** (23–8) – tylko LIVE
- **MVP** po meczu (głosowanie 1 z 5)
- **Tygodniówka DM kapitana**
- Alert zmiany terminu, `/trening`, sztab, panele UI, wiele składów

## Hotfix 1.5.10

Naprawiono crash: `AttributeError: weekly_summary.before_loop` (dekorator `@tasks.loop` wrócił na `weekly_summary`).

## GameHost

| Pole | Wartość |
|------|---------|
| Git Repo | `https://github.com/grabowsky721/starterleauge` |
| Bot py file | `src/bot.py` |
| Auto Update | `1` |

Sekrety: `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN`

Team ID: **869**.
