#!/usr/bin/env python3
"""Make explicit, auditable orbit-label lists for BV hybrid experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def key(label):
    a, lam = label
    return (a + sum(lam), sum(lam), len(lam), tuple(lam), a)


def parse_partition(text: str):
    try:
        ans = tuple(int(x) for x in text.split(",") if x)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("partition must be comma-separated integers") from exc
    if not ans or any(x < 2 for x in ans) or tuple(sorted(ans, reverse=True)) != ans:
        raise argparse.ArgumentTypeError("partition must be decreasing with all parts >=2")
    return ans


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("core_run", type=Path,
                    help="run_basis JSON whose literal basis is the core")
    ap.add_argument("--union-run", action="append", type=Path, default=[],
                    help="append the literal basis from another run JSON")
    ap.add_argument("--partition", action="append", type=parse_partition, default=[],
                    help="append every (1-P1)^a P_lambda through --total-degree")
    ap.add_argument("--total-degree", type=int, default=16)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    core_bytes = args.core_run.read_bytes()
    core = json.loads(core_bytes)
    labels = {(int(a), tuple(int(x) for x in lam)) for a, lam in core["basis"]}
    source_runs = [{"path": str(args.core_run),
                    "sha256": hashlib.sha256(core_bytes).hexdigest()}]
    additions = {}
    for path in args.union_run:
        raw_bytes = path.read_bytes()
        raw = json.loads(raw_bytes)
        if (raw.get("k") != core.get("k") or
                raw.get("parameters") != core.get("parameters")):
            raise ValueError(f"support mismatch in {path}")
        before = len(labels)
        labels.update((int(a), tuple(int(x) for x in lam))
                      for a, lam in raw["basis"])
        additions[f"run:{path}"] = len(labels) - before
        source_runs.append({"path": str(path),
                            "sha256": hashlib.sha256(raw_bytes).hexdigest()})
    for lam in args.partition:
        before = len(labels)
        for a in range(args.total_degree - sum(lam) + 1):
            labels.add((a, lam))
        additions["partition:" + ",".join(map(str, lam))] = len(labels) - before

    basis = sorted(labels, key=key)
    encoded_basis = [[a, list(lam)] for a, lam in basis]
    # The output itself is the exact list accepted by run_basis --basis-json;
    # provenance is printed separately so no downstream parser can silently
    # mistake metadata for a basis label.
    rendered = (json.dumps(encoded_basis, separators=(",", ":")) + "\n").encode()
    args.output.write_bytes(rendered)
    print(json.dumps({
        "core_dimension": len(core["basis"]),
        "hybrid_dimension": len(basis),
        "added": len(basis) - len(core["basis"]),
        "addition_breakdown": additions,
        "source_runs": source_runs,
        "basis_sha256": hashlib.sha256(rendered).hexdigest(),
    }, indent=2))


if __name__ == "__main__":
    main()
