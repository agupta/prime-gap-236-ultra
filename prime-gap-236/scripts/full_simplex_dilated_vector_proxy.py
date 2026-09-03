#!/usr/bin/env python3
"""Exact dilation proxy for a certified full-simplex orbit polynomial.

Given F_0(t)=sum c_(a,lam) (1-sum t)^a P_lam(t), construct
F_1(t)=F_0(c t), where c=alpha_0/alpha_1.  This stays in the same
graded-even finite basis because

  (1-c sum t)^a P_lam(c t)
    = sum_b binom(a,b) (1-c)^(a-b) c^(b+|lam|)
        (1-sum t)^b P_lam(t).

The resulting uncapped full-simplex quotient is an exact search proxy only.
The target wide support is capped, so this script does not verify a
Proposition-1 certificate and its output is never a bound on the capped
optimum.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parent
MODULE_DIR = REPO / "agents" / "small-delta-frontier"
sys.path.insert(0, str(MODULE_DIR))

import scan_bv_epsilon_fixed as scan  # noqa: E402


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dilate_vector(basis, vector, c):
    index = {label: i for i, label in enumerate(basis)}
    if len(index) != len(basis):
        raise ValueError("duplicate basis labels")
    out = [Q(0) for _ in basis]
    for coefficient, (a, lam) in zip(vector, basis):
        if not coefficient:
            continue
        homogeneous_degree = sum(lam)
        for b in range(a + 1):
            label = (b, lam)
            if label not in index:
                raise ValueError(f"dilation closure missing {label}")
            out[index[label]] += (coefficient * math.comb(a, b) *
                                  (1 - c) ** (a - b) *
                                  c ** (b + homogeneous_degree))
    return out


def forms_row(name, k, basis, vector, alpha, eta, delta):
    denominator, numerator, ni, nm, nj = scan.direct_forms(
        k, basis, vector, alpha, eta, delta)
    if denominator <= 0:
        raise ArithmeticError("nonpositive exact denominator")
    quotient = numerator / denominator
    return {
        "name": name,
        "alpha": str(alpha),
        "eta": str(eta),
        "exact_denominator": str(denominator),
        "exact_numerator": str(numerator),
        "exact_quotient": str(quotient),
        "exact_quotient_decimal": format(float(quotient), ".17g"),
        "exact_margin": str(numerator - denominator),
        "denominator_positive": True,
        "margin_positive": numerator > denominator,
        "term_counts": {"F_square": ni, "marginal": nm,
                        "marginal_square": nj},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("certificate", type=Path)
    parser.add_argument("--alpha", type=Q, required=True)
    parser.add_argument("--eta", type=Q, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not (Q(0) < args.eta < args.alpha < Q(1)):
        parser.error("require 0<eta<alpha<1")
    scan.self_test()

    certificate_bytes = args.certificate.read_bytes()
    certificate = json.loads(certificate_bytes)
    k = int(certificate["k"])
    if k != 48:
        raise ValueError("expected a k=48 certificate")
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in certificate["basis"]]
    vector = [Q(x) for x in certificate["rational_vector"]]
    if len(basis) != len(vector):
        raise ValueError("basis/vector length mismatch")
    parameters = certificate["parameters"]
    alpha0, eta0 = Q(parameters["alpha"]), Q(parameters["eta"])
    delta = Q(parameters["delta"])
    c = alpha0 / args.alpha
    if not (Q(0) < c < Q(1)):
        raise ValueError("this proxy expects target alpha > certificate alpha")

    baseline = forms_row("certified_BV_baseline", k, basis, vector,
                         alpha0, eta0, delta)
    if (baseline["exact_denominator"] != certificate["exact_denominator"] or
            baseline["exact_numerator"] != certificate["exact_numerator"]):
        raise AssertionError("baseline does not reproduce certificate")

    dilated = dilate_vector(basis, vector, c)
    matching_eta = eta0 / c
    matching = forms_row("dilated_matching_cutoff", k, basis, dilated,
                         args.alpha, matching_eta, delta)
    target = forms_row("dilated_target_cutoff", k, basis, dilated,
                       args.alpha, args.eta, delta)

    # Exact change-of-variables identities at eta_0/c.
    expected_denominator = Q(baseline["exact_denominator"]) / c ** k
    expected_numerator = Q(baseline["exact_numerator"]) / c ** (k + 1)
    if Q(matching["exact_denominator"]) != expected_denominator:
        raise AssertionError("dilated denominator scaling identity failed")
    if Q(matching["exact_numerator"]) != expected_numerator:
        raise AssertionError("dilated numerator scaling identity failed")

    output = {
        "format": "full-simplex-dilated-fixed-vector-proxy-v1",
        "status": "exact-uncapped-search-proxy",
        "rigorous_particular_forms": True,
        "analytic_support_approved": False,
        "theorem_ready": False,
        "never_implies": [
            "Proposition-1 support",
            "a lower bound on the capped target quotient",
            "an upper bound on the capped target optimum",
            "H1<=236",
        ],
        "certificate_sha256": digest(certificate_bytes),
        "script_sha256": digest(Path(__file__).read_bytes()),
        "integrator_sha256": scan.sha(
            REPO / "agents" / "exact-integrator" / "src" /
            "exact_integrator.py"),
        "dilation": {
            "c": str(c),
            "definition": "F_target(t)=F_certificate(c*t)",
            "matching_eta": str(matching_eta),
            "basis_dimension": len(basis),
            "nonzero_input": sum(x != 0 for x in vector),
            "nonzero_output": sum(x != 0 for x in dilated),
            "exact_scaling_identity_pass": True,
        },
        "rows": [baseline, matching, target],
    }
    encoded = (json.dumps(output, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    args.output.write_bytes(encoded)
    for row in output["rows"]:
        print(row["name"], row["exact_quotient_decimal"],
              "+" if row["margin_positive"] else "-")
    print("sha256", digest(encoded))


if __name__ == "__main__":
    main()
