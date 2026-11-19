> **Wersja bota: `1.9.8`** · plik [`VERSION`](VERSION) · komenda `/wersja`

# PINDOLZ Discord Bot

Bot Discorda do śledzenia meczów drużyny **PINDOLZ** (ID **869**) w [StarterLeague](https://starterleague.pl).

---

## Co nowego w 1.9.8

- Kolejka **zmian terminu**: wysyłka tylko **12:30–21:15**, **1 wiadomość co 15 min**
- Wykrycie zmiany → zawsze do kolejki (bez spamu poza oknem)

### 1.9.7
- Ciche godziny / rekordy soft-startu tylko w embedzie / odporne przyciski składu
- `/pomoc`, `/status` (taski + AREDL), cichsze logi Discord

### 1.9.6
- Wykrywanie zmiany terminu bez limitu 48 h

---

## Interwały (jak często co działa)

1. **LIVE** – co **5 s** w meczu, co **10 s** poza  
2. **Prematch** (60/30/10 min) – co **1 min**  
3. **Daily** (wyniki, nadchodzące, zapis terminów) – co **10 min**  
4. **Kolejka zmian terminu** – co **15 min**, tylko **12:30–21:15**  
5. **AREDL** (nowe recordy) – co **8 min**  
6. **Eventy Discord** – co **5 min**  
7. **Ankiety dostępności** – co **5 min**  
8. **Zaplanowane wiadomości** – co **30 s**  
9. **Status bota** (presence) – co **30 s**  
10. **API watch** – co **60 s**  
11. **Watchdog** (restart pętli) – co **2 min**  
12. **Update GitHub** – co **1 h**  
13. **Tabela** – o **8:00, 18:00, 20:00, 21:30, 23:00**  
14. **Weekly** – o **20:00**  
15. **Cleanup** – o **4:00**  

---

## GameHost

| Pole | Wartość |
|------|--------|
| Bot py file | `src/bot.py` |
| Requirements | `requirements.txt` |

`DISCORD_BOT_TOKEN` + `STARTERLEAGUE_API_TOKEN` wymagane.
