from abc import ABC, abstractmethod

class StorageClient(ABC):
  @abstractmethod
  def read(self, sourceFileName: str, downloadFileName: str, writeMultiple: bool):
    pass

  @abstractmethod
  def write(self, sourceFileName: str, uploadFileName: str, writeMultiple: bool):
    pass