#!/usr/bin/env python3
"""Hostile mutation tests for the independent six-core pair preflight."""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
AUDITOR = HERE/"audit_core6_pair_tier.py"
FULL = HERE/"results/c10_D12_sparse_coordinate_scan_manifest.json"
PAIR = PROJECT/"agents/structural-basis/results/c10_D12_sparse_core6_pair_manifest_v2.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(pair, output, expected=None):
    return subprocess.run([sys.executable, str(AUDITOR),
        "--coordinate-manifest", str(FULL), "--pair-manifest", str(pair),
        "--expect-pair-manifest-sha256", expected or sha(pair),
        "--output", str(output)], stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2)+"\n")


def test_frozen_preflight_and_existing_output():
    with tempfile.TemporaryDirectory(prefix="pair-audit-pass.") as directory:
        output = Path(directory)/"audit.json"
        result = run(PAIR, output)
        if result.returncode != 0:
            raise AssertionError("frozen preflight rejected")
        value = json.loads(output.read_bytes())
        if value["status"] != "AUDIT PASS" or value["pair_count"] != 15 or any(
                x["outputs_present_at_audit"] for x in value["pairs"]):
            raise AssertionError("preflight verdict/count")
        if run(PAIR, output).returncode == 0:
            raise AssertionError("existing output overwritten")


def mutated_fixture(directory, mutation):
    directory = Path(directory)
    manifest = json.loads(PAIR.read_bytes())
    record = manifest["pairs"][0]
    source = Path(record["input_path"])
    value = json.loads(source.read_bytes())
    mutation(manifest, record, value, directory)
    if value is not None:
        pair_input = directory/"pair.json"; write_json(pair_input, value)
        record["input_path"] = str(pair_input); record["input_sha256"] = sha(pair_input)
    manifest_path = directory/"manifest.json"; write_json(manifest_path, manifest)
    return manifest_path


def must_reject(mutation, name):
    with tempfile.TemporaryDirectory(prefix=f"pair-audit-{name}.") as directory:
        manifest = mutated_fixture(directory, mutation)
        output = Path(directory)/"output.json"
        if run(manifest, output).returncode == 0 or output.exists():
            raise AssertionError(f"mutation accepted: {name}")


def test_identity_count_polarization_mutations():
    def coefficient(manifest, record, value, directory):
        value["rational_vector"][0] = "2"
    must_reject(coefficient, "coefficient")

    def count(manifest, record, value, directory):
        value["expected_grouped_counts"]["i_orbit_groups"] += 1
        record["expected_grouped_counts"]["i_orbit_groups"] += 1
    must_reject(count, "count")

    def polarization(manifest, record, value, directory):
        value["polarization"]["Aij"] = "(A_sum-Aii-Ajj)"
    must_reject(polarization, "polarization")


def test_alias_output_presence_and_provenance_mutations():
    def alias(manifest, record, value, directory):
        record["i_stage_path"] = record["input_path"]
    must_reject(alias, "path-alias")

    def present(manifest, record, value, directory):
        marker = directory/"unexpected-result.json"; marker.write_text("{}\n")
        record["result_path"] = str(marker)
    must_reject(present, "preexisting-result")

    def provenance(manifest, record, value, directory):
        manifest["provenance"]["builder_sha256"] = "0"*64
        value["provenance"]["builder_sha256"] = "0"*64
    must_reject(provenance, "builder-provenance")


def main():
    tests = [test_frozen_preflight_and_existing_output,
             test_identity_count_polarization_mutations,
             test_alias_output_presence_and_provenance_mutations]
    for test in tests:
        test(); print("PASS", test.__name__)
    print("PASS all", len(tests), "tests")
    print("auditor_sha256", sha(AUDITOR))


if __name__ == "__main__":
    main()
