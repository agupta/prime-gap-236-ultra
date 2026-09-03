#!/usr/bin/env python3
"""Executable counterexamples for frozen R15 assembler 290dc32b... ."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
ASSEMBLER = REPO / "agents/small-delta-frontier/assemble_piecewise_d16_R15.py"
I_SHA = "cb84d4eb6d24c7be2315b8195b8e0c1a6a9bc52e68e4e5f6a656ea41252e667c"
J_SHA = "5086a4a381d301ae3a5b321f5e5afba685b677d6851694ef555f6ec76d7fdc58"
ASSEMBLER_SHA = \
    "290dc32bf233083ffa52162a4176e0618d6a1fb932d009ca73740d349fe3a363"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) +
            "\n").encode("ascii")


def write(path: Path, value) -> str:
    data = encoded(value)
    path.write_bytes(data)
    return sha(data)


def fabricated_inputs(directory: Path):
    # Deliberately omit source_hashes and almost every support parameter.  The
    # numeric fields are arbitrary, yet the frozen assembler accepts them.
    i_path = directory / "fabricated_i.json"
    i_hash = write(i_path, {
        "status": "piecewise-capped-volume-ramp-D16-Decimal-stage",
        "script_sha256": I_SHA,
        "rigorous": False,
        "theorem_ready": False,
        "decimal_dps": 80,
        "complete_stage": True,
        "cost_probe_h": None,
        "i_stage": {"total_count": 15, "shell_difference": "1"},
        "j_stage": None,
    })
    j_specs = []
    for common, value in ((14, "2"), (15, "3")):
        path = directory / f"fabricated_j{common}.json"
        digest = write(path, {
            "status": "piecewise-D16-R15-specialized-Decimal-J-stage",
            "script_sha256": J_SHA,
            "target_driver_sha256": I_SHA,
            "rigorous": False,
            "theorem_ready": False,
            "decimal_dps": 80,
            "selected_h": None,
            "complete_common_count": True,
            "parameters": {
                "target_total_count": 15, "common_count": common,
            },
            "raw_J_bilinear": {
                "fh": value, "fl": "0", "hh": value,
                "hl": "0", "ll": "0",
            },
        })
        j_specs.append({"path": str(path), "sha256": digest})
    manifest = directory / "manifest.json"
    write(manifest, {
        "format": "piecewise-D16-R15-stage-manifest-v1",
        "decimal_dps": 80,
        "i_stage": {"path": str(i_path), "sha256": i_hash},
        "j_stages": j_specs,
    })
    return manifest


class FrozenAssemblerForgery(unittest.TestCase):
    def setUp(self):
        self.assertEqual(sha(ASSEMBLER.read_bytes()), ASSEMBLER_SHA)

    def invoke(self, manifest: Path, output: Path):
        return subprocess.run(
            [sys.executable, str(ASSEMBLER), str(manifest),
             "--output", str(output)], cwd=REPO, text=True,
            capture_output=True, check=False)

    def test_fabricated_unprovenance_stages_are_accepted(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            manifest = fabricated_inputs(directory)
            output = directory / "forged_result.json"
            result = self.invoke(manifest, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            produced = json.loads(output.read_bytes())
            self.assertEqual(
                produced["status"],
                "piecewise-D16-inner-plus-R15-Decimal-discovery")
            self.assertEqual(produced["I_matrix"][1][1], "1")

    def test_dangling_output_symlink_is_followed(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            manifest = fabricated_inputs(directory)
            destination = directory / "created_through_symlink.json"
            output = directory / "dangling_output.json"
            os.symlink(destination.name, output)
            self.assertFalse(output.exists())
            result = self.invoke(manifest, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(destination.is_file())


if __name__ == "__main__":
    unittest.main()
