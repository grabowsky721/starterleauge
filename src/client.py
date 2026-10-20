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
                "User-Agent": "PINDOLZ-Bot/1.6",
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
        items = data.get("items") or data.get("matches") or []
        if isinstance(data, list):
            items = data
        out = [m for m in items if isinstance(m, dict) and self._is_pindolz(m)]
        return self._cache_set("live", out)

    def get_standings(self, division: str | None = None) -> list:
        div = division or self.current_division
        cache_key = f"standings:{div}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        data = self._get("/standings", params={"division": div})
        table = self._extract_table(data)
        return self._cache_set(cache_key, table, ttl=self._cache_ttl.get("standings", 45))

    def get_pindolz_division(self) -> str:
        return self.current_division

    def _extract_table(self, data) -> list:
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []
        for key in ("standings", "items", "table", "rows"):
            if isinstance(data.get(key), list):
                return data[key]
        return []

    def _has_pindolz(self, table: list) -> bool:
        for row in table or []:
            team = row.get("team") or {}
            if team.get("id") == PINDOLZ_TEAM_ID:
                return True
            name = (team.get("name") or "").upper()
            if name == "PINDOLZ":
                return True
        return False

    def get_division_table(self, division: str | None = None) -> list:
        div = division or self.current_division
        table = self.get_standings(div)
        if table and self._has_pindolz(table):
            if self.on_division:
                try:
                    self.on_division(div)
                except Exception:
                    pass
            return table
        # fallback: spróbuj Division 6
        if div != DIVISION_6:
            table6 = self.get_standings(DIVISION_6)
            if table6 and self._has_pindolz(table6):
                self.current_division = DIVISION_6
                if self.on_division:
                    try:
                        self.on_division(DIVISION_6)
                    except Exception:
                        pass
                return table6
        return table or []

    def get_pindolz_standing(self):
        table = self.get_division_table()
        for row in table or []:
            team = row.get("team") or {}
            if team.get("id") == PINDOLZ_TEAM_ID or (team.get("name") or "").upper() == "PINDOLZ":
                return row
        return None

    def get_form(self, limit: int = 5) -> list[dict]:
        hist = self.get_pindolz_history()
        return hist[:limit] if hist else []

    def did_pindolz_win(self, match: dict) -> bool | None:
        w = match.get("winnerTeamId")
        if w is None:
            return None
        try:
            return int(w) == PINDOLZ_TEAM_ID
        except Exception:
            return None

    def get_division6_table(self) -> list:
        """Alias wstecznej kompatybilności."""
        return self.get_division_table()

    def invalidate_cache(self, key: str | None = None) -> None:
        if key is None:
            self._cache.clear()
        else:
            self._cache.pop(key, None)
