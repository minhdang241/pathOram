from __future__ import annotations

import json
import math
import random
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Tuple

from common import DUMMY_BLOCK_INDEX, Block, Bucket, DataclassWithBytesEncoder, Log
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
    ) -> Tuple[List[int], List[Log]]:
        if block_index < 0 or block_index >= self.N:
            raise ValueError(f"Block index {block_index} out of range")

        # Remap block: Randomly remap the position of block_index to a new random position.
        x = self.position[block_index]
        self.position[block_index] = random.randint(0, self.num_leaves - 1)

        # Read path: Read the path containing block_index
        blocks, logs = self._read_path_nodes(x)
        self.S.extend([block for block in blocks if block.index != DUMMY_BLOCK_INDEX])

        # Update block: If the access is a write, update the data of the block in the stash.
        target_block: Block = Block()
        is_found = False

        for block in self.S:
            if block.index == block_index:
                is_found = True
                target_block = block
                if op == Operation.WRITE:
                    block.data = new_data
                break

        if not is_found and op == Operation.WRITE:
            self.S.append(Block(new_data, block_index))

        """
        Write path: Write the path back and possibly include some additional blocks
        from the stash if they can be placed into the path. Buckets are greedily
        filled with blocks in the stash in the order of their leaf to root, ensuring
        that blocks get pushed as deep down into the tree as possible.
        """
        root2leaf_path = self._get_path_nodes(x)
        nodes = []
        for level in range(self.L, -1, -1):
            evictable_blocks: List[Block] = []
            remained_blocks: List[Block] = []
            for block in self.S:
                new_leaf_node = self.position[block.index]
                new_root2leaf_path = self._get_path_nodes(new_leaf_node)
                if root2leaf_path[level] == new_root2leaf_path[level]:
                    evictable_blocks.append(block)
                else:
                    remained_blocks.append(block)
            evictable_blocks, self.S = (
                evictable_blocks[: self.Z],
                remained_blocks + evictable_blocks[self.Z :],
            )
            evictable_blocks.extend([Block()] * (self.Z - len(evictable_blocks)))
            nodes.append(Bucket(evictable_blocks))
        nodes.reverse()
        write_logs = self._write_nodes(x, nodes)
        logs.append(write_logs)
        return target_block.data, logs

    def _get_path_nodes(self, leaf: int) -> List[int]:
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

    def _read_path_nodes(self, leaf_node: int) -> Tuple[List[Block], List[Log]]:
        """
        Read the nodes from the leaf to the root
        """
        logs: List[Log] = []
        root2leaf_path = self._get_path_nodes(leaf_node)
        blocks = []
        read_paths = []
        for node in root2leaf_path:
            filename = str(node)
            read_paths.append(filename)

        try:
            result: List[Tuple[bytes, Log]] = self.storage_engine.read_multiple(
                read_paths
            )
            for blob, log in result:
                logs.append(log)
                bucket: Bucket = self.storage_engine.reconstruct_bucket(blob)
                blocks.extend(bucket.blocks)
        except Exception:
            blocks.extend([Block() for _ in range(self.Z)])
        return blocks, logs

    def _write_nodes(self, leaf_node: int, nodes: List[Bucket]) -> List[Log]:
        root2leaf_path = self._get_path_nodes(leaf_node)
        node2data = {}
        for i, node_index in enumerate(root2leaf_path):
            data: str = json.dumps(nodes[i], indent=4, cls=DataclassWithBytesEncoder)
            node2data[str(node_index)] = data
            logs: List[Log] = self.storage_engine.write_multiple(data, data)
        return logs
