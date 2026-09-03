#!/usr/bin/env python3
"""Exact D4 calibration for the independent tagged quadratic recurrence.

This is a bounded regression, not a target D12 run.  It reconstructs the
12-term fixed base and six-channel multiplier from their byte-pinned inputs
and demands exact equality with the separately stored D4 particular forms.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import resource
import sys
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from verify.exact_capped_certificate import (  # noqa: E402
    TARGET_C10_D12,
    build_basis_terms,
    expected_labels,
)
from verify.exact_quadratic_multiplier import (  # noqa: E402
    compute_i_quadratic_tagged,
    compute_j_quadratic_tagged,
    load_exact_quadratic_multiplier,
)


BASE = (ROOT / "agents/exact-integrator/results/"
        "c10_capped_D4_decimal55_vector_input.json")
FORMS = (ROOT / "agents/exact-integrator/results/"
         "c10_stratum_quadratic_cappedopt_D4_exact.json")
BASE_SHA = "2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b"
FORMS_SHA = "fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86"
DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")


def read_pinned(path: Path, expected: str):
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise RuntimeError(f"SHA mismatch for {path}: {actual}")
    return raw


def load():
    base = json.loads(read_pinned(BASE, BASE_SHA))
    if (set(base) != {"status", "k", "basis_dimension", "basis",
                     "rational_vector", "provenance"} or
            base["status"] != "exact-fixed-vector-input" or
            base["k"] != 48 or base["basis_dimension"] != 12):
        raise RuntimeError("D4 base metadata mismatch")
    if base["provenance"] != {
        "source": "../../../experiments/results/decimal_hb_c10_noones_D4.json",
        "source_sha256":
            "e879d914f2c183c744476dc59244370898ac5c1f375bcb2529fe20bca2db73c6",
        "interpretation": (
            "Each recorded finite decimal is interpreted exactly as a "
            "rational number, not rounded again."),
    }:
        raise RuntimeError("D4 base provenance mismatch")
    labels = []
    for raw_label in base["basis"]:
        if (not isinstance(raw_label, list) or len(raw_label) != 2 or
                isinstance(raw_label[0], bool) or
                not isinstance(raw_label[0], int) or
                not isinstance(raw_label[1], list)):
            raise RuntimeError("malformed D4 label")
        label = (raw_label[0], tuple(raw_label[1]))
        labels.append(label)
    if len(labels) != 12 or len(set(labels)) != 12 or \
            set(labels) != expected_labels(4, 48):
        raise RuntimeError("D4 basis is not the complete no-ones D4 basis")
    if not isinstance(base["rational_vector"], list) or \
            len(base["rational_vector"]) != 12:
        raise RuntimeError("D4 coefficient vector length mismatch")
    coefficients = []
    for value in base["rational_vector"]:
        if not isinstance(value, str) or DECIMAL.fullmatch(value) is None:
            raise RuntimeError("D4 coefficient is not a canonical finite decimal")
        coefficients.append(Fraction(value))
    forms_raw = read_pinned(FORMS, FORMS_SHA)
    forms = json.loads(forms_raw)
    if forms.get("input_sha256") != BASE_SHA or \
            forms.get("input_json") != "results/c10_capped_D4_decimal55_vector_input.json":
        raise RuntimeError("D4 forms do not pin the calibrated base")
    multipliers = load_exact_quadratic_multiplier(
        FORMS, TARGET_C10_D12, FORMS_SHA)
    return (build_basis_terms(labels, coefficients), multipliers,
            Fraction(forms["denominator"]), Fraction(forms["numerator"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("i", "j", "all"), default="all")
    parser.add_argument("--reverse-faces", action="store_true")
    args = parser.parse_args()
    terms, multipliers, expected_i, expected_kj = load()
    print("D4 inputs parsed; beginning exact tagged calibration", flush=True)
    if args.phase in ("i", "all"):
        started = time.perf_counter()
        actual_i = compute_i_quadratic_tagged(
            terms, TARGET_C10_D12, multipliers,
            reverse_faces=args.reverse_faces)
        print(f"I_SECONDS={time.perf_counter()-started:.6f}", flush=True)
        print(f"I_BITWISE_EQUAL={actual_i == expected_i}", flush=True)
        if actual_i != expected_i:
            raise RuntimeError(f"D4 I mismatch: {actual_i - expected_i}")
    if args.phase in ("j", "all"):
        started = time.perf_counter()
        actual_kj = 48 * compute_j_quadratic_tagged(
            terms, TARGET_C10_D12, multipliers,
            reverse_faces=args.reverse_faces)
        print(f"J_SECONDS={time.perf_counter()-started:.6f}", flush=True)
        print(f"M2_BITWISE_EQUAL={actual_kj == expected_kj}", flush=True)
        if actual_kj != expected_kj:
            raise RuntimeError(f"D4 M2 mismatch: {actual_kj - expected_kj}")
    print("D4 EXACT FORMS PASS")
    print("PEAK_RSS_KIB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


if __name__ == "__main__":
    main()
