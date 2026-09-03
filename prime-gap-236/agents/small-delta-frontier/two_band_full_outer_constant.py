#!/usr/bin/env python3
"""Exact full-outer-schedule constant-shell screen for the two-band support.

Unlike the R=0 screen, the outer coordinate here is the constant function on
the *entire* capped second band, including one through five large coordinates.
The cross and shell J forms are evaluated by intersecting the literal four
distinguished-coordinate branches of two potentially different supports.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
HERE = FILE.parent
REPO = FILE.parents[2]
EI_DIR = REPO / "agents/exact-integrator"
sys.path[:0] = [str(EI_DIR / "src"), str(EI_DIR)]

import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import GroupedEvaluator, add_poly  # noqa: E402


INTEGRATOR_SHA256 = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
GROUPED_SHA256 = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
CERTIFICATE_SHA256 = "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62"
RADIAL_SHA256 = "33fe5d555e736fe5ea3826d569477414fadd2d8a9defc2eaa35718a4f06f82ca"

K = 48
DELTA = Q(7, 250)
ALPHA1 = Q(103, 400)
ETA1 = Q(97, 400)
ALPHA2 = Q(521, 2000)
ETA2 = Q(491, 2000)
OUTER_SCHEDULE = (Q(43, 500), Q(43, 500), Q(57, 500),
                  Q(71, 500), Q(71, 500), Q(71, 500))
BRANCHES = ("Sdelta", "Stotal", "Ltotal", "Lbig")


def sha(path_or_bytes):
    data = path_or_bytes if isinstance(path_or_bytes, bytes) else Path(path_or_bytes).read_bytes()
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class ScheduledSupport(ei.OneStratumSupport):
    schedule: tuple = ()

    @classmethod
    def make(cls, k, alpha, eta, schedule):
        schedule = tuple(schedule)
        if not schedule or len(schedule) > k or any(x <= 0 for x in schedule):
            raise ValueError("invalid schedule")
        if any(right < left or right > left + DELTA
               for left, right in zip(schedule, schedule[1:])):
            raise ValueError("schedule violates B_m <= B_(m+1) <= B_m+delta")
        return cls(k, alpha, DELTA, eta,
                   schedule[0], schedule[min(1, len(schedule) - 1)],
                   schedule[min(2, len(schedule) - 1)], schedule)

    def beta(self, r):
        if r <= 0:
            raise ValueError("beta requires a positive large count")
        return self.schedule[min(r, len(self.schedule)) - 1]


def components(basis, vector, k):
    out = defaultdict(Q)
    for coefficient, (a, lam) in zip(vector, basis):
        for exponent, rest in ei.OneStratumSupport.split_at_distinguished(lam, k):
            out[(rest, exponent, a)] += coefficient
    return tuple((rest, exponent, a, coefficient)
                 for (rest, exponent, a), coefficient in out.items()
                 if coefficient)


def branch_polynomials(support, component_list, r, h):
    """One orbit-polynomial dictionary for each literal marginal branch."""
    answer = {}
    for branch in BRANCHES:
        if support._branch_constraints(r, h, branch) is None:
            answer[branch] = {}
            continue
        block = {}
        for rest, exponent, residual, coefficient in component_list:
            poly = dict(support._marginal_poly(
                r, h, branch, exponent, residual))
            if poly:
                destination = block.setdefault(rest, defaultdict(Q))
                add_poly(destination, poly, coefficient)
        answer[branch] = {orbit: dict(poly) for orbit, poly in block.items()
                          if poly}
    return answer


def cross_marginal(left_support, left_components,
                   right_support, right_components, common_eta,
                   *, return_by_r=False):
    """Exact integral of two (possibly different) support marginals."""
    if left_support.k != right_support.k or left_support.delta != right_support.delta:
        raise ValueError("cross supports disagree in k or delta")
    dimension = left_support.k - 1
    dummy = GroupedEvaluator(left_support, [], [], Q)
    max_r = min(dimension, left_support.max_large(), right_support.max_large())
    by_r = []
    total_integrals = 0
    for r in range(max_r + 1):
        subtotal = Q(0)
        max_h = int(common_eta // left_support.delta) - r
        if max_h < 0:
            by_r.append(Q(0))
            continue
        for h in range(max_h + 1):
            outer = common_eta - (r + h) * left_support.delta
            if outer <= 0:
                continue
            left = branch_polynomials(left_support, left_components, r, h)
            right = branch_polynomials(right_support, right_components, r, h)
            for lb in BRANCHES:
                if not left[lb]:
                    continue
                lc = left_support._branch_constraints(r, h, lb)
                if lc is None:
                    continue
                for rb in BRANCHES:
                    if not right[rb]:
                        continue
                    rc = right_support._branch_constraints(r, h, rb)
                    if rc is None:
                        continue
                    constraints = lc + rc
                    combined = defaultdict(lambda: defaultdict(Q))
                    for lam, lp in left[lb].items():
                        for mu, rp in right[rb].items():
                            product = ei._poly_mul(lp, rp)
                            for nu, multiplicity in ei.multiply_monomial_orbits(
                                    lam, mu):
                                add_poly(combined[nu], product, Q(multiplicity))
                    integrand = defaultdict(Q)
                    for nu, marginal_poly in combined.items():
                        density = dummy.orbit_density(
                            dimension, nu, r, h, max_h)
                        if density:
                            add_poly(integrand,
                                     ei._poly_mul(density, marginal_poly), Q(1))
                    value = dummy.integrate_domain(
                        dict(integrand), dimension, r, outer, constraints)
                    subtotal += value
                    total_integrals += 1
            dummy.clear_face_caches(clear_marginals=True)
        dummy.clear_radial_caches()
        by_r.append(subtotal)
    answer = sum(by_r, Q(0))
    if return_by_r:
        return answer, tuple(by_r), total_integrals
    return answer


def exact_forms(A00, A11, B00, B01, B11, vector):
    x, y = vector
    return (x * x * A00 + y * y * A11,
            x * x * B00 + 2 * x * y * B01 + y * y * B11)


def decimal_solve(A00, A11, B00, B01, B11, precision):
    with localcontext() as context:
        context.prec = precision

        def d(x):
            return Decimal(x.numerator) / Decimal(x.denominator)

        aa, dd = d(B00) / d(A00), d(B11) / d(A11)
        bb = d(B01) ** 2 / (d(A00) * d(A11))
        eigenvalue = (aa + dd + ((aa - dd) ** 2 + 4 * bb).sqrt()) / 2
        ratio = ((eigenvalue * d(A00) - d(B00)) / d(B01)
                 if B01 else Decimal(0))
        return eigenvalue, ratio


def validate_sources():
    if sha(ei.__file__) != INTEGRATOR_SHA256:
        raise RuntimeError("exact integrator changed")
    grouped_path = EI_DIR / "grouped_fixed_vector.py"
    if sha(grouped_path) != GROUPED_SHA256:
        raise RuntimeError("grouped evaluator changed")


def low_k_self_test():
    """Cross evaluator agrees with the canonical recurrence, including signs."""
    schedule = (Q(7, 20), Q(37, 100), Q(39, 100))
    for k in (2, 3):
        local_schedule = schedule[:k]
        left = ScheduledSupport.make(k, Q(2, 5), Q(3, 10), local_schedule)
        right = ScheduledSupport.make(k, Q(9, 20), Q(3, 10), local_schedule)
        labels = [(0, ()), (1, ()), (0, (2,))]
        x = [Q(2), Q(-3), Q(5)]
        y = [Q(-1), Q(4), Q(2)]
        got_lr = cross_marginal(
            left, components(labels, x, k), right, components(labels, y, k),
            Q(3, 10))
        got_rl = cross_marginal(
            right, components(labels, y, k), left, components(labels, x, k),
            Q(3, 10))
        if got_lr != got_rl:
            raise AssertionError("cross-support symmetry failed")
        got_same = cross_marginal(
            left, components(labels, x, k), left, components(labels, x, k),
            Q(3, 10))
        expected_same = sum(
            x[i] * x[j] * left.basis_j(labels[i], labels[j])
            for i in range(len(labels)) for j in range(len(labels)))
        if got_same != expected_same:
            raise AssertionError("cross evaluator/canonical J mismatch")


def build_result(certificate_path, radial_path, precision=160, digits=55):
    validate_sources()
    low_k_self_test()
    cert_bytes = certificate_path.read_bytes()
    radial_bytes = radial_path.read_bytes()
    if sha(cert_bytes) != CERTIFICATE_SHA256 or sha(radial_bytes) != RADIAL_SHA256:
        raise RuntimeError("BV input bytes changed")
    certificate, radial = json.loads(cert_bytes), json.loads(radial_bytes)
    if (certificate.get("integrator_sha256") != INTEGRATOR_SHA256 or
            radial.get("certificate_sha256") != CERTIFICATE_SHA256 or
            radial.get("integrator_sha256") != INTEGRATOR_SHA256):
        raise ValueError("BV input provenance mismatch")
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in certificate["basis"]]
    vector = [Q(x) for x in certificate["rational_vector"]]
    amp_inner, amp_outer = map(Q, radial["rational_amplitudes"])
    if amp_inner != 1:
        raise ValueError("expected normalized inner radial amplitude")
    A00, B00 = Q(radial["exact_denominator"]), Q(radial["exact_numerator"])

    full_r = ei.OneStratumSupport(
        K, ALPHA1, DELTA, ETA2, ALPHA1, ALPHA1, ALPHA1)
    full_v = ei.OneStratumSupport(
        K, ETA1, DELTA, ETA2, ETA1, ETA1, ETA1)
    outer_hi = ScheduledSupport.make(K, ALPHA2, ETA2, OUTER_SCHEDULE)
    outer_lo = ScheduledSupport.make(K, ALPHA1, ETA2, OUTER_SCHEDULE)
    base_components = components(basis, vector, K)
    one_component = (((), 0, 0, Q(1)),)

    rr, rr_by_r, n_rr = cross_marginal(
        full_r, base_components, outer_hi, one_component, ETA2,
        return_by_r=True)
    rl, rl_by_r, n_rl = cross_marginal(
        full_r, base_components, outer_lo, one_component, ETA2,
        return_by_r=True)
    vr, vr_by_r, n_vr = cross_marginal(
        full_v, base_components, outer_hi, one_component, ETA2,
        return_by_r=True)
    vl, vl_by_r, n_vl = cross_marginal(
        full_v, base_components, outer_lo, one_component, ETA2,
        return_by_r=True)
    cross_j = amp_outer * (rr - rl) + (amp_inner - amp_outer) * (vr - vl)

    hh, hh_by_r, n_hh = cross_marginal(
        outer_hi, one_component, outer_hi, one_component, ETA2,
        return_by_r=True)
    hl, hl_by_r, n_hl = cross_marginal(
        outer_hi, one_component, outer_lo, one_component, ETA2,
        return_by_r=True)
    ll, ll_by_r, n_ll = cross_marginal(
        outer_lo, one_component, outer_lo, one_component, ETA2,
        return_by_r=True)
    shell_j = hh - 2 * hl + ll
    A11 = (outer_hi.basis_m1((0, ()), (0, ())) -
           outer_lo.basis_m1((0, ()), (0, ())))
    B01, B11 = K * cross_j, K * shell_j
    if A11 <= 0 or B11 <= 0:
        raise ArithmeticError("full capped shell has nonpositive form")

    solves = []
    for p in (precision, precision + 80):
        eigenvalue, ratio = decimal_solve(A00, A11, B00, B01, B11, p)
        solves.append({"precision": p, "eigenvalue": str(eigenvalue),
                       "outer_over_inner": str(ratio)})
    ratio = Decimal(solves[-1]["outer_over_inner"])
    rational_vector = (Q(1), Q(format(ratio, f".{digits}E")))
    denominator, numerator = exact_forms(
        A00, A11, B00, B01, B11, rational_vector)
    quotient, base_q = numerator / denominator, B00 / A00
    by_r_cross = [K * (amp_outer * (x - y) +
                  (amp_inner - amp_outer) * (z - w))
                  for x, y, z, w in zip(rr_by_r, rl_by_r, vr_by_r, vl_by_r)]
    by_r_shell = [K * (x - 2 * y + z)
                  for x, y, z in zip(hh_by_r, hl_by_r, ll_by_r)]
    return {
        "format": "full-bv-two-band-full-capped-shell-constant-exact-v1",
        "claim_scope": (
            "Exact two-coordinate particular-vector forms. The outer coordinate "
            "uses every allowed large-count stratum. Decimal root discovery is "
            "not an optimality certificate."),
        "k": K,
        "parameters": {
            "delta": str(DELTA), "alpha1": str(ALPHA1),
            "eta1": str(ETA1), "alpha2": str(ALPHA2), "eta2": str(ETA2),
            "outer_schedule": [str(x) for x in OUTER_SCHEDULE]},
        "basis": [
            "certified radial-two-amplitude BV D16 function on band 1",
            "constant on the complete capped band 2"],
        "integrator_sha256": INTEGRATOR_SHA256,
        "grouped_evaluator_sha256": GROUPED_SHA256,
        "script_sha256": sha(FILE),
        "certificate_sha256": sha(cert_bytes),
        "radial_artifact_sha256": sha(radial_bytes),
        "I_matrix": [[str(A00), "0"], ["0", str(A11)]],
        "kJ_matrix": [[str(B00), str(B01)], [str(B01), str(B11)]],
        "by_common_large_count": {
            "cross_kJ": [str(x) for x in by_r_cross],
            "shell_kJ": [str(x) for x in by_r_shell]},
        "branch_integral_counts": {
            "rr": n_rr, "rl": n_rl, "vr": n_vr, "vl": n_vl,
            "hh": n_hh, "hl": n_hl, "ll": n_ll},
        "low_k_signed_regression": True,
        "cross_precision_solves": solves,
        "rational_vector": [str(x) for x in rational_vector],
        "exact_denominator": str(denominator),
        "exact_numerator": str(numerator),
        "exact_quotient": str(quotient),
        "exact_gain": str(quotient - base_q),
        "exact_margin": str(numerator - denominator),
        "denominator_positive": denominator > 0,
        "margin_positive": numerator > denominator,
        "decimal_summary": {
            "base": format(float(base_q), ".17g"),
            "quotient": format(float(quotient), ".17g"),
            "gain": format(float(quotient - base_q), ".17g")},
        "theorem_ready": False,
    }


def publish(path, data):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb", closefd=True) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--certificate", type=Path,
                        default=HERE / "bv_aquarter_B16_vector_exact.json")
    parser.add_argument("--radial-artifact", type=Path,
                        default=HERE / "bv_D16_radial_two_amplitudes_exact.json")
    parser.add_argument("--precision", type=int, default=160)
    parser.add_argument("--digits", type=int, default=55)
    parser.add_argument("--self-test-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test_only:
        validate_sources()
        low_k_self_test()
        print("FULL OUTER CROSS LOW-K TEST PASS")
        return
    if args.output is None:
        parser.error("--output is required unless --self-test-only")
    if args.precision < 100 or args.digits < 30:
        parser.error("require precision>=100 and digits>=30")
    started = time.monotonic()
    result = build_result(args.certificate, args.radial_artifact,
                          args.precision, args.digits)
    result["elapsed_seconds"] = time.monotonic() - started
    result["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    data = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
            "\n").encode("ascii")
    publish(args.output, data)
    print(json.dumps({
        "format": result["format"],
        "quotient": result["decimal_summary"]["quotient"],
        "gain": result["decimal_summary"]["gain"],
        "elapsed_seconds": result["elapsed_seconds"],
        "peak_rss_kib": result["peak_rss_kib"],
        "artifact_sha256": sha(data)}, indent=2))


if __name__ == "__main__":
    main()
