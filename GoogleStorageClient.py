import os
from google.cloud import storage

from StorageClient import StorageClient

# set key credentials file path
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r'/path/to/credentials/project-name-123456.json'



class GoogleStorageClient(StorageClient):
  def __init__(self):
    self.storageClient = storage.Client()
    

  def read(self, path: str, write_multiple: bool):
    pass

  def write(self, path: str, write_multiple: bool):
    pass