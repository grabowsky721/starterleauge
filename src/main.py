from src.client import StarterLeagueClient


def main():
    client = StarterLeagueClient()

    print("=== PINDOLZ – nadchodzące mecze ===")
    upcoming = client.get_pindolz_upcoming()
    if not upcoming:
        print("Brak nadchodzących meczów")
    for m in upcoming:
        t1 = m["team1"]["name"]
        t2 = m["team2"]["name"]
        date = m.get("matchDate", "?")
        time = m.get("matchTime") or ""
        print(f"{date} {time} | {t1} vs {t2} | {m.get('division')}")

    print("\n=== PINDOLZ – ostatnie wyniki ===")
    history = client.get_pindolz_history()
    if not history:
        print("Brak historii")
    for m in history[:10]:  # ostatnie 10
        t1 = m["team1"]["name"]
        t2 = m["team2"]["name"]
        score = m.get("score") or {}
        s1 = score.get("team1", "-")
        s2 = score.get("team2", "-")
        date = m.get("matchDate", "?")
        print(f"{date} | {t1} {s1}:{s2} {t2} | {m.get('division')}")

    print("\n=== PINDOLZ – live ===")
    live = client.get_pindolz_live()
    if not live:
        print("Aktualnie żaden mecz PINDOLZ nie trwa")
    for m in live:
        t1 = m["team1"]["name"]
        t2 = m["team2"]["name"]
        current = m.get("currentMap") or {}
        score = current.get("score") or {}
        print(
            f"LIVE | {t1} vs {t2} | mapa {current.get('name')} "
            f"{score.get('team1', 0)}:{score.get('team2', 0)}"
        )


if __name__ == "__main__":
    main()
