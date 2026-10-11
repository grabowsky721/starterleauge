"""Bootstrap: load working bot from known-good commit (restores after broken push)."""
import os
import sys
import urllib.request

GOOD_URL = (
    "https://raw.githubusercontent.com/grabowsky721/starterleauge/"
    "4e90980ac18b2646c33df8e5823840d5dcb21434/src/bot.py"
)

# Prefer local full file if present (dev)
_local_candidates = [
    os.path.join(os.path.dirname(__file__), "bot_full.py"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot_good.py"),
]

_src = None
for _path in _local_candidates:
    if os.path.isfile(_path):
        with open(_path, "r", encoding="utf-8") as _f:
            _src = _f.read()
        break

if _src is None:
    try:
        with urllib.request.urlopen(GOOD_URL, timeout=30) as _resp:
            _src = _resp.read().decode("utf-8")
    except Exception as _e:
        raise SystemExit(
            f"Nie udalo sie pobrac bot.py z GitHuba ({_e}). "
            f"URL: {GOOD_URL}"
        ) from _e

if "class PindolzBot" not in _src or "bot.run" not in _src:
    raise SystemExit("Pobrany bot.py wyglada na uszkodzony (brak PindolzBot / bot.run).")

_ns = globals()
_ns["__file__"] = os.path.abspath(__file__)
_ns["__name__"] = __name__
exec(compile(_src, _ns["__file__"], "exec"), _ns)
