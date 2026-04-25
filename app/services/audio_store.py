import uuid
from collections import OrderedDict

_MAX = 200
_cache: OrderedDict[str, bytes] = OrderedDict()


def store(audio: bytes) -> str:
    uid = str(uuid.uuid4())
    _cache[uid] = audio
    if len(_cache) > _MAX:
        _cache.popitem(last=False)
    return uid


def get(uid: str) -> bytes | None:
    return _cache.get(uid)
