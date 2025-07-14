from abc import ABC, abstractmethod

class StorageClient(ABC):
  @abstractmethod
  def read(self, path: str, write_multiple: bool):
    pass

  @abstractmethod
  def write(self, path: str, write_multiple: bool):
    pass