#!/usr/bin/env python3
"""Fail-closed tests for the dormant H6 full-vector line emitter."""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
EMITTER = HERE / "emit_h6_line_candidate.py"
MANIFEST = HERE / "results/c10_D12_h6_scalar_line_manifest.json"
DIRECTION = HERE / "results/h6_scalar_line/c10_D12_h6_direction_11.json"
SOURCE = PROJECT / "agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json"
BANDS = PROJECT / "agents/structural-basis/results/c10_D12_degree_bands.json"
RECOVERY = PROJECT / "agents/structural-basis/results/c10_D12_band_sparse_gradient_recovered_v2.json"


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def command(output, step):
    return [sys.executable, str(EMITTER), "--manifest", str(MANIFEST),
            "--direction", str(DIRECTION), "--source", str(SOURCE),
            "--bands", str(BANDS), "--recovery", str(RECOVERY),
            "--s", step, "--output", str(output)]


def test_valid_complete_vector_and_canonical_parser():
    with tempfile.TemporaryDirectory(prefix="emit-h6-test.") as directory:
        output = Path(directory)/"candidate.json"
        subprocess.run(command(output, "1/20"), check=True,
                       stdout=subprocess.DEVNULL)
        value = json.loads(output.read_bytes())
        require(value["k"] == 48 and value["basis_dimension"] == 272 and
                len(value["basis"]) == len(value["rational_vector"]) == 272 and
                value["line"]["coordinate_s"] == "1/20" and
                value["line"]["changed_expanded_coordinate_count"] == 11 and
                value["fresh_exact_dyadic_evaluation_required"] is True,
                "complete fixed vector schema")
        for bad in ("2/40", "0.05", "+1/20", "0"):
            bad_output = Path(directory)/("bad-"+hashlib.sha256(bad.encode()).hexdigest()+".json")
            result = subprocess.run(command(bad_output, bad),
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            require(result.returncode != 0 and not bad_output.exists(),
                    f"malformed s accepted: {bad}")
        result = subprocess.run(command(output, "1/10"),
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        require(result.returncode != 0, "O_EXCL existing output gate")


def test_input_alias_rejected_without_mutation():
    before = MANIFEST.read_bytes()
    result = subprocess.run(command(MANIFEST, "1/20"),
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    require(result.returncode != 0 and MANIFEST.read_bytes() == before,
            "trusted input alias was not fail-closed")


def load_module():
    spec = importlib.util.spec_from_file_location("h6_emitter_test", EMITTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_postwrite_input_and_inode_races():
    module = load_module()
    payload = b'{"status":"test"}\n'
    with tempfile.TemporaryDirectory(prefix="emit-h6-race.") as directory:
        directory = Path(directory)
        trusted_path = directory/"trusted"
        trusted_path.write_bytes(b"trusted")
        output = directory/"output"
        def mutate_trusted(path, descriptor):
            trusted_path.write_bytes(b"changed")
        try:
            module.publish_owned(output, payload, {trusted_path: b"trusted"},
                                 mutate_trusted)
        except module.EmitError:
            pass
        else:
            raise AssertionError("postwrite trusted mutation accepted")
        require(b"REJECTED" in output.read_bytes(), "owned rejection marker")

        foreign_output = directory/"foreign-output"
        foreign = b"FOREIGN INODE MUST SURVIVE"
        def swap_inode(path, descriptor):
            os.unlink(path)
            path.write_bytes(foreign)
        try:
            module.publish_owned(foreign_output, payload, {}, swap_inode)
        except module.EmitError:
            pass
        else:
            raise AssertionError("output inode replacement accepted")
        require(foreign_output.read_bytes() == foreign,
                "foreign replacement inode was modified")


def main():
    tests = [test_valid_complete_vector_and_canonical_parser,
             test_input_alias_rejected_without_mutation,
             test_postwrite_input_and_inode_races]
    for test in tests:
        test(); print("PASS", test.__name__)
    print("PASS all", len(tests), "tests")


if __name__ == "__main__":
    main()
