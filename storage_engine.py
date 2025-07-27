from __future__ import annotations

import base64
import concurrent
import json
import os
import io
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from common import Block, Bucket, EncryptionEngine, Log

from google.cloud import storage


class StorageEngine(ABC):
    @abstractmethod
    def read(self, filename: str) -> Tuple[bytes, Log]:
        pass

    def read_multiple(self, filenames: List[str]) -> List[Tuple[bytes, Log]]:
        results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future2filename = {
                executor.submit(self.read, filename): filename for filename in filenames
            }
            for future in concurrent.futures.as_completed(future2filename):
                try:
                    results.append(future.result())
                except Exception as e:
                    filename = future2filename[future]
                    full_path = os.path.join(self.directory, filename)
                    results.append(
                        (b"", Log(value=f"Error reading {full_path}: {str(e)}"))
                    )
        return results

    @abstractmethod
    def write(self, filename: str, data: str) -> Log:
        """
        Write a file to the storage engine.
        """
        pass

    def write_multiple(self, data: Dict[str, str]) -> List[Log]:
        logs = []
        for filename, file_data in data.items():
            logs.append(self.write(filename, file_data))
        return logs

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
    def __init__(self, bucket: str):
        self.directory = bucket
        key = AESGCM.generate_key(bit_length=128)
        self.crypto_engine = EncryptionEngine(key)
        os.makedirs(self.directory, exist_ok=True)
        print(f"INFO: LocalStorageEngine initialized for directory: '{self.directory}'")

    def read(self, filename: str) -> Tuple[bytes, Log]:
        full_path = os.path.join(self.directory, filename)
        try:
            with open(full_path, "rb") as file:
                ciphertext_bytes = file.read()
            plaintext_bytes = ciphertext_bytes
            # plaintext_bytes = self.crypto_engine.decrypt(ciphertext_bytes)
            return plaintext_bytes, Log(value=f"GET /{full_path}")
        except Exception as e:
            return b"", Log(value=f"Error reading {full_path}: {str(e)}")

    def write(self, filename: str, data: bytes) -> Log:
        full_path = os.path.join(self.directory, filename)
        try:
            # TODO: Enable the encryption
            # ciphertext_bytes = self.crypto_engine.encrypt(plaintext_bytes)
            ciphertext_bytes = data
            with open(full_path, "wb") as file:
                file.write(ciphertext_bytes)
            return Log(value=f"PUT /{full_path}")
        except Exception as e:
            return Log(value=f"Error writing to {full_path}: {str(e)}")



class GCSStorageEngine(StorageEngine):
    def __init__(self, bucket: str):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r'comp6453-credentials.json'
        self.storageClient = storage.Client()
        self.bucket = self.storageClient.bucket(bucket)
        key = AESGCM.generate_key(bit_length=128)
        self.crypto_engine = EncryptionEngine(key)
        print(f"INFO: GCSStorageEngine initialized for bucket: '{bucket}'")

    def read(self, filename: str) -> Tuple[bytes, Log]:
        try:
            blob = self.bucket.blob(filename)
            ciphertext_bytes = blob.download_as_bytes()
            plaintext_bytes = ciphertext_bytes
            # plaintext_bytes = self.crypto_engine.decrypt(ciphertext_bytes)
            return plaintext_bytes, Log(value=f"GET /{filename}")
        except Exception as e:
            return b"", Log(value=f"Error reading {filename}: {str(e)}")

    def write(self, filename: str, data: bytes) -> Log:
        try:
            plaintext_bytes = data
            blob = self.bucket.blob(filename)
            # TODO: Enable the encryption
            # ciphertext_bytes = self.crypto_engine.encrypt(plaintext_bytes)
            ciphertext_bytes = plaintext_bytes
            blob.upload_from_string(ciphertext_bytes)
            return Log(value=f"PUT /{filename}")
        except Exception as e:
            return Log(value=f"Error writing to {filename}: {str(e)}")
