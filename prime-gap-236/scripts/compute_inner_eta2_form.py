#!/usr/bin/env python3
"""Reconstruct the D16 inner marginal square at the wide eta2 cutoff."""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
sys.path[:0] = [str(REPO / "agents/small-delta-frontier")]
import scan_bv_epsilon_fixed as scan  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = REPO / "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json"
    raw = json.loads(source.read_text())
    basis = [(int(a), tuple(int(x) for x in lam)) for a, lam in raw["basis"]]
    vector = [Q(x) for x in raw["rational_vector"]]
    denominator, numerator, groups, components, products = scan.direct_forms(
        48, basis, vector, Q(103, 400), Q(3031, 12000), Q(361, 50000))
    output = {
        "status": "exact-inner-wide-eta2-form",
        "rigorous": True,
        "theorem_ready": False,
        "parameters": {"k": 48, "alpha": "103/400",
                       "eta": "3031/12000", "delta": "361/50000"},
        "denominator": str(denominator),
        "numerator_48J": str(numerator),
        "orbit_groups": groups,
        "marginal_components": components,
        "marginal_products": products,
        "source_hashes": {
            str(source.relative_to(REPO)): sha(source),
            "agents/exact-integrator/src/exact_integrator.py": sha(
                REPO / "agents/exact-integrator/src/exact_integrator.py"),
            "agents/small-delta-frontier/scan_bv_epsilon_fixed.py": sha(
                REPO / "agents/small-delta-frontier/scan_bv_epsilon_fixed.py"),
        },
        "script_sha256": sha(FILE),
    }
    encoded = (json.dumps(output, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    args.output.write_bytes(encoded)
    print("numerator_48J", numerator)
    print("sha256", hashlib.sha256(encoded).hexdigest())


if __name__ == "__main__":
    main()
