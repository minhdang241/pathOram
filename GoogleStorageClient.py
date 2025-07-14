import os
from google.cloud import storage

from StorageClient import StorageClient

# set key credentials file path
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r'/path/to/credentials/project-name-123456.json'



class GoogleStorageClient(StorageClient):
  def __init__(self):
    self.storageClient = storage.Client()
    

  def read(self, sourceFileName: str, downloadFileName: str, writeMultiple: bool):
    pass

  def write(self, sourceFileName: str, uploadFileName: str, writeMultiple: bool):
    pass