from __future__ import annotations

import base64
import json
import os
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import List

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DUMMY_BLOCK_INDEX = -1


@dataclass
class Block:
    data: bytes = field(default_factory=bytes)
    index: int = DUMMY_BLOCK_INDEX
    name: str = ""


@dataclass
class Bucket:
    blocks: List[Block] = field(default_factory=list)


@dataclass
class Log:
    value: str = field(default_factory=str)


class DataclassWithBytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if is_dataclass(obj):
            return asdict(obj)
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("utf-8")
        return super().default(obj)


class EncryptionEngine:
    def __init__(self, key: bytes):
        self.key = key
        self.aesgcm = AESGCM(self.key)

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    def decrypt(self, ciphertext: bytes) -> bytes:
        nonce = ciphertext[:12]
        encrypted_data = ciphertext[12:]
        return self.aesgcm.decrypt(nonce, encrypted_data, None)
