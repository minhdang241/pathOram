import os
from google.cloud import storage

from storage_engine import StorageEngineClient


class GoogleStorageClient(StorageEngineClient):
  def __init__(self):
    self.storageClient = storage.Client()
    self.bucket = self.storageClient.bucket("oram-bucket")
    

  def checkIfFileExists(self, blob):
    if not blob.exists():
      raise FileNotFoundError

  def read(self, path: str, multiple: bool):
    if multiple:
      pass
    else:
      blob = self.bucket.blob(path)
      self.checkIfFileExists(blob)
      contents = blob.download_as_bytes()
      return contents
      


  def write(self, sourceFileName: str, uploadFileName: str, writeMultiple: bool):
    pass