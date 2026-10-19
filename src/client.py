import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://starterleague.pl/api/partners"
PINDOLZ_TEAM_ID = 869
DIVISION_6 = "Starter Division 6"
MASTERS = "Starter Masters"


class StarterLeagueClient:
    def __init__(self, token: str | None = None):
        self.on_division = None  # opcjonalny callback nazwy dywizji
        self.token = token or os.getenv("STARTERLEAGUE_API_TOKEN") or ""
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
        })
        self._cache: dict[str, tuple[float, Any]] = {}
        self._default_ttl = 30.0

    def _cache_get(self, key: str):
        item = self._cache.get(key)
        if not item:
            return None
        exp, val = item
        if time.time() > exp:
            self._cache.pop(key, None)
            return None
        return val

    def _cache_set(self, key: str, value: Any, ttl: float | None = None) -> Any:
        self._cache[key] = (time.time() + (ttl if ttl is not None else self._default_ttl), value)
        return value

    def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        url = f"{API_BASE}{path}"
        last_err = None
        for attempt in range(2):
            try:
                r = self.session.get(url, params=params, timeout=12)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last_err = e
                time.sleep(0.4 * (attempt + 1))
        raise last_err  # type: ignore

    def _is_pindolz(self, match: dict) -> bool:
        t1 = match.get("team1") or {}
        t2 = match.get("team2") or {}
        return t1.get("id") == PINDOLZ_TEAM_ID or t2.get("id") == PINDOLZ_TEAM_ID

    def _fetch_all_pages(self, path: str) -> list[dict]:
        out: list[dict] = []
        page = 1
        max_pages = 30
        while page <= max_pages:
            data = self._get(path, {"page": page})
            items = data.get("data") or data.get("matches") or []
            if isinstance(data, list):
                items = data
            if not items:
                break
            out.extend(items)
            meta = data.get("meta") or data.get("pagination") or {}
            if isinstance(meta, dict):
                last = meta.get("last_page") or meta.get("total_pages")
                if last and page >= int(last):
                    break
            if len(items) < 10:
                break
            page += 1
        return out

    def get_live_raw(self) -> dict:
        return self._get("/matches/live")

    def get_pindolz_upcoming(self) -> list[dict]:
        key = "upcoming"
        hit = self._cache_get(key)
        if hit is not None:
            return hit
        items = [m for m in self._fetch_all_pages("/matches/upcoming") if self._is_pindolz(m)]
        return self._cache_set(key, items, 45)

    def get_pindolz_history(self) -> list[dict]:
        key = "history"
        hit = self._cache_get(key)
        if hit is not None:
            return hit
        items = [m for m in self._fetch_all_pages("/matches/history") if self._is_pindolz(m)]
        return self._cache_set(key, items, 60)

    def get_pindolz_live(self) -> list[dict]:
        key = "live"
        hit = self._cache_get(key)
        if hit is not None:
            return hit
        data = self.get_live_raw()
        items = data.get("data") or data.get("matches") or []
        if isinstance(data, list):
            items = data
        items = [m for m in items if self._is_pindolz(m)]
        return self._cache_set(key, items, 5)

    def get_standings(self, division: str | None = None) -> dict:
        params = {}
        if division:
            params["division"] = division
        return self._get("/standings", params)

    def get_pindolz_division(self) -> str:
        # try detect from standings
        for div in (DIVISION_6, MASTERS):
            try:
                data = self.get_standings(div)
                table = self._extract_table(data, div)
                if self._has_pindolz(table):
                    if callable(self.on_division):
                        try:
                            self.on_division(div)
                        except Exception:
                            pass
                    return div
            except Exception:
                continue
        return DIVISION_6

    def _extract_table(self, data: dict, division: str) -> list[dict]:
        if isinstance(data, list):
            return data
        for key in ("data", "standings", "table", "rows"):
            if isinstance(data.get(key), list):
                return data[key]
        divisions = data.get("divisions") or {}
        if isinstance(divisions, dict) and division in divisions:
            block = divisions[division]
            if isinstance(block, list):
                return block
            if isinstance(block, dict):
                return block.get("standings") or block.get("table") or []
        return []

    def _has_pindolz(self, table: list[dict]) -> bool:
        for row in table:
            team = row.get("team") or {}
            if team.get("id") == PINDOLZ_TEAM_ID or (team.get("name") or "").upper() == "PINDOLZ":
                return True
        return False

    def get_division_table(self) -> list[dict]:
        key = "table"
        hit = self._cache_get(key)
        if hit is not None:
            return hit
        div = self.get_pindolz_division()
        data = self.get_standings(div)
        table = self._extract_table(data, div)
        return self._cache_set(key, table, 60)

    def get_division6_table(self) -> list[dict]:
        """Alias używany przez bota – ta sama tabela co get_division_table."""
        return self.get_division_table()

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
