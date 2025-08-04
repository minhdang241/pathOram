from __future__ import annotations

import json
import logging
import math
import os
import random
import sys
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Tuple

from common import DUMMY_BLOCK_INDEX, Block, Bucket, DataclassWithBytesEncoder, Log
from storage_engine import LocalStorageEngine, StorageEngine

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
        storage_engine: StorageEngine = LocalStorageEngine(
            "local_storage/unprotected_images"
        ),
    ):
        self.N = num_blocks
        self.Z = bucket_size
        self.L = math.ceil(math.log2(self.N)) if self.N > 1 else 0
        self.num_leaves = 2**self.L
        self.stash_file = "stash.json"  # File to store the stash state
        self.storage_engine = storage_engine
        if self._load_stash():
            new_position = {}
            # convert string keys to int keys since the json format requires the keys as string
            for key, value in self.position.items():
                new_position[int(key)] = value
            self.position = new_position
            logger.info(f"Loaded existing stash from {self.stash_file}")
        else:
            logger.info(f"Initialized new stash")
            self.position = {
                i: random.randint(0, self.num_leaves - 1) for i in range(self.N)
            }
            self.S: Dict[int, Block] = {}

    def access(
        self, op: Operation, block_index: int, new_data: Optional[bytes] = None
    ) -> Tuple[List[int], List[Log]]:
        """
        Accesses a block in the Path ORAM structure, performing either a read or write operation.
        Whenever a block is read from the server, the entire path to the mapped leaf is read into the
        stash, the requested block is remapped to another leaf, and then the path that was just read is
        written back to the server. When the path is written back to the server, additional blocks in the
        stash may be evicted into the path as long as the invariant is preserved and there is remaining space
        in the buckets
        Args:
            op (Operation): The operation to perform (READ or WRITE).
            block_index (int): The index of the block to access.
            new_data (Optional[bytes]): The new data to write if the operation is WRITE.
        Returns:
            Tuple[List[int], List[Log]]:
                - The data of the accessed block (as bytes).
                - A list of logs generated during the access.
        Raises:
            ValueError: If the block_index is out of range.
        """
        if block_index < 0 or block_index >= self.N:
            raise ValueError(f"Block index {block_index} out of range")

        old_leaf = self.position[block_index]
        # Randomly remap the position of block_index to a new random position => make it secure.
        self.position[block_index] = random.randint(0, self.num_leaves - 1)

        # Read all the blocks on the path from the root to the "old" leaf node
        blocks, logs = self._get_blocks(old_leaf)
        valid_blocks = [block for block in blocks if block.index != DUMMY_BLOCK_INDEX]

        # Add non-dummy blocks to the stash
        for block in valid_blocks:
            self.S[block.index] = block

        # Update block if the operation is a write.
        # If the block is already in the stash, simply update it.
        target_block: Block = Block()
        is_found = False

        for block in self.S.values():
            if block.index == block_index:
                is_found = True
                target_block = block
                if op == Operation.WRITE:
                    block.data = new_data
                break

        # If the block is not in the stash, add it.
        if not is_found and op == Operation.WRITE:
            self.S[block_index] = Block(new_data, block_index)

        # Write the path back to the ORAM storage.
        # new_leaf = self.position[block_index]
        target_path = self._get_root_to_leaf_path(
            old_leaf
        )  # Path that will be written back to the ORAM storage
        buckets = []
        # In the loop below, we try to fill the buckets in target path greedily  with blocks in the stash
        # Example:
        # Suppose Z=4 (bucket size), and the target_path is [0, 1, 3, 7] (root to leaf).
        # For each level (from leaf to root), we want to fill the bucket at that node with up to Z blocks from the stash.
        # A block can be placed in a bucket at level l if its assigned leaf shares the same ancestor at level l.
        # We greedily select up to Z such blocks for each bucket, remove them from the stash, and pad with dummy blocks if needed.
        for level in range(self.L, -1, -1):
            # Blocks that can be evicted from the stash
            evictable_blocks: List[Block] = []
            # Blocks that remain in the stash
            remained_blocks: List[Block] = []
            for block in self.S.values():
                curr_path = self._get_root_to_leaf_path(self.position[block.index])
                # If the curr path and target path share the same node at this level, the block is evictable.
                if target_path[level] == curr_path[level]:
                    evictable_blocks.append(block)
                else:
                    remained_blocks.append(block)

            # Update the stash with the remaining blocks
            remained_blocks.extend(evictable_blocks[self.Z :])
            for block in remained_blocks:
                self.S[block.index] = block
            # We only take maximum Z blocks from the stash for this bucket.
            evictable_blocks = evictable_blocks[: self.Z]
            for block in evictable_blocks:
                self.S.pop(block.index, None)  # Remove from stash
            # If we have less than Z blocks, we pad with dummy blocks.
            evictable_blocks.extend([Block()] * (self.Z - len(evictable_blocks)))
            buckets.append(Bucket(evictable_blocks))

        write_logs = self._write_path(old_leaf, buckets)
        logs.extend(write_logs)
        # save after each access to avoid losing track of the stash when the server restarts / crashes
        self._save_stash()
        return target_block.data, logs

    def _get_root_to_leaf_path(self, leaf_id: int) -> List[int]:
        """
        Get the node ids from the root to the leaf
        """
        path_indices = []
        # The number of leaves is 2^L. The first leaf node index starts after all parent nodes.
        leaf_start_index = 2**self.L - 1
        node_index = leaf_start_index + leaf_id

        while node_index >= 0:
            path_indices.append(node_index)
            if node_index == 0:  # Root node
                break
            # Move to the parent node
            node_index = (node_index - 1) // 2

        return path_indices[::-1]  # Return from root to leaf

    def _get_blocks(self, leaf: int) -> Tuple[List[Block], List[Log]]:
        """
        Get all blocks on the path from the root to the leaf node.
        """
        logs: List[Log] = []
        root2leaf_path = self._get_root_to_leaf_path(leaf)
        blocks = []
        read_paths = []
        for node in root2leaf_path:
            filename = str(node)
            read_paths.append(filename)

            results: List[Tuple[bytes, Log]] = self.storage_engine.read_multiple(
                read_paths
            )
            for blob, log in results:
                logs.append(log)
                try:
                    bucket: Bucket = self.storage_engine.reconstruct_bucket(blob)
                    blocks.extend(bucket.blocks)
                except Exception as e:
                    logger.error(f"Error reading path nodes: {e}")
                    blocks.extend([Block() for _ in range(self.Z)])
        return blocks, logs

    def _write_path(self, leaf: int, buckets: List[Bucket]) -> List[Log]:
        """
        Write the path back to the storage.
        """
        buckets.reverse()
        root2leaf_path = self._get_root_to_leaf_path(leaf)
        node2data = {}
        for i, node_index in enumerate(root2leaf_path):
            data = json.dumps(
                buckets[i], indent=4, cls=DataclassWithBytesEncoder
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
                    for block in self.S.values()
                ],
                "metadata": {
                    "num_blocks": self.N,
                    "bucket_size": self.Z,
                    "tree_height": self.L,
                    "num_leaves": self.num_leaves,
                },
            }

            with open(self.stash_file, "w") as f:
                json.dump(stash_data, f, separators=(",", ":"))

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
            self.S = {}
            for block_data in stash_data["stash_blocks"]:
                data_bytes = bytes(block_data["data"]) if block_data["data"] else b""
                self.S[block_data["index"]] = Block(data_bytes, block_data["index"])

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


class StashSizeSimulator:
    def __init__(
        self, bucket_size: int, num_blocks: int, num_accesses: int, sim_number: int
    ):
        self.bucket_size = bucket_size
        self.num_blocks = num_blocks
        self.num_accesses = num_accesses
        self.sim_number = sim_number
        self.warmup_accesses = 3_000_000

    def _sample_data(self, i: int) -> str:
        """
        Generates sample data for write operations.
        In Python, this can be any object. A simple string is used here.

        :param i: An integer to make the data unique.
        :return: Sample data.
        """
        return f"block_data_{i}"

    def _write_simulation_results(self, ccdf_counts: list[int]):
        """
        Writes the simulation results to a file.
        The output is a CSV with two columns: stash_size, count.
        The count represents the number of times the stash size was >= stash_size.

        :param ccdf_counts: A list where index `k` holds the number of times
                            the stash size was `k` or greater.
        """
        # Ensure the output directory exists
        output_dir = "simulations"
        os.makedirs(output_dir, exist_ok=True)

        filename = os.path.join(output_dir, f"simulation{self.sim_number}.txt")
        print(f"Writing results to {filename}")

        with open(filename, "w") as f:
            for stash_size, count in enumerate(ccdf_counts):
                # Stop if counts become zero, as in the C++ version
                if count == 0 and stash_size > 0:  # Continue if the first element is 0
                    break
                f.write(f"{stash_size},{count}\n")

        print("Finished writing results.")

    def run_simulation(self):
        """
        Executes the full ORAM stash size simulation.
        """
        # 1. Initialize the ORAM
        oram = PathOram(num_blocks=self.num_blocks, bucket_size=self.bucket_size)

        # 2. Warm-up phase: Perform writes to populate the ORAM
        print(f"Warming up the stash with {self.warmup_accesses:,} writes...")
        for i in range(self.warmup_accesses):
            block_id = i % self.num_blocks
            data = self._sample_data(i)
            oram.access(Operation.WRITE, block_id, data)

        print("Stash warmed up. Starting to record results.")

        # 3. Recording phase: Perform reads and record stash sizes
        # pmf_counts[k] will store the number of times the stash size was exactly k.
        # We size it generously. The max stash size is theoretically num_blocks.
        pmf_counts = [0] * (self.num_blocks + 1)

        for i in range(self.num_accesses):
            block_id = i % self.num_blocks
            oram.access(Operation.READ, block_id, None)

            # Get the stash size. We assume the ORAM object provides this.
            recorded_size = oram.get_stash_size()

            if recorded_size < len(pmf_counts):
                pmf_counts[recorded_size] += 1
            else:
                # Handle unexpectedly large stash sizes if necessary
                print(
                    f"Warning: Stash size {recorded_size} exceeds recording array size.",
                    file=sys.stderr,
                )

            if (i + 1) % 1_000_000 == 0:
                print(
                    f"Accessed {i + 1:,}/{self.num_accesses:,}. Current stash size = {recorded_size}"
                )

        # 4. Post-processing: Convert PMF to CCDF
        # The C++ code calculates the Complementary Cumulative Distribution Function (CCDF).
        # ccdf_counts[k] = sum(pmf_counts[j] for j >= k)
        print("Calculating final distribution...")

        # Initialize CCDF array
        ccdf_counts = [0] * len(pmf_counts)

        # Calculate it efficiently by iterating backwards
        if pmf_counts:
            ccdf_counts[-1] = pmf_counts[-1]
            for i in range(len(pmf_counts) - 2, -1, -1):
                ccdf_counts[i] = pmf_counts[i] + ccdf_counts[i + 1]

        # 5. Write the final results to a file
        self._write_simulation_results(ccdf_counts)


# Example of how to run the simulator
if __name__ == "__main__":
    # Simulation parameters from the C++ context
    BUCKET_SIZE = 4  # Z
    NUM_BLOCKS = 2**16  # N (e.g., 65536)
    NUM_ACCESSES = 5_000_000  # Number of accesses to record
    SIM_NUMBER = 1  # Simulation run ID

    print("--- Starting Stash Size Simulation ---")
    simulator = StashSizeSimulator(
        bucket_size=BUCKET_SIZE,
        num_blocks=NUM_BLOCKS,
        num_accesses=NUM_ACCESSES,
        sim_number=SIM_NUMBER,
    )

    simulator.run_simulation()
    print("--- Simulation complete. ---")
