> **Wersja bota: `1.6.11`** · plik [`VERSION`](VERSION) · `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID 869) w lidze [StarterLeague](https://starterleague.pl).

> Przy każdej zmianie kodu aktualizuj **`VERSION`** i tę linię na górze README.

---

## Funkcje

- Terminarz / wyniki / LIVE · soft-start ~35 s
- Brak daty → **nie ustalono terminu**
- Rola aktywnego składu po zapisie składu
- Zbiórka 60/30/10 · ping roli · konflikt trening vs mecz
- `/trening`, szablony, sztab, panele UI

### 1.6.11
Ulepszenia kodu: odporny soft-start (błąd kroku nie wywala reszty), jednolite logi, `safe_int`, drobne poprawki embeds.

### 1.6.10
Brak daty = nie ustalono terminu.

---

Team **869** · `src/bot.py` + `src/embeds.py`
