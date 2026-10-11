"""Pełny kod bota z commita 4e90980 (ostatnia dobra wersja przed awarią pusha)."""
import os
import urllib.request

GOOD_URL = (
    "https://raw.githubusercontent.com/grabowsky721/starterleauge/"
    "4e90980ac18b2646c33df8e5823840d5dcb21434/src/bot.py"
)

try:
    with urllib.request.urlopen(GOOD_URL, timeout=30) as resp:
        _src = resp.read().decode("utf-8")
except Exception as e:
    raise SystemExit(f"Nie udalo sie pobrac bot.py: {e}\nURL: {GOOD_URL}") from e

if "class PindolzBot" not in _src or "bot.run" not in _src:
    raise SystemExit("Pobrany bot.py jest uszkodzony.")

_ns = globals()
_ns["__file__"] = os.path.abspath(__file__)
_ns["__name__"] = __name__
exec(compile(_src, _ns["__file__"], "exec"), _ns)
