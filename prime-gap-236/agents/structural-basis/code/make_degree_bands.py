#!/usr/bin/env python3
"""Turn a dense polynomial vector into explicit total-degree band functions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json")
    ap.add_argument("--core-degree", type=int, default=4)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    path = Path(args.input_json)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if len(raw["basis"]) != len(raw["rational_vector"]):
        raise SystemExit("basis/vector length mismatch")
    core = []
    bands = {}
    for label, coefficient in zip(raw["basis"], raw["rational_vector"]):
        a, lam = int(label[0]), [int(x) for x in label[1]]
        degree = a + sum(lam)
        term = {"label": [a, lam], "coefficient": coefficient}
        if degree <= args.core_degree:
            core.append(term)
        else:
            bands.setdefault(str(degree), []).append(term)
    result = {
        "status": "exact-rational-degree-band-decomposition",
        "source_json": args.input_json,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "basis_convention": "G_(a,lambda)=(1-sum(t))^a P_lambda(t)",
        "total_degree": "a+sum(lambda)",
        "core_degree": args.core_degree,
        "core": core,
        "bands": bands,
        "identity": "F = sum(core terms) + sum_d H_d exactly over Q",
        "compressed_basis_dimension": len(core) + len(bands),
        "expanded_term_count": len(raw["basis"]),
    }
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output,
                      "compressed_basis_dimension": result["compressed_basis_dimension"],
                      "expanded_term_count": result["expanded_term_count"],
                      "bands": {d: len(v) for d, v in bands.items()}}, indent=2))


if __name__ == "__main__":
    main()
