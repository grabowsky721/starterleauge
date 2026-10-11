import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://starterleague.pl/api/partners"
PINDOLZ_TEAM_ID = 869
DIVISION_6 = "Starter Division 6"
MAX_PAGES = 30


class StarterLeagueClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("STARTERLEAGUE_API_TOKEN")
        if not self.token:
            raise ValueError("Brak STARTERLEAGUE_API_TOKEN")

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            }
        )
        self.current_division: str = DIVISION_6
        self.on_division = None  # callback(nazwa_dywizji), ustawiany przez bota
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_ttl = {
            "live": 4,
            "standings": 45,
            "upcoming": 60,
            "history": 90,
        }

    def _cache_get(self, key: str):
        item = self._cache.get(key)
        if not item:
            return None
        expires, value = item
        if time.monotonic() > expires:
            self._cache.pop(key, None)
            return None
        return value

    def _cache_set(self, key: str, value: Any, ttl: float | None = None) -> Any:
        if ttl is None:
            ttl = self._cache_ttl.get(key, 30)
        self._cache[key] = (time.monotonic() + ttl, value)
        return value

    def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        url = f"{API_BASE}{path}"
        last_err: Exception | None = None
        for attempt in range(2):
            try:
                resp = self.session.get(url, params=params, timeout=12)
                resp.raise_for_status()
                return resp.json()
            except (requests.Timeout, requests.ConnectionError) as e:
                last_err = e
                if attempt == 0:
                    time.sleep(0.8)
                    continue
                raise
        raise last_err  # type: ignore

    def _is_pindolz(self, match: dict) -> bool:
        t1 = match.get("team1") or {}
        t2 = match.get("team2") or {}
        return t1.get("id") == PINDOLZ_TEAM_ID or t2.get("id") == PINDOLZ_TEAM_ID

    def _fetch_all_pages(self, path: str) -> list[dict]:
        items: list[dict] = []
        page = 1
        while page <= MAX_PAGES:
            data = self._get(path, params={"page": page})
            page_items = data.get("items") or []
            items.extend(page_items)
            pagination = data.get("pagination") or {}
            if not pagination.get("hasNextPage"):
                break
            page += 1
        return items

    def get_live_raw(self) -> dict:
        return self._get("/matches/live")

    def get_pindolz_upcoming(self) -> list[dict]:
        cached = self._cache_get("upcoming")
        if cached is not None:
            return cached
        data = [m for m in self._fetch_all_pages("/matches/upcoming") if self._is_pindolz(m)]
        return self._cache_set("upcoming", data)

    def get_pindolz_history(self) -> list[dict]:
        cached = self._cache_get("history")
        if cached is not None:
            return cached
        data = [m for m in self._fetch_all_pages("/matches/history") if self._is_pindolz(m)]
        return self._cache_set("history", data)

    def get_pindolz_live(self) -> list[dict]:
        cached = self._cache_get("live")
        if cached is not None:
            return cached
        data = self.get_live_raw()
        items = data.get("items") or []
        result = [m for m in items if self._is_pindolz(m)]
        return self._cache_set("live", result)

    def get_standings(self, division: str | None = None) -> dict:
        params = {"division": division} if division else None
        return self._get("/standings", params=params)

    def get_pindolz_division(self) -> str:
        """Dywizja PINDOLZ wykrywana z meczów (live → nadchodzące → historia)."""
        cached = self._cache_get("division")
        if cached:
            return cached
        name = None
        for fetch in (self.get_pindolz_live, self.get_pindolz_upcoming, self.get_pindolz_history):
            try:
                for m in fetch():
                    if m.get("division"):
                        name = m["division"]
                        break
            except Exception:
                continue
            if name:
                break
        return self._cache_set("division", name or DIVISION_6, ttl=600)

    @staticmethod
    def _extract_table(data: dict, division: str) -> list[dict]:
        divisions = data.get("divisions") or []
        for d in divisions:
            if d.get("division") == division:
                return d.get("table") or []
        key = division.lower().replace(" ", "")
        for d in divisions:
            if (d.get("division") or "").lower().replace(" ", "") == key:
                return d.get("table") or []
        return []

    @staticmethod
    def _has_pindolz(table: list[dict]) -> bool:
        for row in table:
            team = row.get("team") or {}
            if team.get("id") == PINDOLZ_TEAM_ID or (team.get("name") or "").upper() == "PINDOLZ":
                return True
        return False

    def get_division_table(self) -> list[dict]:
        """Tabela dywizji, w której aktualnie gra PINDOLZ (wykrywana automatycznie)."""
        cached = self._cache_get("standings")
        if cached is not None:
            return cached
        division = self.get_pindolz_division()
        table = self._extract_table(self.get_standings(division), division)
        if not self._has_pindolz(table):
            # PINDOLZ nie ma w tej tabeli (np. po awansie) – szukamy go we wszystkich dywizjach
            try:
                for d in self.get_standings().get("divisions") or []:
                    t = d.get("table") or []
                    if self._has_pindolz(t):
                        division, table = d.get("division") or division, t
                        break
            except Exception:
                pass
        if not table and division != DIVISION_6:
            division = DIVISION_6
            table = self._extract_table(self.get_standings(DIVISION_6), DIVISION_6)
        self.current_division = division
        if self.on_division:
            try:
                self.on_division(division)
            except Exception:
                pass
        return self._cache_set("standings", table)

    # zgodność wsteczna (bot wywołuje tę nazwę w wielu miejscach)
    get_division6_table = get_division_table

    def get_pindolz_standing(self) -> dict | None:
        table = self.get_division_table()
        for row in table:
            team = row.get("team") or {}
            if team.get("id") == PINDOLZ_TEAM_ID or (team.get("name") or "").upper() == "PINDOLZ":
                return row
        return None

    def get_form(self, history: list[dict] | None = None, limit: int = 5) -> str:
        if history is None:
            history = self.get_pindolz_history()
        letters: list[str] = []
        for m in history[:limit]:
            winner = m.get("winnerTeamId")
            if winner is None:
                letters.append("?")
                continue
            letters.append("W" if winner == PINDOLZ_TEAM_ID else "L")
        return "".join(reversed(letters))

    def did_pindolz_win(self, match: dict) -> bool | None:
        winner = match.get("winnerTeamId")
        if winner is None:
            return None
        return winner == PINDOLZ_TEAM_ID

    def invalidate_cache(self, *keys: str) -> None:
        if not keys:
            self._cache.clear()
            return
        for k in keys:
            self._cache.pop(k, None)
