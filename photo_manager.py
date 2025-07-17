from __future__ import annotations

from typing import List, Tuple

from common import Log
from oram import Operation, PathOram
from storage_engine import GCSStorageEngine, LocalStorageEngine


class PhotoManager:
    def __init__(self, is_local: bool = False, use_oram: bool = False):
        self.use_oram = use_oram
        if is_local:
            if use_oram:
                self.storage_engine = LocalStorageEngine()
        else:
            if use_oram:
                self.storage_engine = GCSStorageEngine("<oram-bucket_name>")
            else:
                self.storage_engine = GCSStorageEngine("<normal-bucket_name>")
        self.oram_client = PathOram(self.storage_engine)

    def upload_photo(self, photo_id: str, photo_data: bytes) -> List[Log]:
        if self.use_oram:
            _, logs = self.oram_client.access(Operation.WRITE, photo_id, photo_data)
            return logs
        else:
            log = self.storage_engine.write(photo_id, photo_data)
            return [log]

    def download_photo(self, photo_id: str) -> Tuple[bytes, List[Log]]:
        if self.use_oram:
            data, logs = self.oram_client.access(Operation.READ, photo_id)
            return data, logs
        else:
            data, log = self.storage_engine.read(photo_id)
            return data, [log]
