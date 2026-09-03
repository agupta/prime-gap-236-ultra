#!/usr/bin/env python3
"""Hostile prelaunch audit of the frozen capped D16 staged driver.

No D16 target stage is launched.  The checker pins provenance, validates the
three supports and exact piecewise base, and exercises the ordered cross/count
and selected-h logic on an exact low-dimensional oracle.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
SOURCE = "agents/structural-basis/code/bv_d16_volume_ramp_capped_probe_v1.py"
TESTS = "agents/structural-basis/tests/test_bv_d16_volume_ramp_capped_probe_v1.py"
PIECEWISE_AUDIT = "agents/audit/results/bv_d16_piecewise_definition5_audit.json"
PINNED = {
    SOURCE:
        "cad3e32b77717419061a46d9863e5a99785cf34f71fc5e992f684c3b1741f7f5",
    TESTS:
        "87ed989c9519e8a7890252321f8e15679f010e988400f58959d1f76fb3c416f5",
    PIECEWISE_AUDIT:
        "00e273d07ab98f667fcb3a8172a13349841ed0a4d58807c2308d6850fb3b2b25",
    "agents/exact-integrator/src/exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "agents/exact-integrator/grouped_fixed_vector.py":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    "agents/structural-basis/code/fixed_vector_support_kernel.py":
        "774b8f3a09d77d79d6e4abe56cce4ed1eb82fc5f71ca08cb033bd383091073a3",
    "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json":
        "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
    "results/wide_c722_D16_piecewise_cinner1_couter_natural_exact.json":
        "e30a9a5f356b0303559bd1d3c1cb7a48474e973ec97b164c00832c919f761cb7",
    "agents/audit/results/wide_c722_volume_ramp_analytic_audit.json":
        "88b6e1aeb04bd2e7d8600e5f4a7bcca8726b5307b95e5a4e9337a20c8f7afa96",
    "agents/audit/verify_wide_c722_volume_ramp_analytic.py":
        "f6882dd2df8c0fa6eee900c12f31a9dce453603a948ac7c391c4ad62815bb5a4",
    "agents/audit/WIDE-C722-VOLUME-RAMP-ANALYTIC-AUDIT.md":
        "f6c3eb4d1904fe670fdeb6459c8ab3e30428e6f29b63075f3937b47c59aa25c6",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def strict_json(relative):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate JSON key in {relative}: {key}")
            answer[key] = value
        return answer

    return json.loads(
        (REPO / relative).read_bytes(), object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {relative}: {token}")))


def load_source():
    path = REPO / SOURCE
    spec = importlib.util.spec_from_file_location(
        "audited_capped_stage_driver", path)
    require(spec is not None and spec.loader is not None,
            "cannot load capped stage driver")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == path.resolve(),
            "wrong capped stage driver imported")
    return module


def tiny_kernel(module, k, coefficients):
    labels = ((0, ()), (1, ()), (0, (2,)))
    payload = {
        "basis": [[a, list(lam)] for a, lam in labels],
        "basis_dimension": len(labels), "degree": 2, "k": k,
        "rational_vector": [str(Q(x)) for x in coefficients],
    }
    data = (json.dumps(payload, sort_keys=True, separators=(",", ":")) +
            "\n").encode("ascii")
    return module.kernel_core.compile_kernel_bytes(data)


def add_tables(destination, source):
    for key, value in source.items():
        destination[key] += value


def build():
    for relative, expected in PINNED.items():
        require(sha(REPO / relative) == expected,
                f"frozen capped-stage input changed: {relative}")
    module = load_source()
    require(module.sha256(module.FILE) == PINNED[SOURCE],
            "driver self identity changed")
    module.require_pins()
    module.validate_geometry_sources()
    independent = strict_json(PIECEWISE_AUDIT)
    require(independent.get("status") == "AUDIT PASS",
            "piecewise exact-base audit is not PASS")

    require(module.K == 48 and module.DEGREE == 16 and
            module.DELTA == Q(361, 50000) and
            module.ALPHA_INNER == Q(103, 400) and
            module.ETA_INNER == Q(97, 400) and
            module.ALPHA_OUTER == Q(3211, 12000) and
            module.ETA_OUTER == Q(3031, 12000) and
            module.NATURAL_C == Q(3090, 3211),
            "target constants changed")
    expected_schedule = tuple(
        min(Q(49, 625) + (m - 1) * module.DELTA, Q(1599, 10000))
        for m in range(1, 24))
    require(module.SCHEDULE == expected_schedule and
            all(left <= right <= left + module.DELTA
                for left, right in zip(module.SCHEDULE,
                                       module.SCHEDULE[1:])),
            "volume-ramp schedule changed")
    feasible = [0] + [
        r for r in range(1, module.K + 1)
        if r * module.DELTA < module.SCHEDULE[
            min(r, len(module.SCHEDULE)) - 1]]
    require(feasible == list(range(23)),
            "active outer total-count inventory changed")

    supports = module.make_supports(Q)
    require(set(supports) == {"inner_eta1", "inner_eta2", "high", "low"}
            and supports["inner_eta1"].eta == module.ETA_INNER
            and supports["inner_eta2"].eta == module.ETA_OUTER
            and supports["high"].eta == supports["low"].eta ==
            module.ETA_OUTER
            and supports["low"].alpha == module.ALPHA_INNER
            and supports["high"].alpha == module.ALPHA_OUTER
            and supports["low"].schedule == supports["high"].schedule ==
            module.SCHEDULE,
            "three-support Definition-5 geometry changed")
    base = module.load_piecewise_exact_base()
    cert = strict_json(
        "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json")
    require(Q(base["I_matrix"][0][0]) == Q(cert["exact_denominator"]) and
            Q(base["kJ_matrix"][0][0]) == Q(cert["exact_numerator"]),
            "c_inner=1 exact base changed")

    # Exact low-k oracle.  Distinct coefficient kernels are deliberately used
    # for inner and outer, and all six ordered block tags are computed even
    # though target production needs only one of hl/lh.
    k = 3
    inner_kernel = tiny_kernel(module, k, (Q(2), Q(-3), Q(5)))
    outer_kernel = tiny_kernel(module, k, (Q(-1), Q(4), Q(2)))
    delta, eta = Q(1, 20), Q(1, 5)
    schedule = (Q(4, 25), Q(9, 50), Q(1, 5))
    inner = module.ei.OneStratumSupport(
        k, Q(11, 50), delta, eta,
        Q(11, 50), Q(11, 50), Q(11, 50))
    high = module.ScheduledSupport.make(
        k, Q(3, 10), delta, eta, schedule)
    low = module.ScheduledSupport.make(
        k, Q(11, 50), delta, eta, schedule)
    tiny_supports = {"inner": inner, "high": high, "low": low}
    tiny_kernels = {"inner": inner_kernel, "high": outer_kernel,
                    "low": outer_kernel}
    pairs = (("fh", "inner", "high"), ("fl", "inner", "low"),
             ("hh", "high", "high"), ("hl", "high", "low"),
             ("lh", "low", "high"), ("ll", "low", "low"))
    aggregate = {tag: defaultdict(Q) for tag, _, _ in pairs}
    selected = {tag: defaultdict(Q) for tag, _, _ in pairs}
    for r in range(k):
        tables, _, _ = module.cross_bundle_r(
            tiny_supports, tiny_kernels, Q, pairs, r)
        for tag in aggregate:
            add_tables(aggregate[tag], tables[tag])
        high_eval = module.kernel_core.KernelEvaluator(high, outer_kernel, Q)
        low_eval = module.kernel_core.KernelEvaluator(low, outer_kernel, Q)
        high_direct, _ = high_eval.evaluate_j_r(
            *module.component_data(high_eval), r)
        low_direct, _ = low_eval.evaluate_j_r(
            *module.component_data(low_eval), r)
        require(sum(tables["hh"].values(), Q(0)) == high_direct and
                sum(tables["ll"].values(), Q(0)) == low_direct and
                tables["hl"] == {
                    (right, left): value
                    for (left, right), value in tables["lh"].items()},
                f"ordered cross/self oracle failed at common r={r}")
        max_h = int(eta / delta) - r
        for h in range(max_h + 1):
            piece, _, _ = module.cross_bundle_r(
                tiny_supports, tiny_kernels, Q, pairs, r, selected_h=h)
            for tag in selected:
                add_tables(selected[tag], piece[tag])
    require(all(dict(selected[tag]) == dict(aggregate[tag])
                for tag in aggregate),
            "selected-h pieces do not exhaust complete common-count tables")

    counts = range(k + 1)
    shell = {}
    for r in counts:
        for s in counts:
            key = (r, s)
            shell[key] = (aggregate["hh"].get(key, Q(0)) +
                          aggregate["ll"].get(key, Q(0)) -
                          aggregate["hl"].get(key, Q(0)) -
                          aggregate["hl"].get((s, r), Q(0)))
            require(shell[key] == shell[(s, r)] if (s, r) in shell else True,
                    "HL transpose symmetrization failed")
    scalar_from_one_table = (
        sum(aggregate["hh"].values(), Q(0)) +
        sum(aggregate["ll"].values(), Q(0)) -
        2 * sum(aggregate["hl"].values(), Q(0)))
    scalar_from_two_tables = (
        sum(aggregate["hh"].values(), Q(0)) +
        sum(aggregate["ll"].values(), Q(0)) -
        sum(aggregate["hl"].values(), Q(0)) -
        sum(aggregate["lh"].values(), Q(0)))
    require(scalar_from_one_table == scalar_from_two_tables,
            "uniform-amplitude HL/LH identity failed")

    return {
        "status": "AUDIT PASS",
        "scope": "frozen Decimal staged discovery driver; no heavy target stage run",
        "checker_sha256": sha(FILE),
        "pinned": PINNED,
        "checks": {
            "analytic_volume_ramp_artifact_bound": True,
            "piecewise_exact_base_independently_audited": True,
            "inner_kernel_dilation": "1",
            "outer_kernel_dilation": "3090/3211",
            "inner_inner_cutoff": "97/400",
            "all_outer_involving_cutoffs": "3031/12000",
            "outer_active_total_counts": list(range(23)),
            "I_shell_is_scheduled_high_minus_scheduled_low": True,
            "distinct_inner_outer_kernel_oracle": True,
            "ordered_cross_has_no_hidden_factor_two": True,
            "HL_transpose_identity": True,
            "selected_h_exhaustion_oracle": True,
        },
        "mandatory_consumer_contract": {
            "exact_target_dilations_only": ["1", "3090/3211"],
            "all_I_total_counts": list(range(23)),
            "all_J_common_counts": list(range(23)),
            "exact_J_tags": ["fh", "fl", "hh", "hl", "ll"],
            "selected_h": None,
            "complete_common_count": True,
            "shell_entry_formula": "HH[R,S]+LL[R,S]-HL[R,S]-HL[S,R]",
            "never_use_entrywise": "HH+LL-2HL unless amplitudes are uniform",
            "compare_decimal_precisions": [80, 100],
            "rigorous_sign_still_required": True,
        },
        "decision": (
            "safe to use for pinned staged Decimal discovery under the listed "
            "consumer contract; no output is an exact or interval certificate"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
