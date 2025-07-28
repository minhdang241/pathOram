from __future__ import annotations

import json
import logging
import math
import os
import random
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Tuple

from common import DUMMY_BLOCK_INDEX, Block, Bucket, DataclassWithBytesEncoder, Log
from storage_engine import StorageEngine

# Configure logging
logger = logging.getLogger(__name__)


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
        num_blocks: int = 1024,
        bucket_size: int = 4,
        storage_engine: StorageEngine = None,
    ):
        self.N = num_blocks
        self.Z = bucket_size
        self.L = math.ceil(math.log2(self.N)) if self.N > 1 else 0
        self.storage_engine = storage_engine
        self.num_leaves = 2**self.L
        self.stash_file = "stash.json"
        if self._load_stash():
            logger.info(f"Loaded existing stash from {self.stash_file}")
        else:
            logger.info(f"Initialized new stash")
            self.position = {
                i: random.randint(0, self.num_leaves - 1) for i in range(self.N)
            }
            self.S: List[Block] = []

    def access(
        self, op: Operation, block_index: int, new_data: Optional[bytes] = None
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
        logs.extend(write_logs)
        # save after each access to avoid losing track of the stash when the server restarts / crashes
        self._save_stash()
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
        except Exception as e:
            logger.warning(f"Error reading path nodes: {e}")
            blocks.extend([Block() for _ in range(self.Z)])
        return blocks, logs

    def _write_nodes(self, leaf_node: int, nodes: List[Bucket]) -> List[Log]:
        root2leaf_path = self._get_path_nodes(leaf_node)
        node2data = {}
        for i, node_index in enumerate(root2leaf_path):
            data = json.dumps(
                nodes[i], indent=4, cls=DataclassWithBytesEncoder
            ).encode()
            node2data[str(node_index)] = data
            logs: List[Log] = self.storage_engine.write_multiple(node2data)
        return logs

    def _save_stash(self) -> bool:
        """
        Save the current stash state to stash.json

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            stash_data = {
                "position_map": self.position,
                "stash_blocks": [
                    {
                        "data": list(block.data) if block.data else [],
                        "index": block.index,
                    }
                    for block in self.S
                ],
                "metadata": {
                    "num_blocks": self.N,
                    "bucket_size": self.Z,
                    "tree_height": self.L,
                    "num_leaves": self.num_leaves,
                },
            }

            with open(self.stash_file, "w") as f:
                json.dump(stash_data, f, indent=2)

            logger.debug(f"Stash saved to {self.stash_file}")
            return True

        except Exception as e:
            logger.error(f"Error saving stash: {e}")
            return False

    def _load_stash(self) -> bool:
        """
        Internal method to load stash from file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.stash_file):
                return False

            with open(self.stash_file, "r") as f:
                stash_data = json.load(f)

            # Load position map
            self.position = stash_data["position_map"]

            # Load stash blocks
            self.S = []
            for block_data in stash_data["stash_blocks"]:
                data_bytes = bytes(block_data["data"]) if block_data["data"] else b""
                self.S.append(Block(data_bytes, block_data["index"]))

            # Verify metadata consistency
            metadata = stash_data["metadata"]
            if (
                metadata["num_blocks"] != self.N
                or metadata["bucket_size"] != self.Z
                or metadata["tree_height"] != self.L
                or metadata["num_leaves"] != self.num_leaves
            ):
                logger.warning("Stash metadata doesn't match current ORAM parameters")
                return False

            return True

        except Exception as e:
            logger.error(f"Error loading stash: {e}")
            return False
