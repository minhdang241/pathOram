from __future__ import annotations

import logging
import os
import sys
from enum import Enum

from oram import PathOram
from storage_engine import InMemoryStorageEngine


class Operation(Enum):
    READ = "READ"
    WRITE = "WRITE"


class StashSizeSimulator:
    def __init__(
        self, bucket_size: int, num_blocks: int, num_accesses: int, sim_number: int
    ):
        self.bucket_size = bucket_size
        self.num_blocks = num_blocks
        self.num_accesses = num_accesses
        self.sim_number = sim_number
        self.warmup_accesses = 3_000

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
        oram = PathOram(
            num_blocks=self.num_blocks,
            bucket_size=self.bucket_size,
            storage_engine=InMemoryStorageEngine(),
            persist=False,
        )

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
    path_oram_logger = logging.getLogger("oram")
    path_oram_logger.setLevel(logging.CRITICAL)

    # Simulation parameters from the C++ context
    BUCKET_SIZE = 4  # Z
    NUM_BLOCKS = 2**16  # N (e.g., 65536)
    NUM_ACCESSES = 5_000  # Number of accesses to record
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
