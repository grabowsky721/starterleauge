def standings_embed(
    table: list[dict],
    division: str = "Starter Division 6",
    changes: dict | None = None,
) -> discord.Embed:
    embed = _base(f"🏆 Tabela · {division}", C_TABLE)
    if not table:
        embed.description = "Brak danych tabeli."
        return embed
    changes = changes or {}
    lines = [f" {'#':>2} {'Drużyna':<14} {'W-L':>5} {'RD':>4} {'Pkt':>3}"]
    lines.append("─" * 33)
    for row in table[:16]:
        rank = row.get("rank") or "?"
        team = (row.get("team") or {}).get("name") or "???"
        pts = row.get("points")
        w = row.get("wins") or 0
        l = row.get("losses") or 0
        marker = "▶" if team.upper() == "PINDOLZ" else " "
        d = changes.get(team.upper(), 0)
        delta = f" ▲{min(d, 9)}" if d > 0 else f" ▼{min(abs(d), 9)}" if d < 0 else ""
        lines.append(
            f"{marker}{str(rank):>2} {team[:14]:<14} {f'{w}-{l}':>5} "
            f"{_signed(row.get('roundDifference')):>4} {pts if pts is not None else '–':>3}{delta}"
        )
    embed.description = "```\n" + "\n".join(lines) + "\n```"
    embed.set_footer(
        text="▶ PINDOLZ • RD = różnica rund" + (" • ▲▼ zmiana pozycji" if changes else "")
    )
    _add_links(embed)
    return embed