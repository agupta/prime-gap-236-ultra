#!/usr/bin/env python3
"""Exact two-coordinate screen for the full-BV-core/two-band support.

The first coordinate is the already certified two-amplitude BV function

    F_1 = a F_0  (sum(t) <= eta_1),
          b F_0  (eta_1 < sum(t) < alpha_1).

The second coordinate is the constant function on the part of band 2 having
no coordinates larger than delta:

    F_2 = 1_{alpha_1 < sum(t) < alpha_2}
            1_{max_i t_i <= delta}.

Definition 5 uses eta_1 for the (1,1) J block and eta_2 for the cross and
(2,2) blocks.  This program evaluates the latter two blocks by exact
inclusion--exclusion over the common-coordinate box.  Decimal arithmetic is
used only to discover a two-dimensional eigenvector; the reported particular
vector is contracted with Fraction arithmetic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from functools import lru_cache
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
HERE = FILE.parent
REPO = FILE.parents[2]
EI_PATH = REPO / "agents/exact-integrator/src/exact_integrator.py"
sys.path.insert(0, str(EI_PATH.parent))

import exact_integrator as ei  # noqa: E402


EXPECTED_INTEGRATOR_SHA256 = (
    "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
)
EXPECTED_CERTIFICATE_SHA256 = (
    "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62"
)
EXPECTED_RADIAL_SHA256 = (
    "33fe5d555e736fe5ea3826d569477414fadd2d8a9defc2eaa35718a4f06f82ca"
)

K = 48
DELTA = Q(7, 250)
ALPHA1 = Q(103, 400)
ETA1 = Q(97, 400)
ALPHA2 = Q(521, 2000)
ETA2 = Q(491, 2000)


def sha(path_or_bytes) -> str:
    data = (path_or_bytes if isinstance(path_or_bytes, bytes)
            else Path(path_or_bytes).read_bytes())
    return hashlib.sha256(data).hexdigest()


def matrix_sha(m1, m2):
    """Canonical exact-matrix identity shared with the independent block run."""
    digest = hashlib.sha256()
    for name, matrix in (("M1", m1), ("M2", m2)):
        digest.update((name + "\n").encode("ascii"))
        for row in matrix:
            digest.update(("\t".join(str(x) for x in row) + "\n").encode("ascii"))
    return digest.hexdigest()


def poly_add(left, right):
    out = defaultdict(Q, left)
    for degree, coefficient in right.items():
        out[degree] += coefficient
    return {degree: value for degree, value in out.items() if value}


def poly_scale(poly, factor):
    return {degree: factor * coefficient for degree, coefficient in poly.items()
            if factor * coefficient}


def poly_mul(left, right):
    out = defaultdict(Q)
    for i, x in left.items():
        for j, y in right.items():
            out[i + j] += x * y
    return {degree: value for degree, value in out.items() if value}


def linear_power(constant, slope, power):
    """Coefficients of ``(constant+slope*U)^power`` by the power of U."""
    return {
        j: Q(math.comb(power, j)) * constant ** (power - j) * slope ** j
        for j in range(power + 1)
        if constant ** (power - j) * slope ** j
    } if power else {0: Q(1)}


def integrate_poly(poly, lo, hi):
    if hi <= lo:
        return Q(0)
    return sum(coefficient * (hi ** (degree + 1) - lo ** (degree + 1)) /
               (degree + 1) for degree, coefficient in poly.items())


@lru_cache(maxsize=None)
def orbit_density(dimension, nu, delta, h, max_h):
    """Density in w=sum(u)-h*delta on an inclusion--exclusion face.

    The returned dictionary is keyed by the power of w.  It includes the
    orbit size, all choices of translated upper faces, and the angular
    Dirichlet factor.  It is an independent one-variable specialization of
    GroupedEvaluator.orbit_density at large count r=0.
    """
    if dimension < 1 or len(nu) > dimension or not 0 <= h <= max_h:
        return {}
    density = defaultdict(Q)
    for multiplicity, large, small in ei._selected_exponent_splits(
            dimension, tuple(nu), 0):
        if large:
            raise AssertionError("r=0 unexpectedly selected a large exponent")
        for (hh, pdegree), coefficient in ei._small_box_dp(
                small, delta, max_h).items():
            if hh != h:
                continue
            power = pdegree + dimension - 1
            density[power] += (Q(multiplicity) * coefficient /
                               math.factorial(power))
    factor = ei.orbit_size(dimension, tuple(nu))
    return {power: factor * coefficient
            for power, coefficient in density.items() if coefficient}


def box_orbit_cumulative(dimension, delta, nu, radial_poly, endpoint):
    """Integral on ``0<=u_i<=delta, sum(u)<=endpoint``.

    ``radial_poly`` is a polynomial in the unshifted total U=sum(u).
    """
    if endpoint <= 0:
        return Q(0)
    max_h = min(dimension, int(endpoint // delta))
    answer = Q(0)
    for h in range(max_h + 1):
        upper = endpoint - h * delta
        if upper <= 0:
            continue
        # Rewrite the radial polynomial in w, where U=h*delta+w.
        shifted = defaultdict(Q)
        shift = h * delta
        for degree, coefficient in radial_poly.items():
            for j in range(degree + 1):
                shifted[j] += (coefficient * math.comb(degree, j) *
                               shift ** (degree - j))
        density = orbit_density(dimension, tuple(nu), delta, h, max_h)
        for wpow, angular in density.items():
            for degree, coefficient in shifted.items():
                total = wpow + degree
                answer += angular * coefficient * upper ** (total + 1) / \
                    (total + 1)
    return answer


def box_orbit_interval(dimension, delta, nu, radial_poly, lo, hi):
    return (box_orbit_cumulative(dimension, delta, tuple(nu), radial_poly, hi) -
            box_orbit_cumulative(dimension, delta, tuple(nu), radial_poly, lo))


def marginal_expansion(basis, vector, k, upper):
    """Return coefficients of P_rest(u)*(upper-U)^p after integrating t."""
    out = defaultdict(Q)
    for coefficient, (a, lam) in zip(vector, basis):
        if not coefficient:
            continue
        for exponent, rest in ei.OneStratumSupport.split_at_distinguished(lam, k):
            for c in range(a + 1):
                power = exponent + c + 1
                beta = Q(math.comb(a, c) * math.factorial(exponent) *
                         math.factorial(c), math.factorial(power))
                out[(rest, power)] += (coefficient * beta *
                                       (1 - upper) ** (a - c))
    return {key: value for key, value in out.items() if value}


def contract_marginal_with_shell(marginal, upper, intervals, dimension, delta):
    """Integrate one polynomial marginal times the scalar shell marginal."""
    answer = Q(0)
    for (nu, power), coefficient in marginal.items():
        residual = linear_power(upper, Q(-1), power)
        for lo, hi, shell_poly in intervals:
            answer += coefficient * box_orbit_interval(
                dimension, delta, nu, poly_mul(residual, shell_poly), lo, hi)
    return answer


def box_volume_between(dimension, delta, lo, hi):
    return box_orbit_interval(dimension, delta, (), {0: Q(1)}, lo, hi)


def shell_intervals(alpha1=ALPHA1, alpha2=ALPHA2,
                    eta2=ETA2, delta=DELTA):
    """Piecewise polynomial q(U)=length of the distinguished shell fiber."""
    x0 = alpha1 - delta
    x1 = alpha2 - delta
    if not (Q(0) < x0 < x1 < eta2 < alpha1 < alpha2):
        raise ValueError("the specialized shell breakpoint ordering failed")
    width = alpha2 - alpha1
    return (
        (x0, x1, {0: -x0, 1: Q(1)}),
        (x1, eta2, {0: width}),
    )


def clip_intervals(intervals, upper):
    out = []
    for lo, hi, poly in intervals:
        clipped = min(hi, upper)
        if clipped > lo:
            out.append((lo, clipped, poly))
    return tuple(out)


def decimal_2x2(A00, A11, B00, B01, B11, precision):
    """Largest generalized eigenvalue and x1/x0 for diagonal A."""
    if A00 <= 0 or A11 <= 0:
        raise ArithmeticError("nonpositive denominator diagonal")
    with localcontext() as ctx:
        ctx.prec = precision

        def dec(value):
            return Decimal(value.numerator) / Decimal(value.denominator)

        a = dec(B00) / dec(A00)
        d = dec(B11) / dec(A11)
        b2 = dec(B01) ** 2 / (dec(A00) * dec(A11))
        lam = (a + d + ((a - d) ** 2 + Decimal(4) * b2).sqrt()) / 2
        if B01:
            ratio = (lam * dec(A00) - dec(B00)) / dec(B01)
        else:
            ratio = Decimal(0) if a >= d else Decimal("Infinity")
        return lam, ratio


def exact_forms(A00, A11, B00, B01, B11, vector):
    x, y = vector
    denominator = x * x * A00 + y * y * A11
    numerator = x * x * B00 + 2 * x * y * B01 + y * y * B11
    return denominator, numerator


def load_inputs(certificate_path, radial_path):
    certificate_bytes = certificate_path.read_bytes()
    radial_bytes = radial_path.read_bytes()
    if sha(EI_PATH) != EXPECTED_INTEGRATOR_SHA256:
        raise RuntimeError("exact integrator source changed")
    if sha(certificate_bytes) != EXPECTED_CERTIFICATE_SHA256:
        raise RuntimeError("BV certificate bytes changed")
    if sha(radial_bytes) != EXPECTED_RADIAL_SHA256:
        raise RuntimeError("radial certificate bytes changed")
    certificate = json.loads(certificate_bytes)
    radial = json.loads(radial_bytes)
    if certificate.get("integrator_sha256") != EXPECTED_INTEGRATOR_SHA256:
        raise ValueError("certificate/integrator provenance mismatch")
    if radial.get("integrator_sha256") != EXPECTED_INTEGRATOR_SHA256 or \
            radial.get("certificate_sha256") != EXPECTED_CERTIFICATE_SHA256:
        raise ValueError("radial/certificate provenance mismatch")
    if (certificate.get("k") != K or radial.get("k") != K or
            radial.get("R") != str(ALPHA1) or radial.get("V") != str(ETA1)):
        raise ValueError("BV geometry mismatch")
    p = certificate.get("parameters", {})
    if {key: p.get(key) for key in
            ("alpha", "eta", "delta", "beta1", "beta2", "beta3plus")} != {
            "alpha": str(ALPHA1), "eta": str(ETA1), "delta": str(DELTA),
            "beta1": str(ALPHA1), "beta2": str(ALPHA1),
            "beta3plus": str(ALPHA1)}:
        raise ValueError("certificate is not the full-BV simplex")
    return certificate, radial, certificate_bytes, radial_bytes


def build_result(certificate_path, radial_path, precision=180, digits=60):
    certificate, radial, certificate_bytes, radial_bytes = load_inputs(
        certificate_path, radial_path)
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in certificate["basis"]]
    vector = [Q(x) for x in certificate["rational_vector"]]
    if len(basis) != 307 or len(vector) != len(basis):
        raise ValueError("unexpected BV basis dimension")
    amp_inner, amp_outer = map(Q, radial["rational_amplitudes"])
    imat = [[Q(x) for x in row] for row in radial["I_matrix"]]
    bmat = [[Q(x) for x in row] for row in radial["kJ_matrix"]]
    A00, B00 = exact_forms(
        imat[0][0], imat[1][1], bmat[0][0], bmat[0][1], bmat[1][1],
        (amp_inner, amp_outer))
    if (A00 != Q(radial["exact_denominator"]) or
            B00 != Q(radial["exact_numerator"])):
        raise ArithmeticError("radial particular-vector contraction failed")

    intervals = shell_intervals()
    dimension = K - 1
    marginal_R = marginal_expansion(basis, vector, K, ALPHA1)
    marginal_V = marginal_expansion(basis, vector, K, ETA1)
    cross_R = contract_marginal_with_shell(
        marginal_R, ALPHA1, intervals, dimension, DELTA)
    cross_V = contract_marginal_with_shell(
        marginal_V, ETA1, clip_intervals(intervals, ETA1), dimension, DELTA)
    B01 = K * (amp_outer * cross_R +
               (amp_inner - amp_outer) * cross_V)

    A11 = box_volume_between(K, DELTA, ALPHA1, ALPHA2)
    shell_square = Q(0)
    for lo, hi, poly in intervals:
        shell_square += box_orbit_interval(
            dimension, DELTA, (), poly_mul(poly, poly), lo, hi)
    B11 = K * shell_square
    if A11 <= 0 or B11 <= 0:
        raise ArithmeticError("outer-shell direction has nonpositive forms")

    solves = []
    for p in (precision, precision + 80):
        eigenvalue, ratio = decimal_2x2(A00, A11, B00, B01, B11, p)
        solves.append({"precision": p, "eigenvalue": str(eigenvalue),
                       "outer_over_inner": str(ratio)})
    ratio = Decimal(solves[-1]["outer_over_inner"])
    if not ratio.is_finite():
        rational_vector = (Q(0), Q(1))
    else:
        rational_vector = (Q(1), Q(format(ratio, f".{digits}E")))
    denominator, numerator = exact_forms(
        A00, A11, B00, B01, B11, rational_vector)
    if denominator <= 0:
        raise ArithmeticError("rationalized vector has nonpositive I")
    quotient = numerator / denominator
    base_quotient = B00 / A00
    imatrix = [[A00, Q(0)], [Q(0), A11]]
    bmatrix = [[B00, B01], [B01, B11]]

    return {
        "format": "full-bv-two-band-r0-shell-two-coordinate-exact-v1",
        "claim_scope": (
            "Exact finite two-coordinate forms and exact rational particular "
            "vector. Decimal eigenvalue calculations are discovery-only; the "
            "separate mixed-band equidistribution audit remains required."),
        "k": K,
        "parameters": {
            "epsilon": "3/400", "delta": str(DELTA),
            "A": ["-3/400", "1/4", "253/1000"],
            "alpha": [str(ALPHA1), str(ALPHA2)],
            "eta": [str(ETA1), str(ETA2)],
            "outer_schedule": ["43/500", "43/500", "57/500",
                               "71/500", "71/500", "71/500"],
        },
        "basis": [
            "certified radial-two-amplitude BV D16 function on band 1",
            "constant on band-2 shell with all 48 coordinates <=delta",
        ],
        "definition5_cutoffs": {
            "inner_inner": str(ETA1), "inner_outer": str(ETA2),
            "outer_outer": str(ETA2)},
        "shell_fiber_intervals": [
            {"lo": str(lo), "hi": str(hi),
             "polynomial_by_U_degree": {str(k): str(v) for k, v in poly.items()}}
            for lo, hi, poly in intervals],
        "integrator_sha256": EXPECTED_INTEGRATOR_SHA256,
        "script_sha256": sha(FILE),
        "certificate_sha256": sha(certificate_bytes),
        "radial_artifact_sha256": sha(radial_bytes),
        "marginal_term_counts": {
            "alpha1": len(marginal_R), "eta1": len(marginal_V)},
        "I_matrix": [[str(x) for x in row] for row in imatrix],
        "kJ_matrix": [[str(x) for x in row] for row in bmatrix],
        "matrix_sha256": matrix_sha(imatrix, bmatrix),
        "radial_base_exact_match": True,
        "cross_precision_solves": solves,
        "rational_vector": [str(x) for x in rational_vector],
        "exact_denominator": str(denominator),
        "exact_numerator": str(numerator),
        "exact_quotient": str(quotient),
        "exact_margin": str(numerator - denominator),
        "denominator_positive": denominator > 0,
        "margin_positive": numerator > denominator,
        "base_exact_quotient": str(base_quotient),
        "exact_gain": str(quotient - base_quotient),
        "decimal_summary": {
            "base_quotient": format(float(base_quotient), ".17g"),
            "particular_quotient": format(float(quotient), ".17g"),
            "gain": format(float(quotient - base_quotient), ".17g"),
            "outer_I_over_inner_I": format(float(A11 / A00), ".17g"),
        },
        "theorem_ready": False,
    }


def publish_fresh(path, payload):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--certificate", type=Path, default=(
        HERE / "bv_aquarter_B16_vector_exact.json"))
    parser.add_argument("--radial-artifact", type=Path, default=(
        HERE / "bv_D16_radial_two_amplitudes_exact.json"))
    parser.add_argument("--precision", type=int, default=180)
    parser.add_argument("--digits", type=int, default=60)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.precision < 100 or args.digits < 30:
        parser.error("require precision>=100 and digits>=30")
    result = build_result(args.certificate, args.radial_artifact,
                          args.precision, args.digits)
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    publish_fresh(args.output, payload)
    print(json.dumps({
        "status": result["format"],
        "base_quotient": result["decimal_summary"]["base_quotient"],
        "exact_quotient": result["decimal_summary"]["particular_quotient"],
        "exact_gain": result["decimal_summary"]["gain"],
        "margin_positive": result["margin_positive"],
        "artifact_sha256": sha(payload),
    }, indent=2))


if __name__ == "__main__":
    main()
