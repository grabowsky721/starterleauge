import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://starterleague.pl/api/partners"
PINDOLZ_TEAM_ID = 869


class StarterLeagueClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("STARTERLEAGUE_API_TOKEN")
        if not self.token:
            raise ValueError(
                "Brak tokena. Ustaw STARTERLEAGUE_API_TOKEN w .env lub przekaż do konstruktora."
            )

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            }
        )

    def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        url = f"{API_BASE}{path}"
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _is_pindolz(self, match: dict) -> bool:
        team1 = match.get("team1") or {}
        team2 = match.get("team2") or {}
        return team1.get("id") == PINDOLZ_TEAM_ID or team2.get("id") == PINDOLZ_TEAM_ID

    def _fetch_all_pages(self, path: str) -> list[dict]:
        """Pobiera wszystkie strony z endpointu meczowego."""
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

    def get_upcoming(self, page: int = 1) -> dict:
        return self._get("/matches/upcoming", params={"page": page})

    def get_history(self, page: int = 1) -> dict:
        return self._get("/matches/history", params={"page": page})

    def get_live(self) -> dict:
        return self._get("/matches/live")

    def get_standings(self, division: str | None = None) -> dict:
        params = {"division": division} if division else None
        return self._get("/standings", params=params)

    # --- tylko PINDOLZ ---

    def get_pindolz_upcoming(self) -> list[dict]:
        all_matches = self._fetch_all_pages("/matches/upcoming")
        return [m for m in all_matches if self._is_pindolz(m)]

    def get_pindolz_history(self) -> list[dict]:
        all_matches = self._fetch_all_pages("/matches/history")
        return [m for m in all_matches if self._is_pindolz(m)]

    def get_pindolz_live(self) -> list[dict]:
        data = self.get_live()
        items = data.get("items") or []
        return [m for m in items if self._is_pindolz(m)]
