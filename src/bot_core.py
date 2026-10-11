from src.bot_views import *  # noqa: F401,F403
from src._core_a import SRC as _A
from src._core_b import SRC as _B

exec(_A + _B, globals())
