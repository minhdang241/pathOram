from __future__ import annotations

import base64
import json
from abc import ABC, abstractmethod
from typing import List, Tuple

from common import Block, Bucket


class StorageEngine(ABC):
    @abstractmethod
    def read(self, path: str, multiple: bool = False) -> Tuple[Bucket, str]:
        """
        Read a file from the storage engine.
        Construct the path to the file from the filename
        For example: path = f"gcs://{filename}"
        Also return a list of paths
        """
        pass

    @abstractmethod
    def write(self, path: str, multiple: bool = False):
        """
        Write a file to the storage engine.
        """
        pass

    def reconstruct_bucket(self, data: bytes) -> Bucket:
        """
        Reconstruct a bucket from the data.
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
