#!/usr/bin/env python3
"""Mutation tests for the independent strict D14 A aggregate auditor."""

from __future__ import annotations

import copy
from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
CHECKER = HERE / "verify_d14_one_band_a_aggregate_v2_strict_audit.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("strict_a_auditor", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def failure(function, fragment):
    try:
        function()
    except Exception as error:
        if fragment not in str(error):
            raise AssertionError((fragment, type(error).__name__, str(error)))
    else:
        raise AssertionError(f"mutant unexpectedly passed: {fragment}")


def main():
    checker = load_checker()
    path = checker.SHARD_DIRECTORY / "r00.json"
    row, _ = checker.load_canonical(path, checker.SHARD_SHA[0])
    checker.validate_shard(0, row)

    mutant = copy.deepcopy(row)
    mutant["exact_values"]["band_I_count"] = str(
        Q(mutant["exact_values"]["band_I_count"]) + 1)
    failure(lambda: checker.validate_shard(0, mutant), "subtraction/scaling")

    mutant = copy.deepcopy(row)
    mutant["geometry"]["schedule"][12] = "1/5"
    failure(lambda: checker.validate_shard(0, mutant), "geometry")

    mutant = copy.deepcopy(row)
    del mutant["source_hashes"][next(iter(mutant["source_hashes"]))]
    failure(lambda: checker.validate_shard(0, mutant), "identity/provenance")

    mutant = copy.deepcopy(row)
    mutant["inventory"]["high_faces"] -= 1
    failure(lambda: checker.validate_shard(0, mutant), "inventory")

    mutant = copy.deepcopy(row)
    mutant["candidate"]["scaled_exact_full_simplex_I"] = str(
        Q(mutant["candidate"]["scaled_exact_full_simplex_I"]) + 1)
    failure(lambda: checker.validate_shard(0, mutant), "full-simplex arithmetic")

    duplicate = b'{"x":1,"x":2}\n'
    failure(lambda: checker.strict_load(duplicate, "duplicate fixture"),
            "duplicate JSON key")
    print("7/7 strict D14 A aggregate-auditor mutation tests passed")


if __name__ == "__main__":
    main()
