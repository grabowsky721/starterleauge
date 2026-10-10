import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://starterleague.pl/api/partners"
PINDOLZ_TEAM_ID = 869
DIVISION_6 = "Starter Division 6"


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

    def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        url = f"{API_BASE}{path}"
        resp = self.session.get(url, params=params, timeout=12)
        resp.raise_for_status()
        return resp.json()

    def _is_pindolz(self, match: dict) -> bool:
        t1 = match.get("team1") or {}
        t2 = match.get("team2") or {}
        return t1.get("id") == PINDOLZ_TEAM_ID or t2.get("id") == PINDOLZ_TEAM_ID

    def _opponent_name(self, match: dict) -> str:
        t1 = match.get("team1") or {}
        t2 = match.get("team2") or {}
        if t1.get("id") == PINDOLZ_TEAM_ID:
            return t2.get("name") or "???"
        return t1.get("name") or "???"

    def _fetch_all_pages(self, path: str) -> list[dict]:
        items: list[dict] = []
        page = 1
        while True:
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
        return [m for m in self._fetch_all_pages("/matches/upcoming") if self._is_pindolz(m)]

    def get_pindolz_history(self) -> list[dict]:
        return [m for m in self._fetch_all_pages("/matches/history") if self._is_pindolz(m)]

    def get_pindolz_live(self) -> list[dict]:
        data = self.get_live_raw()
        items = data.get("items") or []
        return [m for m in items if self._is_pindolz(m)]

    def get_standings(self, division: str | None = None) -> dict:
        params = {"division": division} if division else None
        return self._get("/standings", params=params)

    def get_division6_table(self) -> list[dict]:
        """Tabela Starter Division 6."""
        data = self.get_standings(DIVISION_6)
        divisions = data.get("divisions") or []
        for d in divisions:
            if d.get("division") == DIVISION_6:
                return d.get("table") or []
        # fallback – szukaj po fragmencie nazwy
        for d in divisions:
            name = (d.get("division") or "").lower()
            if "division 6" in name or "division6" in name:
                return d.get("table") or []
        return []
