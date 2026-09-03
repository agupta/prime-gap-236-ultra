#!/usr/bin/env python3
"""Append selected exact stratum-tagged p2 columns to an exact L/Z matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction as Q
from pathlib import Path

from exact_lz_integrator import LZMatrixBuilder, c722_support, qtext
from p2_enrichment import P2Entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base_matrix", type=Path)
    ap.add_argument("--strata", help="comma list; default all active")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    base_bytes = args.base_matrix.read_bytes()
    raw = json.loads(base_bytes)
    if raw.get("format") != "exact-lz-matrices-v1":
        raise ValueError("wrong base format")
    k, degree = int(raw["parameters"]["k"]), int(raw["parameters"]["degree"])
    if k != 48:
        raise ValueError("this research script is pinned to C722 k=48")
    support = c722_support(k)
    engine = P2Entries(support, degree)
    base_labels = [tuple(x) for x in raw["labels"]]
    if tuple(base_labels) != engine.base.labels:
        raise ValueError("base labels do not match reconstructed C722 labels")
    selected = (support.active_strata() if args.strata is None else
                tuple(int(x) for x in args.strata.split(",") if x != ""))
    if len(set(selected)) != len(selected) or any(
            r not in support.active_strata() for r in selected):
        raise ValueError("invalid or repeated p2 stratum")
    selected = tuple(sorted(selected))

    tagged = [engine.lz(*x) for x in base_labels] + [engine.p2(r) for r in selected]
    n0, n = len(base_labels), len(tagged)
    I = [[Q(0) for _ in range(n)] for _ in range(n)]
    J = [[Q(0) for _ in range(n)] for _ in range(n)]
    oldI = [[Q(x) for x in row] for row in raw["I"]]
    oldJ = [[Q(x) for x in row] for row in raw["J"]]
    for i in range(n0):
        if len(oldI[i]) != n0 or len(oldJ[i]) != n0:
            raise ValueError("malformed base matrix")
        I[i][:n0] = oldI[i]
        J[i][:n0] = oldJ[i]
    for i in range(n0, n):
        for j in range(i + 1):
            I[i][j] = I[j][i] = engine.i_entry(tagged[i], tagged[j])
            J[i][j] = J[j][i] = engine.j_entry(tagged[i], tagged[j])

    # Exact independent contraction catches new-column factors and ordering.
    c = tuple(Q(((-1) ** (i + tagged[i][1])) * (i + 3), i + 17)
              for i in range(n))
    mi = sum(c[i] * I[i][j] * c[j] for i in range(n) for j in range(n))
    mj = sum(c[i] * J[i][j] * c[j] for i in range(n) for j in range(n))
    di, dj = engine.direct_fixed_vector(tagged, c)
    if (mi, mj) != (di, dj):
        raise AssertionError("enriched matrix/direct contraction mismatch")

    # Put R first so the generic block-whitener can use the block structure.
    disk_labels = ([[r, "lz", a, b] for r, a, b in base_labels] +
                   [[r, "p2", 0, 0] for r in selected])
    out = {
        "format": "exact-lz-p2-matrices-v1",
        "parameters": dict(raw["parameters"]),
        "base_matrix_sha256": hashlib.sha256(base_bytes).hexdigest(),
        "p2_strata": list(selected),
        "labels": disk_labels,
        "I": [[qtext(x) for x in row] for row in I],
        "J": [[qtext(x) for x in row] for row in J],
        "fixed_vector_direct_contraction": "PASS",
    }
    encoded = (json.dumps(out, sort_keys=True, separators=(",", ":")) + "\n").encode()
    args.output.write_bytes(encoded)
    print("P2 ENRICHED EXACT MATRIX PASS", "base", n0, "p2", len(selected), "total", n)
    print("p2_strata", ",".join(map(str, selected)))
    print("sha256", hashlib.sha256(encoded).hexdigest())


if __name__ == "__main__":
    main()
