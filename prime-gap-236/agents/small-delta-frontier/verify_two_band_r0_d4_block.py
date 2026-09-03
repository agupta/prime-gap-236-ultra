#!/usr/bin/env python3
"""Independent exact reconstruction of the root two-band R=0 D4 block.

This checker does not import ``scripts/two_band_bv_r0_block.py``.  It expands
all shell marginals as orbit polynomials in the unshifted common total U and
integrates them with the independently tested one-variable box-density core
in ``bv_two_band_r0_shell.py``.  It reconstructs all 11x11 I and 48J entries,
their canonical matrix SHA, exact LDL pivots, and the serialized particular
vector forms.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
from collections import defaultdict
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
HERE = FILE.parent
REPO = FILE.parents[2]
CORE_PATH = HERE / "bv_two_band_r0_shell.py"
CORE_SHA256 = "a9e7502d044b42863229968f037de58144fa4b110c4f5da5f62154a941d13c84"
PRODUCER_PATH = REPO / "scripts/two_band_bv_r0_block.py"
PRODUCER_SHA256 = "e1bccfc497c8193bd7e4d8c828a07e303b709f59d4223b183b9ca88c6f0b163e"
ARTIFACT_PATH = HERE / "results/two_band_bv_r0_even_D4_exact.json"
ARTIFACT_SHA256 = "0d31daa77d50353c6510fc6cb73695c7901569409214fe09bd84a29a13c577b2"


def sha(path_or_bytes):
    data = path_or_bytes if isinstance(path_or_bytes, bytes) else Path(path_or_bytes).read_bytes()
    return hashlib.sha256(data).hexdigest()


if sha(CORE_PATH) != CORE_SHA256:
    raise RuntimeError("independent box-moment core changed")
spec = importlib.util.spec_from_file_location("independent_two_band_box_core", CORE_PATH)
if spec is None or spec.loader is None:
    raise ImportError("cannot load independent two-band box core")
core = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = core
spec.loader.exec_module(core)
ei = core.ei


def orbit_poly_add(*terms):
    """Add scalar multiples of {orbit: radial-polynomial} dictionaries."""
    out = defaultdict(lambda: defaultdict(Q))
    for block, scalar in terms:
        for orbit, poly in block.items():
            for degree, coefficient in poly.items():
                out[orbit][degree] += scalar * coefficient
    return {orbit: {degree: value for degree, value in poly.items() if value}
            for orbit, poly in out.items()
            if any(poly.values())}


def marginal_as_orbit_poly(label, upper):
    raw = core.marginal_expansion([label], [Q(1)], core.K, upper)
    out = defaultdict(lambda: defaultdict(Q))
    for (orbit, power), coefficient in raw.items():
        for degree, value in core.linear_power(upper, Q(-1), power).items():
            out[orbit][degree] += coefficient * value
    return {orbit: dict(poly) for orbit, poly in out.items()}


def vector_marginal_as_orbit_poly(basis, vector, upper):
    raw = core.marginal_expansion(basis, vector, core.K, upper)
    out = defaultdict(lambda: defaultdict(Q))
    for (orbit, power), coefficient in raw.items():
        for degree, value in core.linear_power(upper, Q(-1), power).items():
            out[orbit][degree] += coefficient * value
    return {orbit: {degree: value for degree, value in poly.items() if value}
            for orbit, poly in out.items() if any(poly.values())}


def fixed_delta_marginal_as_orbit_poly(label):
    """Literal t-integral from 0 to delta, expanded in powers of U."""
    a, lam = label
    out = defaultdict(lambda: defaultdict(Q))
    for exponent, rest in ei.OneStratumSupport.split_at_distinguished(
            lam, core.K):
        for c in range(a + 1):
            coefficient = (Q(math.comb(a, c) * (-1) ** c,
                             exponent + c + 1) *
                           core.DELTA ** (exponent + c + 1))
            for degree, value in core.linear_power(1, -1, a - c).items():
                out[rest][degree] += coefficient * value
    return {orbit: {degree: value for degree, value in poly.items() if value}
            for orbit, poly in out.items() if any(poly.values())}


def multiply_orbit_radial(left, right):
    out = defaultdict(lambda: defaultdict(Q))
    for lam, p in left.items():
        for mu, q in right.items():
            radial = core.poly_mul(p, q)
            for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu):
                for degree, coefficient in radial.items():
                    out[nu][degree] += multiplicity * coefficient
    return {orbit: {degree: value for degree, value in poly.items() if value}
            for orbit, poly in out.items() if any(poly.values())}


def integrate_orbit_block(block, dimension, lo, hi):
    return sum(core.box_orbit_interval(
        dimension, core.DELTA, orbit, poly, lo, hi)
        for orbit, poly in block.items())


def shell_i_entry(left, right):
    a, lam = left
    b, mu = right
    radial = core.linear_power(1, -1, a + b)
    return sum(multiplicity * core.box_orbit_interval(
        core.K, core.DELTA, nu, radial, core.ALPHA1, core.ALPHA2)
        for nu, multiplicity in ei.multiply_monomial_orbits(lam, mu))


def exact_ldl(matrix):
    n = len(matrix)
    lower = [[Q(int(i == j)) for j in range(n)] for i in range(n)]
    pivots = []
    for j in range(n):
        pivot = matrix[j][j] - sum(
            lower[j][h] ** 2 * pivots[h] for h in range(j))
        if pivot <= 0:
            raise ArithmeticError(f"nonpositive exact pivot {j}")
        pivots.append(pivot)
        for i in range(j + 1, n):
            lower[i][j] = (matrix[i][j] - sum(
                lower[i][h] * lower[j][h] * pivots[h]
                for h in range(j))) / pivot
    return pivots


def exact_quadratic(matrix, vector):
    return sum(vector[i] * matrix[i][j] * vector[j]
               for i in range(len(vector)) for j in range(len(vector)))


def reconstruct(artifact):
    certificate_path = HERE / "bv_aquarter_B16_vector_exact.json"
    radial_path = HERE / "bv_D16_radial_two_amplitudes_exact.json"
    certificate, radial, _, _ = core.load_inputs(certificate_path, radial_path)
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in certificate["basis"]]
    vector = [Q(x) for x in certificate["rational_vector"]]
    amp_inner, amp_outer = map(Q, radial["rational_amplitudes"])
    radial_i = [[Q(x) for x in row] for row in radial["I_matrix"]]
    radial_b = [[Q(x) for x in row] for row in radial["kJ_matrix"]]
    base_i, base_b = core.exact_forms(
        radial_i[0][0], radial_i[1][1], radial_b[0][0], radial_b[0][1],
        radial_b[1][1], (amp_inner, amp_outer))

    shell_basis = ei.even_basis(4)
    serialized_basis = [(int(a), tuple(lam)) for a, lam in artifact["shell_basis"]]
    if serialized_basis != shell_basis or artifact.get("basis_dimension") != 11:
        raise ValueError("D4 shell basis changed")
    n = 1 + len(shell_basis)
    m1 = [[Q(0) for _ in range(n)] for _ in range(n)]
    m2 = [[Q(0) for _ in range(n)] for _ in range(n)]
    m1[0][0], m2[0][0] = base_i, base_b

    mr1 = vector_marginal_as_orbit_poly(basis, vector, core.ALPHA1)
    mv1 = vector_marginal_as_orbit_poly(basis, vector, core.ETA1)
    core_low = orbit_poly_add((mr1, amp_outer),
                              (mv1, amp_inner - amp_outer))
    core_high = orbit_poly_add((mr1, amp_outer))
    l0 = core.ALPHA1 - core.DELTA
    l1 = core.ALPHA2 - core.DELTA

    qa, qb = [], []
    for label in shell_basis:
        mdelta = fixed_delta_marginal_as_orbit_poly(label)
        m_r1 = marginal_as_orbit_poly(label, core.ALPHA1)
        m_r2 = marginal_as_orbit_poly(label, core.ALPHA2)
        qa.append(orbit_poly_add((mdelta, Q(1)), (m_r1, Q(-1))))
        qb.append(orbit_poly_add((m_r2, Q(1)), (m_r1, Q(-1))))

    # Constant shell marginal is a particularly transparent breakpoint test.
    if (qa[0] != {(): {0: -l0, 1: Q(1)}} or
            qb[0] != {(): {0: core.ALPHA2 - core.ALPHA1}}):
        raise AssertionError("literal constant shell marginal changed")

    for j in range(len(shell_basis)):
        cross = (
            integrate_orbit_block(multiply_orbit_radial(core_low, qa[j]),
                                  core.K - 1, l0, l1) +
            integrate_orbit_block(multiply_orbit_radial(core_low, qb[j]),
                                  core.K - 1, l1, core.ETA1) +
            integrate_orbit_block(multiply_orbit_radial(core_high, qb[j]),
                                  core.K - 1, core.ETA1, core.ETA2))
        m2[0][j + 1] = m2[j + 1][0] = core.K * cross

    for i, left in enumerate(shell_basis):
        for j in range(i + 1):
            m1[i + 1][j + 1] = m1[j + 1][i + 1] = shell_i_entry(
                left, shell_basis[j])
            shell_j = (
                integrate_orbit_block(multiply_orbit_radial(qa[i], qa[j]),
                                      core.K - 1, l0, l1) +
                integrate_orbit_block(multiply_orbit_radial(qb[i], qb[j]),
                                      core.K - 1, l1, core.ETA2))
            m2[i + 1][j + 1] = m2[j + 1][i + 1] = core.K * shell_j
    return m1, m2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    artifact_bytes = args.artifact.read_bytes()
    if sha(PRODUCER_PATH) != PRODUCER_SHA256:
        raise RuntimeError("producer source changed")
    if args.artifact.resolve() != ARTIFACT_PATH.resolve() or \
            sha(artifact_bytes) != ARTIFACT_SHA256:
        raise RuntimeError("D4 artifact identity changed")
    artifact = json.loads(artifact_bytes)
    if (artifact.get("format") !=
            "two-band-bv-radial-D16-plus-r0-shell-even-block-exact-v1" or
            artifact.get("script_sha256") != PRODUCER_SHA256 or
            artifact.get("shell_degree") != 4 or
            artifact.get("k") != core.K):
        raise ValueError("D4 artifact schema/producer mismatch")
    m1, m2 = reconstruct(artifact)
    matrix_hash = core.matrix_sha(m1, m2)
    if matrix_hash != artifact.get("matrix_sha256"):
        raise ArithmeticError("independent exact D4 matrix SHA mismatch")
    pivots = exact_ldl(m1)
    if [str(x) for x in pivots] != artifact.get("exact_I_LDL_pivots"):
        raise ArithmeticError("exact LDL pivot mismatch")
    vector = [Q(x) for x in artifact["rational_vector"]]
    denominator = exact_quadratic(m1, vector)
    numerator = exact_quadratic(m2, vector)
    expected = {
        "exact_denominator": denominator,
        "exact_numerator": numerator,
        "exact_quotient": numerator / denominator,
        "exact_margin": numerator - denominator,
    }
    for key, value in expected.items():
        if Q(artifact.get(key, "NaN")) != value:
            raise ArithmeticError(f"particular-vector {key} mismatch")
    if artifact.get("denominator_positive") != (denominator > 0) or \
            artifact.get("margin_positive") != (numerator > denominator):
        raise ArithmeticError("serialized sign mismatch")

    result = {
        "status": "AUDIT PASS",
        "scope": (
            "independent exact reconstruction of every D4 R=0 two-band I/48J "
            "entry, canonical matrix SHA, LDL pivots, and particular-vector forms; "
            "no optimality or two-band analytic theorem inferred"),
        "script_sha256": sha(FILE),
        "core_sha256": CORE_SHA256,
        "producer_sha256": PRODUCER_SHA256,
        "artifact_sha256": ARTIFACT_SHA256,
        "matrix_sha256": matrix_hash,
        "dimension": len(m1),
        "entry_count_per_symmetric_matrix": len(m1) * (len(m1) + 1) // 2,
        "exact_denominator": str(denominator),
        "exact_numerator": str(numerator),
        "exact_quotient": str(numerator / denominator),
        "exact_gain": artifact["exact_gain"],
        "denominator_positive": denominator > 0,
        "margin_positive": numerator > denominator,
    }
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode(), end="")


if __name__ == "__main__":
    main()
