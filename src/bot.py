import base64
import os

_raw = []
for i in range(4):
    m = __import__(f"src.p{i}", fromlist=["PART"])
    p = m.PART
    if not isinstance(p, str):
        p = "".join(p)
    _raw.append(base64.b64decode(p))

_src = b"".join(_raw).decode("utf-8")
_ns = globals()
_ns["__file__"] = os.path.abspath(__file__)
_ns["__name__"] = __name__
exec(compile(_src, _ns["__file__"], "exec"), _ns)
