> **Wersja bota: `1.6.6`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz / wyniki / LIVE
- Soft-start **~35 s**, wiadomość startu znika po **2 min**
- **Zbiórka 60 / 30 / 10 min** – DM do składu bez „Gram” + lista do kapitana
- Prematch z **pingiem roli aktywnego składu** (`/setup-rola-sklad`)
- **Konflikt terminów** – ostrzeżenie przy treningu blisko meczu ligowego (±2 h)
- `/trening`, szablony, sztab, panele UI

### 1.6.6
Zbiórka 60/30/10, ping `@aktywny-skład` na prematch, konflikt trening vs mecz.

### 1.6.5
Stopka startu 2 min wymuszona w bocie.

### 1.6.4
Fix `/setup-all` ChannelSelect.

---

## Prematch / zbiórka

| Czas | Co |
|------|-----|
| 60 min | Kanał + DM zbiórki (feature `prematch1h`) |
| 30 min | Kanał + DM zbiórki + stare remind DM |
| 10 min | Kanał + DM zbiórki |

Ping roli z `/setup-rola-sklad`, jeśli ustawiona.  
Zbiórka: gracze ze składu bez potwierdzenia **Gram**.

---

## GameHost

| Pole | Wartość |
|------|---------|
| Git Repo | `https://github.com/grabowsky721/starterleauge` |
| Bot py file | `src/bot.py` |
| Auto Update | `1` |

Sekrety: `DISCORD_BOT_TOKEN`, `STARTERLEAGUE_API_TOKEN`

Team ID: **869**.
