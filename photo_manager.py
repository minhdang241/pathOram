from __future__ import annotations

from typing import List, Tuple

from common import Log
from oram import Operation, PathOram
from storage_engine import GCSStorageEngine, LocalStorageEngine
import os


class PhotoManager:
    def __init__(self, is_local: bool = False):
        if is_local:
            self.storage_engine = LocalStorageEngine("local_storage/unprotected_images")
            self.oram_storage_engine = LocalStorageEngine("local_storage/oram")
        else:
            self.storage_engine = GCSStorageEngine("normal-bucket-comp6453")
            self.oram_storage_engine = GCSStorageEngine("oram-bucket")
        self.oram_client = PathOram(
            num_blocks=16, storage_engine=self.oram_storage_engine
        )

    def list_unprotected_photo_ids(self) -> List[str]:
        # List file names in local_storage/normal/ (unprotected)
        return sorted([
            f for f in os.listdir(self.storage_engine.directory)
            if os.path.isfile(os.path.join(self.storage_engine.directory, f))
        ])

    def upload_photo(
        self, photo_id: str, photo_data: bytes, use_oram: bool = False
    ) -> List[Log]:
        if use_oram:
            _, logs = self.oram_client.access(Operation.WRITE, photo_id, photo_data)
            return logs
        else:
            log = self.storage_engine.write(photo_id, photo_data)
            return [log]

    def download_photo(
        self, photo_id: str, use_oram: bool = False
    ) -> Tuple[bytes, List[Log]]:
        if use_oram:
            data, logs = self.oram_client.access(Operation.READ, int(photo_id))
            print(data, logs)
            return data, logs
        else:
            data, log = self.storage_engine.read(photo_id)
            return data, [log]
