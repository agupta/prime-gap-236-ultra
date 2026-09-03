#!/usr/bin/env python3
"""Disabled exact-common-r stage producer for the active25 27D pencil.

The arithmetic core and disabled resource gate are byte-pinned.  The target
stage path exists for audit, but cannot execute until a later, separately
audited source revision pins an authorized gate.  Shards are exact Fractions
indexed by the common large count and merge by componentwise addition.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import sys
import time


FILE = Path(__file__).resolve()
HERE = FILE.parent
CORE_PATH = HERE / "frontier_active25_inner_d16_tagged_shell.py"
GATE_PATH = HERE / "results/frontier_active25_innerD16_tagged_shell_prelaunch_gate.json"
GATE_CHECKER = HERE / "verify_frontier_active25_prelaunch_gate.py"
PINNED = {
    CORE_PATH: "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    GATE_PATH: "1642a5efcc4e2b304271fe3b785d439ce9b1ddb405855f56a7e62a1b4e61e6ac",
    GATE_CHECKER: "552e6e92916c62179f56262f33fddfeda46d65463c7a13edb165892f0c15020b",
}


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def snapshots():
    answer = {}
    for path, expected in PINNED.items():
        data = path.read_bytes()
        if sha256(data) != expected:
            raise RuntimeError(f"staged dependency changed: {path}")
        answer[path] = data
    return answer


_START = snapshots()
_SPEC = importlib.util.spec_from_file_location("active25_staged_core", CORE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(CORE_PATH)
core = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = core
_SPEC.loader.exec_module(core)


def load_gate():
    gate = json.loads(_START[GATE_PATH])
    if (gate.get("format") !=
            "frontier-active25-inner-D16-tagged-shell-prelaunch-gate-v1" or
            gate.get("arithmetic_core_sha256") != PINNED[CORE_PATH] or
            gate.get("analytic_audit_sha256") !=
            core.PINNED[core.ANALYTIC] or
            gate.get("active_outer_counts") != list(range(26)) or
            gate.get("stage_common_r") != list(range(26)) or
            gate.get("dimension") != 27 or
            gate.get("resource_gate", {}).get("workers") != 1):
        raise ValueError("staged gate identity mismatch")
    return gate


def require_authorized():
    gate = load_gate()
    if (gate.get("launch_authorized") is not True or
            gate.get("status") != "AUTHORIZED"):
        raise RuntimeError("target traversal is disabled by the frozen gate")
    return gate


def production_inputs(inner_loader=core.load_inner_coordinate):
    """Build cross inputs while keeping shell logic independent of degree.

    A future audited D18 loader need only return the same five-object contract
    ``(basis,vector,amplitudes,inner_I,inner_48J)``.  No shell support,
    right-count tagging, or common-r traversal code then changes.
    """
    basis, vector, amplitudes, inner_i, inner_b = inner_loader()
    supports = core.make_supports()
    components = core.outer_core.components(basis, vector, core.K)
    one = (((), 0, 0, Q(1)),)
    named = {"R": (supports["R"], components),
             "V": (supports["V"], components),
             "H": (supports["H"], one),
             "L": (supports["L"], one)}
    catalog = (("rh", "R", "H"), ("rl", "R", "L"),
               ("vh", "V", "H"), ("vl", "V", "L"))
    weights = core.production_pair_weights(amplitudes)
    return named, catalog, weights, inner_i, inner_b, len(basis)


def exact_common_r_shard(common_r, *, inner_loader=core.load_inner_coordinate,
                         progress=False):
    if type(common_r) is not int or common_r not in range(26):
        raise ValueError("common_r is not an audited active count")
    named, catalog, weights, inner_i, inner_b, inner_dimension = \
        production_inputs(inner_loader)
    table, counts, geometric, nonzero, faces = core.grouped_weighted_cross(
        named, catalog, weights, core.ETA2, common_strata=(common_r,),
        direct_full_left=("R", "V"), progress=progress)
    if len(table) != core.K + 1:
        raise ArithmeticError("target-count table has wrong length")
    if any(value for index, value in enumerate(table)
           if index not in (common_r, common_r + 1)):
        raise ArithmeticError("common-r shard escaped its two target counts")
    return {
        "common_r": common_r,
        "complete_common_r": True,
        "domain_counts": counts,
        "faces": faces,
        "geometric_group_count": geometric,
        "inner_48J": str(inner_b),
        "inner_I": str(inner_i),
        "inner_basis_dimension": inner_dimension,
        "nonzero_group_count": nonzero,
        "raw_J_cross_by_target_R": [str(value) for value in table],
    }


def stage_payload(common_r):
    gate = require_authorized()
    started = time.monotonic()
    before = snapshots()
    self_before = FILE.read_bytes()
    shard = exact_common_r_shard(common_r, progress=True)
    if snapshots() != before or FILE.read_bytes() != self_before:
        raise RuntimeError("stage source closure changed")
    return {
        "arithmetic_core_sha256": PINNED[CORE_PATH],
        "driver_sha256": sha256(FILE),
        "gate_sha256": PINNED[GATE_PATH],
        "launch_gate_status": gate["status"],
        "parameters": core.parameter_record(),
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "shard": shard,
        "status": "frontier-active25-inner-D16-exact-common-r-stage",
        "theorem_ready": False,
        "wall_seconds": time.monotonic() - started,
    }


def strict_shard(value):
    if type(value) is not dict or set(value) != {
            "common_r", "complete_common_r", "domain_counts", "faces",
            "geometric_group_count", "inner_48J", "inner_I",
            "inner_basis_dimension", "nonzero_group_count",
            "raw_J_cross_by_target_R"}:
        raise ValueError("shard schema mismatch")
    r = value["common_r"]
    counts = value["domain_counts"]
    if (type(r) is not int or r not in range(26) or
            value["complete_common_r"] is not True or
            type(counts) is not dict or
            set(counts) != {"rh", "rl", "vh", "vl"} or
            any(type(counts[tag]) is not int or counts[tag] < 0
                for tag in counts) or
            type(value["faces"]) is not int or value["faces"] <= 0 or
            type(value["geometric_group_count"]) is not int or
            value["geometric_group_count"] < 0 or
            type(value["nonzero_group_count"]) is not int or
            not 0 <= value["nonzero_group_count"] <=
            value["geometric_group_count"] or
            type(value["inner_basis_dimension"]) is not int or
            value["inner_basis_dimension"] <= 0 or
            type(value["raw_J_cross_by_target_R"]) is not list or
            len(value["raw_J_cross_by_target_R"]) != core.K + 1):
        raise ValueError("shard identity mismatch")
    fraction_fields = [value["inner_I"], value["inner_48J"],
                       *value["raw_J_cross_by_target_R"]]
    if any(type(x) is not str or str(Q(x)) != x for x in fraction_fields):
        raise ValueError("noncanonical shard fraction")
    vector = [Q(x) for x in value["raw_J_cross_by_target_R"]]
    if any(x for index, x in enumerate(vector) if index not in (r, r + 1)):
        raise ValueError("shard target support mismatch")
    return r, vector


def merge_exact_shards(shards):
    """Deterministic merge, independent of file or completion order."""
    by_r = {}
    inner_identity = None
    for shard in shards:
        r, vector = strict_shard(shard)
        if r in by_r:
            raise ValueError("duplicate common-r shard")
        identity = (Q(shard["inner_I"]), Q(shard["inner_48J"]),
                    shard["inner_basis_dimension"])
        if inner_identity is None:
            inner_identity = identity
        elif inner_identity != identity:
            raise ValueError("inner coordinate changed between shards")
        by_r[r] = vector
    if set(by_r) != set(range(26)):
        raise ValueError("incomplete common-r shard set")
    total = [sum((by_r[r][index] for r in range(26)), Q(0))
             for index in range(core.K + 1)]
    return total, inner_identity


def preflight():
    gate = load_gate()
    core_preflight = core.preflight()
    return {
        "active_common_r": list(range(26)),
        "arithmetic_core_sha256": PINNED[CORE_PATH],
        "core_preflight": core_preflight,
        "deterministic_merge": "sort unique shards by common_r; exact Fraction sum",
        "dimension": 27,
        "driver_sha256": sha256(FILE),
        "future_inner_loader_contract":
            "basis,vector,amplitudes,inner_I,inner_48J",
        "gate_sha256": PINNED[GATE_PATH],
        "launch_authorized": gate["launch_authorized"],
        "status": "frontier-active25-exact-staged-preflight",
        "target_started": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--stage-r", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.preflight_only:
        if args.stage_r is not None or args.output is not None:
            parser.error("preflight takes no stage/output")
        print(json.dumps(preflight(), sort_keys=True, indent=2))
        return
    if args.stage_r is None or args.output is None:
        parser.error("stage mode requires --stage-r and --output")
    payload = (json.dumps(stage_payload(args.stage_r), sort_keys=True,
                          separators=(",", ":")) + "\n").encode("ascii")
    core.publish(args.output, payload)
    print(json.dumps({"output_sha256": sha256(payload)}, sort_keys=True))


if __name__ == "__main__":
    main()
