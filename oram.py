from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Union


class Operation(Enum):
    READ = "READ"
    WRITE = "WRITE"


class Block:
    def __init__(self, data: Optional[List[int]], index: int, leaf_id: int):
        self.data = data if data is not None else []
        self.index = index
        self.leaf_id = leaf_id


class OramInterface(ABC):
    """
    Abstract base class for ORAM (Oblivious RAM) implementations.
    Defines the interface that all ORAM implementations must follow.
    """

    @abstractmethod
    def access(
        self, op: Operation, block_index: int, new_data: Optional[List[int]] = None
    ) -> Optional[List[int]]:
        pass

    @abstractmethod
    def P(self, leaf: int, level: int) -> int:
        pass

    @abstractmethod
    def get_position_map(self) -> List[int]:
        pass

    @abstractmethod
    def get_stash(self) -> List[Block]:
        pass

    @abstractmethod
    def get_stash_size(self) -> int:
        pass

    @abstractmethod
    def get_num_leaves(self) -> int:
        pass

    @abstractmethod
    def get_num_levels(self) -> int:
        pass

    @abstractmethod
    def get_num_blocks(self) -> int:
        pass

    @abstractmethod
    def get_num_buckets(self) -> int:
        pass
