from __future__ import annotations

import json
import math
import random
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Tuple

from common import API, DUMMY_BLOCK_INDEX, Block, Bucket, DataclassWithBytesEncoder
from storage_engine import StorageEngine


class Operation(Enum):
    READ = "READ"
    WRITE = "WRITE"


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


class PathOram(OramInterface):
    """
    N: Number of blocks
    L: Height of binary tree
    Z: Bucket size
    S: client's local stash
    """

    def __init__(
        self,
        num_blocks: int,
        bucket_size: int = 4,
        storage_engine: StorageEngine = None,
    ):
        self.N = num_blocks
        self.Z = bucket_size
        self.L = math.ceil(math.log2(self.N)) if self.N > 1 else 0
        self.storage_engine = storage_engine
        self.num_leaves = 2**self.L
        # a map from the block to the leaf
        self.position = {
            i: random.randint(0, self.num_leaves - 1) for i in range(self.N)
        }
        self.S: List[Block] = []

    def access(
        self, op: Operation, block_index: int, new_data: bytes
    ) -> Tuple[List[int], List[API]]:
        if block_index < 0 or block_index >= self.N:
            raise ValueError(f"Block index {block_index} out of range")

        # Remap block to a new random path
        leaf_node = self.position[block_index]
        self.position[block_index] = random.randint(0, self.num_leaves - 1)

        # Read the path and add to the stash
        blocks, apis = self._read_l2r_nodes(leaf_node)
        self.S.extend([block for block in blocks if block.index != DUMMY_BLOCK_INDEX])

        # Find block in stash
        target_block: Block = None
        is_found = False

        for i, block in enumerate(self.S):
            if block.index == block_index:
                is_found = True
                target_block = block
                if op == Operation.WRITE:
                    self.S[i] = Block(new_data, block_index)
                break

        if not is_found and op == Operation.WRITE:
            self.S.append(Block(new_data, block_index))

        # Remap the position
        leaf2root_path = self._get_l2r_nids(leaf_node)
        for level in range(self.L, -1, -1):
            stash_prime: List[Block] = []
            remain: List[Block] = []
            for block in self.S:
                new_leaf_node = self.position[block.index]
                new_leaf2root_path = self._get_l2r_nids(new_leaf_node)
                if leaf2root_path[level] == new_leaf2root_path[level]:
                    stash_prime.append(block)
                else:
                    remain.append(block)
            tmp = stash_prime[: self.Z]
            self.S = remain + stash_prime[self.Z :]
            stash_prime = tmp
            stash_prime.extend([Block()] * (self.Z - len(stash_prime)))
            api = self._write_node(leaf_node, Bucket(stash_prime))
            apis.extend(api)
        return target_block.data, apis

    def _get_l2r_nids(self, leaf: int) -> List[int]:
        """
        Get the node ids from the leaf to the root
        """
        path = []
        node_index = 0
        for level in range(self.L + 1):
            path.append(node_index)
            # Determine next node based on the bits of the leaf_id
            if level < self.L:
                bit = (leaf >> (self.L - 1 - level)) & 1
                if bit == 0:
                    node_index = 2 * node_index + 1
                else:
                    node_index = 2 * node_index + 2
        return path

    def _read_l2r_nodes(self, leaf_node: int) -> Tuple[List[Block], List[API]]:
        """
        Read the nodes from the leaf to the root
        """
        apis: List[API] = []
        leaf2root_path = self._get_l2r_nids(leaf_node)
        blocks = []
        for node in leaf2root_path:
            try:
                data, api = self.storage_engine.read(node)
                apis.append(api)
                bucket: Bucket = self.storage_engine.reconstruct_bucket(data)
                blocks.extend(bucket.blocks)
            except Exception:
                blocks.extend([Block() for _ in range(self.Z)])
        return blocks, apis

    def _write_node(self, node_id: int, bucket: Bucket) -> API:
        data = json.dumps(bucket, indent=4, cls=DataclassWithBytesEncoder)
        api: API = self.storage_engine.write(node_id, data)
        return api
