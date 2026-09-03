#!/usr/bin/env python3
"""Exact C10 D4 oracle for the multiplier-independent moment table.

This performs a fresh degree-two moment-table traversal and compares every
assembled entry against the frozen six-channel D4 exact artifact.  It is a D4
calibration only; it makes no statement about a D12 degree-three sign.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import resource
import stat
import sys
import time
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
EI = HERE.parent / "exact-integrator"
sys.path[:0] = [str(HERE), str(EI), str(EI / "src")]

import exact_integrator as ei  # noqa: E402
from stratum_moment_table import StratumMomentTableEvaluator, quadratic  # noqa: E402
from stratum_quadratic import StratumQuadraticEvaluator  # noqa: E402


INPUT = EI / "results/c10_capped_D4_decimal55_vector_input.json"
INPUT_SHA = "2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b"
REFERENCE = EI / "results/c10_stratum_quadratic_cappedopt_D4_exact.json"
REFERENCE_SHA = "fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86"
PARAMETERS = {
    "alpha": Q(79247, 300000), "delta": Q(1, 100),
    "eta": Q(76247, 300000), "beta1": Q(3, 20),
    "beta2": Q(3, 20), "beta3plus": Q(97, 625),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def matrix_sha(matrix):
    raw = json.dumps([[str(x) for x in row] for row in matrix],
                     separators=(",", ":")).encode()
    return sha(raw)


def load_inputs():
    input_bytes, reference_bytes = INPUT.read_bytes(), REFERENCE.read_bytes()
    require(sha(input_bytes) == INPUT_SHA, "D4 fixed base SHA mismatch")
    require(sha(reference_bytes) == REFERENCE_SHA,
            "D4 quadratic reference SHA mismatch")
    source, reference = json.loads(input_bytes), json.loads(reference_bytes)
    require(source["k"] == 48 and reference["k"] == 48,
            "D4 oracle k mismatch")
    expected_parameters = {key: str(value) for key, value in PARAMETERS.items()}
    require(reference["parameters"] == expected_parameters,
            "D4 oracle parameter mismatch")
    labels = [(int(a), tuple(int(x) for x in partition))
              for a, partition in source["basis"]]
    coefficients = [Q(x) for x in source["rational_vector"]]
    require(len(labels) == len(coefficients) == 12,
            "D4 fixed basis dimension")
    i_blocks = {int(r): [[Q(x) for x in row] for row in block]
                for r, block in reference["i_blocks"].items()}
    j_entries = {}
    for key, value in reference["j_entries"].items():
        parsed = ast.literal_eval(key)
        require(type(parsed) is tuple and len(parsed) == 2,
                "D4 reference J label")
        j_entries[parsed] = Q(value)
    return labels, coefficients, i_blocks, j_entries, input_bytes, reference_bytes


def publish(path_text, payload):
    path = Path(path_text).resolve()
    require(path not in {INPUT.resolve(), REFERENCE.resolve(),
                         Path(__file__).resolve()}, "output path alias")
    raw = (json.dumps(payload, indent=2) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), "output is not regular")
        offset = 0
        while offset < len(raw):
            count = os.write(fd, raw[offset:])
            require(count > 0, "short output write")
            offset += count
        os.fsync(fd)
        require(path.read_bytes() == raw, "output bytes mismatch")
    finally:
        os.close(fd)
    print(json.dumps({"status": payload["status"],
                      "output_sha256": sha(raw)}, indent=2))


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} OUTPUT.json")
    labels, coefficients, ref_i, ref_j, input_bytes, reference_bytes = \
        load_inputs()
    support = ei.OneStratumSupport(
        48, PARAMETERS["alpha"], PARAMETERS["delta"], PARAMETERS["eta"],
        PARAMETERS["beta1"], PARAMETERS["beta2"], PARAMETERS["beta3plus"])
    evaluator = StratumMomentTableEvaluator(
        support, labels, coefficients, Q, degree=2)
    start = time.perf_counter()
    forms = evaluator.evaluate_moment_forms(progress=True)
    seconds = time.perf_counter() - start

    reference_evaluator = StratumQuadraticEvaluator(
        support, labels, coefficients, Q)
    ref_labels, ref_a, ref_b = reference_evaluator.assemble_dense(ref_i, ref_j)
    require(forms["labels"] == ref_labels, "D4 label mismatch")
    require(forms["a_matrix"] == ref_a, "D4 I matrix mismatch")
    require(forms["b_matrix"] == ref_b, "D4 48J matrix mismatch")
    require(forms["i_faces"] == 312, "D4 I face count mismatch")
    require(forms["j_branch_domains"] == 1200,
            "D4 J domain count mismatch")
    vector = [Q(x) for x in json.loads(reference_bytes)["rational_vector"]]
    denominator = quadratic(forms["a_matrix"], vector)
    numerator = quadratic(forms["b_matrix"], vector)
    reference = json.loads(reference_bytes)
    require(denominator == Q(reference["denominator"]) and
            numerator == Q(reference["numerator"]),
            "D4 particular-vector contraction mismatch")
    require(INPUT.read_bytes() == input_bytes and
            REFERENCE.read_bytes() == reference_bytes,
            "D4 oracle input changed during traversal")

    payload = {
        "status": "exact-D4-stratum-moment-table-oracle-pass",
        "rigorous_forms": True,
        "theorem_ready": False,
        "scope": "C10 D4 degree-two calibration; no D12 sign",
        "input_sha256": INPUT_SHA,
        "reference_sha256": REFERENCE_SHA,
        "moment_table_script_sha256": sha(
            (HERE / "stratum_moment_table.py").read_bytes()),
        "oracle_script_sha256": sha(Path(__file__).read_bytes()),
        "integrator_sha256": sha(Path(ei.__file__).read_bytes()),
        "matrix_dimension": len(forms["labels"]),
        "i_matrix_sha256": matrix_sha(forms["a_matrix"]),
        "b48_matrix_sha256": matrix_sha(forms["b_matrix"]),
        "all_entries_equal_frozen_D4_oracle": True,
        "particular_denominator": str(denominator),
        "particular_numerator": str(numerator),
        "particular_quotient": str(numerator / denominator),
        "i_faces": forms["i_faces"],
        "j_branch_domains": forms["j_branch_domains"],
        "i_scalar_moment_integrals": forms["i_scalar_moment_integrals"],
        "j_moment_products": forms["j_moment_products"],
        "j_scalar_moment_integrals": forms["j_scalar_moment_integrals"],
        "reference_j_channel_integrals": reference["j_channel_integrals"],
        "forms_seconds": seconds,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    publish(sys.argv[1], payload)


if __name__ == "__main__":
    main()
