from __future__ import annotations

import base64
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

from common import Block, Bucket, Log


class StorageEngine(ABC):
    @abstractmethod
    def read(self, filename: str) -> Tuple[bytes, Log]:
        """
        Read a file from the storage engine.
        Construct the path to the file from the filename
        For example: path = f"gcs://{filename}"
        Also return a list of paths
        """
        pass

    def read_multiple(self, filenames: List[str]) -> List[Tuple[bytes, Log]]:
        pass

    @abstractmethod
    def write(self, filename: str, data: bytes) -> Log:
        """
        Write a file to the storage engine.
        """
        pass

    @abstractmethod
    def write_multiple(self, data: Dict[str, bytes]) -> List[Log]:
        """
        Write multiple files to the storage engine.
        """
        pass

    def reconstruct_bucket(self, data: bytes) -> Bucket:
        """
        Reconstruct a node (Bucket) from the data.
        """
        json_string = data.decode("utf-8")  # convert binary to string
        data_dict = json.loads(json_string)
        blocks: List[Block] = []
        for block_dict in data_dict.get("blocks"):
            base64_data_string = block_dict.get("data", "")
            reconstructed_data = base64.b64decode(base64_data_string.encode("utf-8"))
            block = Block(reconstructed_data, block_dict.get("index"))
            blocks.append(block)
        return Bucket(blocks)


class LocalStorageEngine(StorageEngine):
    def __init__(self):
        pass

    def read(self, filename: str) -> Tuple[bytes, Log]:
        pass

    def read_multiple(self, filenames: List[str]) -> List[Tuple[bytes, Log]]:
        pass

    def write(self, filename: str) -> Log:
        pass

    def write_multiple(self, data: Dict[str, bytes]) -> List[Log]:
        pass


class GCSStorageEngine(StorageEngine):
    def __init__(self, bucket: str):
        self.bucket = bucket
        pass

    def read(self, filename: str) -> Tuple[bytes, Log]:
        pass

    def write(self, filename: str) -> Log:
        pass

    def write_multiple(self, data: Dict[str, bytes]) -> List[Log]:
        pass
