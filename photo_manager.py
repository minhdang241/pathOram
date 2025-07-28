from __future__ import annotations

import os
from typing import List, Tuple

from common import Log
from oram import Operation, PathOram
from storage_engine import GCSStorageEngine, LocalStorageEngine


class PhotoManager:
    def __init__(self, is_local: bool = False):
        if is_local:
            self.storage_engine = LocalStorageEngine("local_storage/unprotected_images")
            self.oram_storage_engine = LocalStorageEngine(
                "local_storage/protected_images"
            )
        else:
            self.storage_engine = GCSStorageEngine("normal-bucket-comp6453")
            self.oram_storage_engine = GCSStorageEngine("oram-bucket")
        self.oram_client = PathOram(
            num_blocks=16, storage_engine=self.oram_storage_engine
        )

    def list_photo_ids(self) -> List[str]:
        # List file names in local_storage/unprotected_images/ (unprotected)
        return self.storage_engine.list_photo_ids()

    def upload_photo(
        self, photo_id: str, photo_data: bytes, use_oram: bool = False
    ) -> List[Log]:
        if use_oram:
            block_id = int(photo_id.split(".")[0])
            _, logs = self.oram_client.access(Operation.WRITE, block_id, photo_data)
            return logs
        else:
            log = self.storage_engine.write(photo_id, photo_data)
            return [log]

    def download_photo(
        self, photo_id: str, use_oram: bool = False
    ) -> Tuple[bytes, List[Log]]:
        if use_oram:
            data, logs = self.oram_client.access(Operation.READ, int(photo_id))
            return data, logs
        else:
            data, log = self.storage_engine.read(photo_id)
            return data, [log]
