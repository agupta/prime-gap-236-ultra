#!/usr/bin/env python3
"""Formula-level audit of the non-rigorous capped count-pencil MCMC.

This checker runs no Markov chain.  It pins the search instrument, checks its
exact normalizers/cutoffs, and exercises the matrix assembly and count split
on hostile synthetic fixtures.  Passing says only that the sampled moments
would be placed in the intended finite pencil; it says nothing about MCMC
convergence or the sign of an exact quotient.
"""

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
SOURCE = "scripts/heuristic_capped_count_pencil_mcmc.py"
MIDDLE = "scripts/heuristic_piecewise_capped_mcmc.py"
HELPER = "scripts/heuristic_capped_piecewise_probe.py"
PIECEWISE = "results/wide_c722_D16_piecewise_cinner1_couter_natural_exact.json"
INNER_ETA2 = "results/wide_c722_D16_inner_eta2_exact.json"
CERT = "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json"
PINNED = {
    SOURCE:
        "5accfe97f9561ce08f3fb403d9d0579847caf289a9cbd2ca8ad6229f6bc11c7b",
    MIDDLE:
        "7d456f0616c382858c946ada3f6ea8d7bc72c22b04eb62a1b566f3077acd7213",
    HELPER:
        "a40f7304e7a2b1413130fabb0ae7f9cb3dd78909159f4eeb24ebe6b7049fd220",
    PIECEWISE:
        "e30a9a5f356b0303559bd1d3c1cb7a48474e973ec97b164c00832c919f761cb7",
    INNER_ETA2:
        "78ae10ff34a195779077222f7a845a948a78e11ff905c7e5cbdb590c6d6f256e",
    CERT:
        "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def strict_json(relative: str):
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
            ValueError(f"nonfinite token in {relative}: {token}")))


def load_source():
    path = REPO / SOURCE
    spec = importlib.util.spec_from_file_location(
        "audited_heuristic_count_pencil", path)
    require(spec is not None and spec.loader is not None,
            "cannot load count-pencil source")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == path.resolve(),
            "wrong count-pencil module imported")
    return module


def validate_adjacency(matrix, counts):
    for i, left in enumerate(counts, 1):
        for j, right in enumerate(counts, 1):
            if abs(left - right) > 1 and matrix[i, j] != 0:
                raise ArithmeticError("nonadjacent outer J entry is nonzero")


def build():
    for relative, expected in PINNED.items():
        require(sha(REPO / relative) == expected,
                f"frozen MCMC input changed: {relative}")
    module = load_source()
    helper = module.H
    require(Path(module.MCMC_PATH).resolve() == (REPO / MIDDLE).resolve() and
            Path(module.M.HELPER_PATH).resolve() == (REPO / HELPER).resolve() and
            helper.K == 48 and helper.ALPHA1 == Q(103, 400) and
            helper.ETA1 == Q(97, 400) and
            helper.ALPHA2 == Q(3211, 12000) and
            helper.ETA2 == Q(3031, 12000) and
            helper.C_OUT == Q(3090, 3211),
            "helper identity or Definition-5 parameters changed")

    piecewise = strict_json(PIECEWISE)
    eta2 = strict_json(INNER_ETA2)
    cert = strict_json(CERT)
    a = [[Q(x) for x in row] for row in piecewise["I_matrix"]]
    b = [[Q(x) for x in row] for row in piecewise["kJ_matrix"]]
    b00 = b[0][0]
    b_inner_eta2 = Q(eta2["numerator_48J"])
    require(piecewise.get("parameters", {}).get("eta1") == "97/400" and
            eta2.get("parameters") == {
                "alpha": "103/400", "delta": "361/50000",
                "eta": "3031/12000", "k": 48} and
            b00 == Q(cert["exact_numerator"]) and b_inner_eta2 > b00,
            "eta1/eta2 exact inner normalizers changed")

    # Hostile fixture (i): the eta1<eta2 inner tail is strictly nonzero.
    # The importance envelope must use the eta2 form, whereas the matrix's
    # B00 uses eta1.  Replacing one by the other changes every sampled block
    # scale and is explicitly detected here.
    inner_tail = b_inner_eta2 - b00
    envelope = b_inner_eta2 + b[1][1]
    mutated_envelope = b00 + b[1][1]
    require(inner_tail > 0 and envelope != mutated_envelope and
            envelope * Q(3, 17) != mutated_envelope * Q(3, 17),
            "eta2-to-eta1 envelope mutation was not detected")

    # Hostile fixture (ii): one common-count point contributes its small
    # distinguished branch to count r, its large branch to count r+1, and
    # their product only to the adjacent (r,r+1) entry.
    exact = {"a00": np.longdouble(2), "a11_full": np.longdouble(3),
             "b00": np.longdouble(5), "b11_full": np.longdouble(7),
             "b_inner_eta2": np.longdouble(11)}
    frequency = np.zeros(49, dtype=np.longdouble)
    moments = {
        "cross": np.zeros(48, dtype=np.longdouble),
        "diagonal": np.zeros(48, dtype=np.longdouble),
        "adjacent": np.zeros(47, dtype=np.longdouble),
        "common_counts": np.zeros(48, dtype=np.longdouble),
    }
    r = 4
    small, large, inner, density = map(
        np.longdouble, (3, 5, 2, 13))
    frequency[r], frequency[r + 1], frequency[r + 2] = (.2, .3, .4)
    moments["cross"][r] = inner * small / density
    moments["cross"][r + 1] = inner * large / density
    moments["diagonal"][r] = small * small / density
    moments["diagonal"][r + 1] = large * large / density
    moments["adjacent"][r] = small * large / density
    counts = (r, r + 1, r + 2)
    _, diag_a, matrix_b = module.top_eigenvalue(
        exact, frequency, moments, counts)
    scale = exact["b_inner_eta2"] + exact["b11_full"]
    require(diag_a[1] == exact["a11_full"] * frequency[r] and
            matrix_b[0, 1] == scale * inner * small / density and
            matrix_b[0, 2] == scale * inner * large / density and
            matrix_b[1, 1] == scale * small * small / density and
            matrix_b[2, 2] == scale * large * large / density and
            matrix_b[1, 2] == matrix_b[2, 1] ==
            scale * small * large / density and
            matrix_b[1, 3] == matrix_b[3, 1] == 0,
            "small/large count placement or adjacent factor changed")
    validate_adjacency(matrix_b, counts)
    fake = matrix_b.copy()
    fake[1, 3] = fake[3, 1] = 1
    try:
        validate_adjacency(fake, counts)
    except ArithmeticError:
        nonadjacent_mutation_rejected = True
    else:
        nonadjacent_mutation_rejected = False
    require(nonadjacent_mutation_rejected,
            "fake nonadjacent entry was accepted")

    # Directly test the support helper's small/large split on a constant fiber.
    nodes, weights = np.polynomial.legendre.leggauss(9)
    exponents = (0, 2, 4, 6, 8, 10, 12, 14, 16)
    qtensor = np.zeros((2, 17, 9), dtype=np.longdouble)
    qtensor[:, 0, 0] = 1
    common_count = np.array([r, r], dtype=int)
    beta_r = helper.ld(helper.schedule_q(r))
    beta_next = helper.ld(helper.schedule_q(r + 1))
    common_sum = np.array([.05, .05], dtype=np.longdouble)
    large_sum = np.array([.04, beta_r + helper.ld(helper.DELTA) / 2],
                         dtype=np.longdouble)
    got_small, got_large = helper.marginal_support_parts(
        qtensor, common_sum, common_count, large_sum,
        helper.ld(helper.ALPHA2), helper.ld(helper.ALPHA2), exponents,
        nodes.astype(np.longdouble), weights.astype(np.longdouble), True)
    expected_small0 = min(helper.ld(helper.DELTA),
                          helper.ld(helper.ALPHA2) - common_sum[0])
    expected_large0 = max(
        np.longdouble(0),
        min(helper.ld(helper.ALPHA2) - common_sum[0],
            beta_next - large_sum[0]) - helper.ld(helper.DELTA))
    tolerance = np.longdouble("2e-17")
    require(abs(got_small[0] - expected_small0) < tolerance and
            abs(got_large[0] - expected_large0) < tolerance and
            abs(got_small[1]) < tolerance and abs(got_large[1]) < tolerance,
            "constant-fiber cap split disagrees with exact interval lengths")

    return {
        "status": "SEARCH-INSTRUMENT PASS",
        "rigorous_quotient": False,
        "checker_sha256": sha(FILE),
        "pinned": PINNED,
        "formula_checks": {
            "I_count_blocks_are_diagonal": True,
            "B00_uses_eta1": "97/400",
            "outer_involving_J_blocks_use_eta2": "3031/12000",
            "importance_envelope_is_b_inner_eta2_plus_b11_full": True,
            "factor_48_already_present_in_exact_envelope": True,
            "small_branch_maps_common_r_to_total_r": True,
            "large_branch_maps_common_r_to_total_r_plus_1": True,
            "outer_J_has_only_diagonal_and_adjacent_entries": True,
            "ordinary_symmetric_contraction_supplies_adjacent_factor_two": True,
        },
        "hostile_fixtures": {
            "eta1_for_eta2_mutation_rejected": True,
            "inner_tail_48J": str(inner_tail),
            "inner_tail_48J_positive": True,
            "fake_nonadjacent_entry_rejected": True,
            "constant_fiber_small_large_split_pass": True,
        },
        "decision": (
            "formula-level discovery instrument only; MCMC convergence, "
            "floating-point error, and any quotient sign remain non-rigorous"),
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
