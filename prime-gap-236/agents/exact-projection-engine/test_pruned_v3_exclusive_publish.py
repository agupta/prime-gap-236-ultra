#!/usr/bin/env python3

import importlib.util
import multiprocessing
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
TARGET = HERE / "d14_grid38_scaled_b_shard_pruned_v3.py"
SPEC = importlib.util.spec_from_file_location("pruned_v3_publish_target", TARGET)
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def competing_publish(path, payload, barrier, queue):
    barrier.wait()
    try:
        RUNNER.publish_exclusive(Path(path), payload)
        queue.put(("published", payload))
    except FileExistsError:
        queue.put(("exists", payload))


class ExclusivePublicationTest(unittest.TestCase):
    def test_intervening_existing_file_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "shard.json"
            target.write_bytes(b"intervening\n")
            with self.assertRaises(FileExistsError):
                RUNNER.publish_exclusive(target, b"new certificate\n")
            self.assertEqual(target.read_bytes(), b"intervening\n")
            self.assertEqual(list(Path(directory).glob(".*.tmp.*")), [])

    def test_two_same_path_publishers_have_exactly_one_winner(self):
        context = multiprocessing.get_context("fork")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "shard.json"
            barrier = context.Barrier(2)
            queue = context.Queue()
            payloads = (b"first exact bytes\n", b"second exact bytes\n")
            processes = [
                context.Process(
                    target=competing_publish,
                    args=(str(target), payload, barrier, queue))
                for payload in payloads]
            for process in processes:
                process.start()
            for process in processes:
                process.join(10)
                self.assertEqual(process.exitcode, 0)
            results = [queue.get(timeout=1), queue.get(timeout=1)]
            self.assertEqual(sorted(status for status, _ in results),
                             ["exists", "published"])
            published = next(payload for status, payload in results
                             if status == "published")
            self.assertEqual(target.read_bytes(), published)
            self.assertIn(published, payloads)
            self.assertEqual(list(Path(directory).glob(".*.tmp.*")), [])


if __name__ == "__main__":
    unittest.main()
