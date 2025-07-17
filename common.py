from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import List

DUMMY_BLOCK_INDEX = -1


@dataclass
class Block:
    data: bytes = field(default_factory=bytes)
    index: int = DUMMY_BLOCK_INDEX


@dataclass
class Bucket:
    blocks: List[Block] = field(default_factory=list)


@dataclass
class API:
    value: str = field(default_factory=str)


class DataclassWithBytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if is_dataclass(obj):
            return asdict(obj)
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("utf-8")
        return super().default(obj)
