> **Wersja bota: `1.6.13`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz / wyniki / LIVE · soft-start ~35 s
- Brak daty → **nie ustalono terminu**
- Rola składu, zbiórka 60/30/10, ping roli, konflikt treningów
- Cache API · mniej blokowania event loop

### 1.6.13
`fetch_user_safe`, async `get_form`, logi w `guarded` zamiast surowego print.

### 1.6.12
Async cache terminarza i tabeli.

Team **869** · `src/bot.py`
