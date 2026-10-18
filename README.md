> **Wersja bota: `1.6.10`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz / wyniki / LIVE · soft-start ~35 s
- Brak daty meczu → **„nie ustalono terminu”** (w API data zawsze idzie z godziną)
- Rola aktywnego składu po zapisie składu
- Zbiórka 60/30/10 · ping roli · konflikt trening vs mecz
- `/trening`, szablony, sztab, panele UI

### 1.6.10
Uproszczenie terminu: tylko **nie ustalono terminu** gdy brak daty (bez osobnego „brak godziny”).

### 1.6.9
Zamiast `?` przy braku daty: nie ustalono terminu.

Team **869** · `src/bot.py` + `src/embeds.py`
