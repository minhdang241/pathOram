from __future__ import annotations

import json
import logging
import os
from typing import List, Tuple

from common import Block, Log
from oram import Operation, PathOram
from storage_engine import GCSStorageEngine, LocalStorageEngine

logger = logging.getLogger(__name__)

MAX_FILES = 8


class PhotoManager:
    def __init__(self, is_local: bool = False):
        if is_local:
            self.storage_engine = LocalStorageEngine("local_storage/unprotected_images")
            self.oram_storage_engine = LocalStorageEngine(
                "local_storage/protected_images"
            )
            # load name2blockid from file
            self.json_file = "name2blockid.json"
            # try:
            #     with open("name2blockid.json", "r") as f:
            #         self.name2blockid = json.load(f)
            # except:
            #     self.name2blockid = {}
        else:
            self.json_file = "oramname2blockid.json"
            self.storage_engine = GCSStorageEngine("normal-bucket-comp6453")
            self.oram_storage_engine = GCSStorageEngine("oram-bucket")
            self.oram_client = PathOram(
                num_blocks=MAX_FILES, storage_engine=self.oram_storage_engine
            )

        try:
            with open(self.json_file, "r") as f:
                self.name2blockid = json.load(f)
        except:
            self.name2blockid = {}
        self.file_counter = len(self.name2blockid)

    def list_photo_ids(self, use_oram: bool = False) -> List[str]:
        if use_oram:
            """
            Little hack here, instead of extracting the name from all the files from the storage,
            we use the name2blockid.json file to get the name of the files. :)
            """
            return self.name2blockid.keys()
        else:
            return self.storage_engine.list_photo_ids()

    def upload_photo(
        self, photo_id: str, photo_data: bytes, use_oram: bool = False
    ) -> List[Log]:
        if use_oram:
            if self.file_counter >= MAX_FILES:
                logger.error(f"Maximum number of files reached: {MAX_FILES}")
                return []
            block_id = self.file_counter
            _, logs = self.oram_client.access(Operation.WRITE, block_id, photo_data)
            self.file_counter += 1
            self.name2blockid[photo_id] = block_id

            # save name2blockid to file
            with open(self.json_file, "w") as f:
                json.dump(self.name2blockid, f)
            return logs
        else:
            log = self.storage_engine.write(photo_id, photo_data)
            return [log]

    def download_photo(
        self, photo_id: str, use_oram: bool = False
    ) -> Tuple[bytes, List[Log]]:
        if use_oram:
            block_id = self.name2blockid[photo_id]
            data, logs = self.oram_client.access(Operation.READ, block_id)
            return data, logs
        else:
            data, log = self.storage_engine.read(photo_id)
            return data, [log]
