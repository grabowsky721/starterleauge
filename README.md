> **Wersja bota: `1.7.9`** · plik [`VERSION`](VERSION) · komenda `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID **869**) w [StarterLeague](https://starterleague.pl).

Przy każdej zmianie kodu aktualizuj **`VERSION`** i linię wersji na górze tego pliku.

---

## Co nowego w 1.7.9

- AREDL: sprawdzenie nowych recordów co **8 min** (wcześniej 12)

### 1.7.8
- Przywrócone **grafiki AI** (Cloudflare Workers AI / FLUX): zapowiedź meczu + wynik
- Env: `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` (opcjonalne)

### Wcześniej (1.7.4–1.7.7)
- **AREDL**: `/setup-aredl` (kanał + ping roli), `/aredl`, `/aredl nick:…`
- Alert o nowym zatwierdzonym recordzie klanu Pdlz
- Naprawa `get_form` / `daily_check`
- Usunięte VC
- GIF-y osobno po wygranej i przegranej

---

## Struktura projektu

```
VERSION
README.md
requirements.txt
.env.example
src/
  bot.py
  client.py
  db.py
  embeds.py
```

---

## Sekrety (GameHost)

| Zmienna | Wymagane | Opis |
|---------|----------|------|
| `DISCORD_BOT_TOKEN` | tak | Token bota Discord |
| `STARTERLEAGUE_API_TOKEN` | tak | Token Partner API |
| `CLOUDFLARE_ACCOUNT_ID` | nie | Grafiki AI |
| `CLOUDFLARE_API_TOKEN` | nie | Grafiki AI |

**Nie commituj tokenów do repozytorium.**

---

## GameHost

| Pole | Wartość |
|------|--------|
| Git Repo | `https://github.com/grabowsky721/starterleauge` |
| Branch | `main` |
| Auto Update | `1` |
| Bot py file | `src/bot.py` |
| Requirements | `requirements.txt` |
