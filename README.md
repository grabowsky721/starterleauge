# StarterLeague Partner API – PINDOLZ

Prosty klient do oficjalnego Partner API StarterLeague, który zwraca **tylko mecze drużyny PINDOLZ** (team id: `869`).

## Endpointy używane

- `GET /matches/upcoming`
- `GET /matches/history`
- `GET /matches/live`
- `GET /standings`

API **nie ma** filtra po drużynie, więc klient sam stronicuje i filtruje po `team1.id` / `team2.id`.

## Szybki start

1. Skopiuj `.env.example` → `.env` i wklej swój token:
   ```bash
   cp .env.example .env
   ```

2. Zainstaluj zależności:
   ```bash
   pip install -r requirements.txt
   ```

3. Odpal:
   ```bash
   python -m src.main
   ```

## Token

Token generujesz po zalogowaniu na https://starterleague.pl/api-partnerskie  
Zaczyna się od `slp_`.

**Nigdy** nie commituj pliku `.env`.

## Przykład użycia w kodzie

```python
from src.client import StarterLeagueClient

client = StarterLeagueClient()

# tylko mecze PINDOLZ
upcoming = client.get_pindolz_upcoming()
history = client.get_pindolz_history()
live = client.get_pindolz_live()

print(f"Nadchodzące: {len(upcoming)}")
print(f"Historia: {len(history)}")
print(f"Live: {len(live)}")
```

## Struktura

```
├── .env.example
├── requirements.txt
├── README.md
└── src/
    ├── __init__.py
    ├── client.py      # główny klient API + filtr PINDOLZ
    └── main.py        # przykład uruchomienia
```
