> **Wersja bota: `1.6.12`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz / wyniki / LIVE · soft-start ~35 s
- Brak daty → **nie ustalono terminu**
- Rola aktywnego składu po zapisie składu
- Zbiórka 60/30/10 · ping roli · konflikt trening vs mecz
- Cache API (upcoming 10 min, tabela 5 min) – mniej blokowania event loop

### 1.6.12
Async cache terminarza i tabeli, `load_lineup_ids`, prematch bez sync API w pętli.

### 1.6.11
Odporny soft-start, logi, `safe_int`.

Team **869** · `src/bot.py` + `src/embeds.py`
