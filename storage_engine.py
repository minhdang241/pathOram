from abc import ABC, abstractmethod

class StorageEngineClient(ABC):
  @abstractmethod
  def read(self, path: str, multiple: bool = False):
    """
    Read a file from the storage engine.
    """
    pass

  @abstractmethod
  def write(self, path: str, multiple: bool = False):
    """
    Write a file to the storage engine.
    """
    pass