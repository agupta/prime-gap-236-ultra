#!/usr/bin/env python3
"""Exact fixed-vector proxy on an analytically *unapproved* full simplex.

This is a search gate for capped/two-band supports.  It removes the caps and
therefore must never be cited as a Proposition-1 support or an upper bound on
the capped optimum.  The particular-vector I and kJ forms themselves are
exact and are reconstructed from orbit identities, not a matrix dump.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parent
MODULE_DIR = REPO / "agents" / "small-delta-frontier"
sys.path.insert(0, str(MODULE_DIR))

import scan_bv_epsilon_fixed as scan  # noqa: E402


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in certificate["basis"]]
    vector = [Q(x) for x in certificate["rational_vector"]]
    if (len(basis) != len(vector) or len(basis) != len(set(basis)) or
            int(certificate["k"]) != 48):
        raise ValueError("malformed k=48 certificate")
    parameters = certificate["parameters"]
    baseline_alpha, baseline_eta = (Q(parameters["alpha"]),
                                    Q(parameters["eta"]))
    delta = Q(parameters["delta"])
    square = scan.square_orbit_polynomial({
        label: coefficient for label, coefficient in zip(basis, vector)
        if coefficient})

    rows = []
    for name, alpha, eta in (
            ("certified_BV_baseline", baseline_alpha, baseline_eta),
            ("uncapped_proxy", args.alpha, args.eta)):
        denominator, numerator, ni, nm, nj = scan.direct_forms(
            48, basis, vector, alpha, eta, delta, square)
        if denominator <= 0:
            raise ArithmeticError("nonpositive exact denominator")
        rows.append({
            "name": name,
            "alpha": str(alpha),
            "eta": str(eta),
            "exact_denominator": str(denominator),
            "exact_numerator": str(numerator),
            "exact_quotient": str(numerator / denominator),
            "exact_margin": str(numerator - denominator),
            "denominator_positive": denominator > 0,
            "margin_positive": numerator > denominator,
            "term_counts": {"F_square": ni, "marginal": nm,
                            "marginal_square": nj},
        })
    if (rows[0]["exact_denominator"] != certificate["exact_denominator"] or
            rows[0]["exact_numerator"] != certificate["exact_numerator"]):
        raise AssertionError("baseline forms do not reproduce certificate")
    output = {
        "status": "exact-fixed-vector-uncapped-search-proxy",
        "rigorous_particular_forms": True,
        "analytic_support_approved": False,
        "theorem_ready": False,
        "never_implies": [
            "Proposition-1 support",
            "upper bound on a capped variational problem",
            "H1<=236",
        ],
        "certificate_sha256": sha(certificate_bytes),
        "script_sha256": sha(Path(__file__).read_bytes()),
        "integrator_sha256": scan.sha(
            REPO / "agents" / "exact-integrator" / "src" /
            "exact_integrator.py"),
        "rows": rows,
    }
    encoded = (json.dumps(output, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    args.output.write_bytes(encoded)
    print("baseline", float(Q(rows[0]["exact_quotient"])))
    print("uncapped_proxy", float(Q(rows[1]["exact_quotient"])))
    print("proxy_margin_sign", "+" if rows[1]["margin_positive"] else "-")
    print("sha256", sha(encoded))


if __name__ == "__main__":
    main()
