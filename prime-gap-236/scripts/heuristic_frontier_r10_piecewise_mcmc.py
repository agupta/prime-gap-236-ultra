#!/usr/bin/env python3
"""Run the corrected two-band D16 MCMC on the r10/.166 support frontier.

The underlying sampler is the already-audited search instrument.  This thin
driver replaces only the large-count schedule at runtime and adds explicit
provenance for that override.  Output is heuristic and has no proof status.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
BASE = REPO / "scripts/heuristic_piecewise_capped_mcmc.py"
SPEC = importlib.util.spec_from_file_location("piecewise_mcmc", BASE)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

START = Q(5051, 50000)
PLATEAU = Q(83, 500)


def schedule(r):
    if r <= 0:
        raise ValueError("schedule is defined only at positive count")
    return min(START + (r - 1) * M.H.DELTA, PLATEAU)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chains", type=int, default=128)
    parser.add_argument("--groups", type=int, default=8)
    parser.add_argument("--burnin", type=int, default=300)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--thin", type=int, default=2)
    parser.add_argument("--seed", type=int, default=2360488)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    M.H.schedule_q = schedule
    with tempfile.TemporaryDirectory(prefix="frontier-r10-", dir="/tmp") as td:
        temporary = Path(td) / "base.json"
        saved = sys.argv
        sys.argv = [str(BASE), "--chains", str(args.chains),
                    "--groups", str(args.groups), "--burnin",
                    str(args.burnin), "--steps", str(args.steps),
                    "--thin", str(args.thin), "--seed", str(args.seed),
                    "--only", "both", "--output", str(temporary)]
        try:
            M.main()
        finally:
            sys.argv = saved
        result = json.loads(temporary.read_text())
    result["status"] = "HEURISTIC ONLY -- FRONTIER-R10 SCHEDULE"
    result["rigorous"] = False
    result["theorem_ready"] = False
    result["analytic_audit_pending_at_run"] = True
    result["runtime_schedule"] = {
        "id": "frontier-r10-plateau-166",
        "formula": "min(5051/50000+(r-1)*361/50000,83/500)",
        "active_counts": list(range(23)),
        "values": [str(schedule(r)) for r in range(1, 24)],
    }
    result.setdefault("source_hashes", {})[
        str(FILE.relative_to(REPO))] = sha256(FILE)
    result["source_hashes"][str(BASE.relative_to(REPO))] = sha256(BASE)
    payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        handle.write(payload)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    print(json.dumps({
        "artifact_sha256": digest,
        "status": result["status"],
        "fixed_amplitude_estimate": result["fixed_amplitude_estimate"],
        "I_group_standard_error": result["I"]["group_standard_error"],
        "J_group_standard_error": result["J"]["group_standard_error"],
    }, indent=2))


if __name__ == "__main__":
    main()
