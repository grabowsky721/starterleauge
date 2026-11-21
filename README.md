> **Wersja bota: `1.9.13`** · plik [`VERSION`](VERSION) · komenda `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID **869**) w [StarterLeague](https://starterleague.pl).

Przy każdej zmianie kodu aktualizuj **`VERSION`** i linię wersji na górze tego pliku.

---

## Co nowego w 1.9.10

- Nowe interwały: LIVE **40 s** poza meczem, AREDL **10 min**, API watch **120 s**, watchdog **5 min**, update GitHub **15 min**
- Kolejka terminów: sprawdza co **15 s**, wysyła tylko **12:30–21:15** (1 wiadomość)

### 1.9.9
- Kolejka terminów: **15 s** zamiast 15 min

### 1.9.8
- Kolejka zmian terminu w oknie 12:30–21:15

### 1.9.7
- Soft-start / status / pomoc / odporne przyciski składu / cichsze logi

### 1.9.6
- Wykrywanie zmiany terminu bez limitu 48 h

---

## Interwały

1. **LIVE** – **5 s** w meczu / **40 s** poza  
2. **Prematch** (60/30/10) – **1 min**  
3. **Daily** – **10 min**  
4. **Kolejka terminów** – co **15 s** (wysyłka tylko **12:30–21:15**)  
5. **AREDL** – **10 min**  
6. **Eventy Discord** – **5 min**  
7. **Ankiety** – **5 min**  
8. **Zaplanowane wiadomości** – **30 s**  
9. **Status bota** – **30 s**  
10. **API watch** – **120 s**  
11. **Watchdog** – **5 min**  
12. **Update GitHub** – **15 min**  
13. **Tabela** – **8:00, 18:00, 20:00, 21:30, 23:00**  
14. **Weekly** – **20:00**  
15. **Cleanup** – **4:00**  

---

## GameHost

| Pole | Wartość |
|------|--------|
| Git Repo | `https://github.com/grabowsky721/starterleauge` |
| Branch | `main` |
| Bot py file | `src/bot.py` |
| Requirements | `requirements.txt` |

| Zmienna | Wymagane |
|---------|----------|
| `DISCORD_BOT_TOKEN` | tak |
| `STARTERLEAGUE_API_TOKEN` | tak |

Python 3.10+. **Nie commituj tokenów.**
