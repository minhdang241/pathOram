from __future__ import annotations

from typing import List, Tuple

from common import API
from oram import Operation, PathOram
from storage_engine import LocalStorageEngine


class PhotoManager:
    def __init__(self, is_local: bool = False):
        if is_local:
            self.storage_engine = LocalStorageEngine()
        self.oram_client = PathOram(self.storage_engine)

    def upload_photo(
        self, photo_id: str, photo_data: bytes, use_oram: bool = False
    ) -> List[API]:
        if use_oram:
            _, apis = self.oram_client.access(Operation.WRITE, photo_id, photo_data)
            return apis
        else:
            api = self.storage_engine.write(photo_id, photo_data)
            return [api]

    def download_photo(
        self, photo_id: str, use_oram: bool = False
    ) -> Tuple[bytes, List[API]]:
        if use_oram:
            data, apis = self.oram_client.access(Operation.READ, photo_id)
            return data, apis
        else:
            data, api = self.storage_engine.read(photo_id)
            return data, [api]
