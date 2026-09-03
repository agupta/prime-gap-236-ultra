#!/usr/bin/env python3
"""Formula-level audit of the non-rigorous single-count umbrella sampler."""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
SOURCE = "scripts/heuristic_capped_single_count_umbrella_mcmc.py"
BASE = "scripts/heuristic_capped_count_pencil_mcmc.py"
MIDDLE = "scripts/heuristic_piecewise_capped_mcmc.py"
HELPER = "scripts/heuristic_capped_piecewise_probe.py"
PINNED = {
    SOURCE:
        "fcef0eefc2a0503d2d1f27c568c64897dab01f8ed4c84dc33afb47a3551200a5",
    BASE:
        "5accfe97f9561ce08f3fb403d9d0579847caf289a9cbd2ca8ad6229f6bc11c7b",
    MIDDLE:
        "7d456f0616c382858c946ada3f6ea8d7bc72c22b04eb62a1b566f3077acd7213",
    HELPER:
        "a40f7304e7a2b1413130fabb0ae7f9cb3dd78909159f4eeb24ebe6b7049fd220",
    "results/wide_c722_D16_piecewise_cinner1_couter_natural_exact.json":
        "e30a9a5f356b0303559bd1d3c1cb7a48474e973ec97b164c00832c919f761cb7",
    "results/wide_c722_D16_inner_eta2_exact.json":
        "78ae10ff34a195779077222f7a845a948a78e11ff905c7e5cbdb590c6d6f256e",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def load_source():
    path = REPO / SOURCE
    spec = importlib.util.spec_from_file_location(
        "audited_single_count_umbrella", path)
    require(spec is not None and spec.loader is not None,
            "cannot load umbrella source")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == path.resolve() and
            Path(module.BASE_PATH).resolve() == (REPO / BASE).resolve() and
            Path(module.C.MCMC_PATH).resolve() == (REPO / MIDDLE).resolve() and
            Path(module.M.HELPER_PATH).resolve() == (REPO / HELPER).resolve(),
            "umbrella import closure changed")
    return module


def build():
    for relative, expected in PINNED.items():
        require(sha(REPO / relative) == expected,
                f"frozen umbrella input changed: {relative}")
    module = load_source()
    helper = module.H
    require(helper.K == 48 and helper.ETA1 == Q(97, 400) and
            helper.ETA2 == Q(3031, 12000),
            "Definition-5 dimensions/cutoffs changed")

    # Exact discrete hostile fixture for
    # E_pi[f] = E_piw[f/w] / E_piw[1/w].
    probability = (Q(1, 5), Q(3, 10), Q(1, 2))
    weight = (Q(1), Q(7), Q(2))
    observable = (Q(-2), Q(5), Q(11, 3))
    z = sum(p * w for p, w in zip(probability, weight))
    biased = tuple(p * w / z for p, w in zip(probability, weight))
    numerator = sum(pw * f / w for pw, f, w in
                    zip(biased, observable, weight))
    denominator = sum(pw / w for pw, w in zip(biased, weight))
    require(numerator / denominator ==
            sum(p * f for p, f in zip(probability, observable)),
            "umbrella self-normalization identity failed")

    # The pair-redistribution proposal has the same conditional density in
    # both directions (the selected pair sum is invariant).  With a symmetric
    # q, Metropolis min(1,d'w'/dw) satisfies detailed balance exactly.
    dw, dwp = Q(5, 7), Q(13, 11)
    forward = dw * min(Q(1), dwp / dw)
    reverse = dwp * min(Q(1), dw / dwp)
    require(forward == reverse, "Metropolis detailed balance failed")

    # For target total count 15: small distinguished t preserves common
    # count 15; large t increments common count 14 to total count 15.
    count = np.array([13, 14, 15, 16])
    small = np.array([2, 3, 5, 7], dtype=np.longdouble)
    large = np.array([11, 13, 17, 19], dtype=np.longdouble)
    selected = (small * (count == 15) + large * (count + 1 == 15))
    require(np.array_equal(
        selected, np.array([0, 13, 5, 0], dtype=np.longdouble)),
        "small@15 plus large@14 selection changed")
    biased_mask = ((count == 15) | (count + 1 == 15))
    require(np.array_equal(biased_mask,
                           np.array([False, True, True, False])),
            "J umbrella does not target common counts 14 and 15 exactly")

    # Pooled estimates must weight group ratios by their inverse-umbrella
    # denominator, equivalently pool raw numerators and denominators.
    den = np.array([2, 5, 17], dtype=np.longdouble)
    num = np.array([7, -3, 29], dtype=np.longdouble)
    ratio = num / den
    pooled = np.sum(ratio * den) / np.sum(den)
    raw_pooled = np.sum(num) / np.sum(den)
    unweighted = ratio.mean(dtype=np.longdouble)
    require(pooled == raw_pooled and pooled != unweighted,
            "denominator-weighted group pooling changed")

    # Independent 2x2 whitening check catches a missing off-diagonal square
    # or factor two.  A symmetric matrix stores B01 once; the eigenformula
    # contains B01^2 after whitening.
    a00, arr = np.longdouble(2), np.longdouble(3)
    b00, b0r, brr = map(np.longdouble, (1, 4, 5))
    reported = module.top_2d(a00, arr, b00, b0r, brr)
    whitened = np.array(
        [[b00 / a00, b0r / np.sqrt(a00 * arr)],
         [b0r / np.sqrt(a00 * arr), brr / arr]], dtype=np.longdouble)
    expected = np.linalg.eigvalsh(np.asarray(whitened, dtype=float))[-1]
    require(abs(reported - expected) < np.longdouble("1e-15"),
            "2x2 generalized-eigenvalue formula changed")

    return {
        "status": "SEARCH-INSTRUMENT PASS",
        "rigorous_quotient": False,
        "checker_sha256": sha(FILE),
        "pinned": PINNED,
        "formula_checks": {
            "self_normalized_change_of_measure_identity": True,
            "pair_redistribution_proposal_symmetric": True,
            "Metropolis_detailed_balance_for_density_times_umbrella": True,
            "I_umbrella_targets_total_count_15": True,
            "J_umbrella_targets_common_counts_14_and_15": True,
            "J_selected_component_is_small_at_15_plus_large_at_14": True,
            "pooled_groups_weighted_by_inverse_umbrella_denominator": True,
            "two_by_two_off_diagonal_scaling": True,
            "B00_cutoff": "97/400",
            "outer_involving_cutoff": "3031/12000",
        },
        "decision": (
            "formula-level search instrument only; burn-in, autocorrelation, "
            "floating-point error, and every quotient sign remain non-rigorous"),
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
