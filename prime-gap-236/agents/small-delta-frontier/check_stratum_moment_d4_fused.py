#!/usr/bin/env python3
"""Fresh exact D4 matrix oracle for the fused SoA moment product."""

from __future__ import annotations

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
EI = HERE.parent / "exact-integrator"
sys.path[:0] = [str(HERE), str(EI), str(EI / "src")]

import exact_integrator as ei  # noqa: E402
from check_stratum_moment_d4_oracle import (  # noqa: E402
    INPUT, INPUT_SHA, PARAMETERS, REFERENCE, REFERENCE_SHA,
    load_inputs, matrix_sha, require, sha,
)
from stratum_moment_table import quadratic  # noqa: E402
from stratum_moment_table_fused import (  # noqa: E402
    FusedStratumMomentTableEvaluator,
    canonical_schema_sha256,
    validate_moment_tag_schema,
)
from stratum_quadratic import StratumQuadraticEvaluator  # noqa: E402


DEPENDENCIES = (
    HERE / "stratum_moment_table.py",
    HERE / "stratum_moment_table_fused.py",
    HERE / "check_stratum_moment_d4_oracle.py",
    EI / "stratum_quadratic.py",
    EI / "stratum_linear.py",
    EI / "stratum_amplitude.py",
    EI / "grouped_fixed_vector.py",
    Path(ei.__file__),
)


def snapshot_dependencies():
    answer = {}
    for path in (INPUT, REFERENCE, Path(__file__), *DEPENDENCIES):
        resolved = path.resolve()
        require(resolved not in answer, "fused D4 dependency path alias")
        raw = resolved.read_bytes()
        require(len(raw) <= 20_000_000, "fused D4 dependency too large")
        answer[resolved] = raw
    return answer


def publish_owned(path_text, payload, trusted):
    path = Path(path_text).resolve()
    require(path not in trusted, "fused D4 output aliases dependency")
    raw = (json.dumps(payload, indent=2) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), "fused D4 output regular")
        offset = 0
        while offset < len(raw):
            count = os.write(fd, raw[offset:])
            require(count > 0, "fused D4 short write")
            offset += count
        os.fsync(fd)
        fs, ps = os.fstat(fd), os.stat(path, follow_symlinks=False)
        require((fs.st_dev, fs.st_ino) == (ps.st_dev, ps.st_ino) and
                path.read_bytes() == raw, "fused D4 output ownership/bytes")
        for trusted_path, original in trusted.items():
            require(trusted_path.read_bytes() == original,
                    f"fused D4 dependency changed: {trusted_path}")
    finally:
        os.close(fd)
    print(json.dumps({"status": payload["status"],
                      "output_sha256": sha(raw)}, indent=2))


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} OUTPUT.json")
    trusted = snapshot_dependencies()
    labels, coefficients, ref_i, ref_j, input_bytes, reference_bytes = \
        load_inputs()
    reference = json.loads(reference_bytes)
    support = ei.OneStratumSupport(
        48, PARAMETERS["alpha"], PARAMETERS["delta"], PARAMETERS["eta"],
        PARAMETERS["beta1"], PARAMETERS["beta2"], PARAMETERS["beta3plus"])
    evaluator = FusedStratumMomentTableEvaluator(
        support, labels, coefficients, Q, degree=2)
    start = time.perf_counter()
    forms = evaluator.evaluate_moment_forms(progress=True)
    elapsed = time.perf_counter() - start
    validate_moment_tag_schema(forms["tag_schema"], 2)
    require(forms["tag_schema_sha256"] == canonical_schema_sha256(2),
            "fused D4 schema SHA mismatch")

    reference_evaluator = StratumQuadraticEvaluator(
        support, labels, coefficients, Q)
    ref_labels, ref_a, ref_b = reference_evaluator.assemble_dense(ref_i, ref_j)
    require(forms["labels"] == ref_labels, "fused D4 labels")
    require(forms["a_matrix"] == ref_a, "fused D4 I matrix")
    require(forms["b_matrix"] == ref_b, "fused D4 48J matrix")
    require(forms["i_faces"] == 312 and forms["j_branch_domains"] == 1200,
            "fused D4 face/domain counts")
    require(forms["j_fused_traversals"] == 1200 and
            forms["j_logical_moment_products"] == 8556 and
            forms["j_scalar_moment_integrals"] == 57788,
            "fused D4 logical tag counts")
    vector = [Q(x) for x in reference["rational_vector"]]
    denominator = quadratic(forms["a_matrix"], vector)
    numerator = quadratic(forms["b_matrix"], vector)
    require(denominator == Q(reference["denominator"]) and
            numerator == Q(reference["numerator"]),
            "fused D4 particular contraction")
    dependency_hashes = {
        str(path): sha(raw) for path, raw in trusted.items()
    }
    payload = {
        "status": "exact-D4-fused-stratum-moment-oracle-pass",
        "rigorous_forms": True,
        "theorem_ready": False,
        "scope": "C10 D4 degree-two fused-product calibration only",
        "k": 48,
        "degree": 2,
        "parameters": {key: str(value) for key, value in PARAMETERS.items()},
        "input_sha256": INPUT_SHA,
        "reference_sha256": REFERENCE_SHA,
        "dependency_hashes": dependency_hashes,
        "tag_schema": forms["tag_schema"],
        "tag_schema_sha256": forms["tag_schema_sha256"],
        "matrix_dimension": len(forms["labels"]),
        "i_matrix_sha256": matrix_sha(forms["a_matrix"]),
        "b48_matrix_sha256": matrix_sha(forms["b_matrix"]),
        "all_entries_equal_frozen_D4_oracle": True,
        "particular_denominator": str(denominator),
        "particular_numerator": str(numerator),
        "particular_quotient": str(numerator / denominator),
        "i_faces": forms["i_faces"],
        "i_scalar_moment_integrals": forms["i_scalar_moment_integrals"],
        "j_branch_domains": forms["j_branch_domains"],
        "j_fused_traversals": forms["j_fused_traversals"],
        "j_logical_moment_products": forms[
            "j_logical_moment_products"],
        "j_scalar_moment_integrals": forms[
            "j_scalar_moment_integrals"],
        "j_orbit_pair_visits": forms["j_orbit_pair_visits"],
        "j_tagged_polynomial_multiplies": forms[
            "j_tagged_polynomial_multiplies"],
        "j_density_visits": forms["j_density_visits"],
        "j_density_tag_contractions": forms[
            "j_density_tag_contractions"],
        "forms_seconds": elapsed,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    require(INPUT.read_bytes() == input_bytes and
            REFERENCE.read_bytes() == reference_bytes,
            "fused D4 source/reference changed")
    publish_owned(sys.argv[1], payload, trusted)


if __name__ == "__main__":
    main()
