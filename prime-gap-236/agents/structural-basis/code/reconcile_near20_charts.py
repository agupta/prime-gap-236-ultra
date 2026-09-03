#!/usr/bin/env python3
"""Reconcile the two affine charts used for the near20 projective line.

This is a discovery-artifact consistency checker.  It proves, relative to the
serialized rational data, why the two reported values called ``infinity`` are
different and bounds the only actual discrepancy: the MP100 Euler residual.
It makes no exact-integral or sieve claim.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
H_PATH = ROOT / "agents/structural-basis/results/c10_D12_h12_near20_quadratic_from_mp100.json"
RAW_PATH = ROOT / "agents/small-delta-frontier/results/near20_scalar_line_independent.json"
H_SHA = "bf227a7f76bc6e54194b2e225291efde917a951b9b0958871e44a651fecfedb1"
RAW_SHA = "6046a35ccdee0e10f7e81303e984024deab0fd1b4fe23c9a39c3b02eebfc1464"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_bound(path, expected):
    data = path.read_bytes()
    require(sha(data) == expected, f"SHA mismatch: {path}")
    return json.loads(data)


def evaluate_h(coefficients, s):
    return coefficients[0] + coefficients[1] * s + coefficients[2] * s * s


def evaluate_raw(coefficients, u):
    return coefficients[0] + 2 * coefficients[1] * u + coefficients[2] * u * u


def transformed_coefficients(raw, gamma, t):
    a00, a01, a11 = raw
    return [
        a00,
        2 * (a00 * (gamma - 1) + gamma * t * a01),
        a00 * (gamma - 1) ** 2
        + 2 * gamma * t * (gamma - 1) * a01
        + (gamma * t) ** 2 * a11,
    ]


def reconcile(h_artifact, raw_artifact):
    gamma = Fraction(raw_artifact["projective_identity"]["scale"])
    t = Fraction(raw_artifact["projective_identity"]["t"])
    require(gamma != 0 and gamma != 1 and t != 0, "degenerate chart map")

    h_d = [Fraction(x) for x in h_artifact["quadratic"]["D_coefficients"]]
    h_n = [Fraction(x) for x in h_artifact["quadratic"]["N_coefficients"]]
    raw_d = [Fraction(x) for x in
             raw_artifact["raw_line_forms"]["A00_A01_A11"]]
    raw_n = [Fraction(x) for x in
             raw_artifact["raw_line_forms"]["B00_B01_B11"]]
    e_d = Fraction(raw_artifact["raw_line_forms"]["base_euler_D_error"])
    e_n = Fraction(raw_artifact["raw_line_forms"]["base_euler_N_error"])

    predicted_d = transformed_coefficients(raw_d, gamma, t)
    predicted_n = transformed_coefficients(raw_n, gamma, t)
    expected_d = [Fraction(0), 2 * (gamma - 1) * e_d,
                  -2 * (gamma - 1) * e_d]
    expected_n = [Fraction(0), 2 * (gamma - 1) * e_n,
                  -2 * (gamma - 1) * e_n]
    require([x - y for x, y in zip(h_d, predicted_d)] == expected_d,
            "D chart residual identity")
    require([x - y for x, y in zip(h_n, predicted_n)] == expected_n,
            "N chart residual identity")

    h_best = h_artifact["ranked_projective_candidates"][0]
    require(h_best["name"].startswith("stationary_"), "h best is not finite")
    s_h = Fraction(h_best["s"])
    q_h = Fraction(h_best["quotient_exact"])
    raw_roots = raw_artifact["stationary"]["finite_real_roots_with_D_positive"]
    require(raw_roots, "raw chart has no finite stationary root")
    raw_candidates = []
    for item in raw_roots:
        u = Fraction(item["u_decimal"])
        q = evaluate_raw(raw_n, u) / evaluate_raw(raw_d, u)
        raw_candidates.append((q, u))
    q_raw, u_raw = max(raw_candidates)

    # y=gamma*(theta+t*d) implies
    # theta+s*(y-theta)=lambda(s)*(theta+u(s)*d), where
    # lambda=1+(gamma-1)s and u=gamma*t*s/lambda.
    s_from_raw = u_raw / (gamma * t - u_raw * (gamma - 1))
    q_h_same_point = (evaluate_h(h_n, s_from_raw) /
                      evaluate_h(h_d, s_from_raw))
    d_residual = 2 * (gamma - 1) * e_d * s_from_raw * (1 - s_from_raw)
    n_residual = 2 * (gamma - 1) * e_n * s_from_raw * (1 - s_from_raw)

    require(q_h < 1 and q_raw < 1, "near20 line unexpectedly crosses one")
    require(abs(q_h - q_raw) < Fraction(1, 10**50),
            "stationary values disagree beyond Euler-error scale")
    require(abs(s_h - s_from_raw) < Fraction(1, 10**50),
            "stationary points disagree beyond Euler-error scale")

    return {
        "gamma": gamma,
        "t": t,
        "h_best_s": s_h,
        "raw_best_u": u_raw,
        "raw_best_mapped_h_s": s_from_raw,
        "stationary_s_difference": s_h - s_from_raw,
        "h_best_q": q_h,
        "raw_best_q": q_raw,
        "stationary_q_difference": q_h - q_raw,
        "same_point_q_difference": q_h_same_point - q_raw,
        "euler_D_relative": e_d / raw_d[0],
        "euler_N_relative": e_n / raw_n[0],
        "D_chart_residual_relative_at_raw_best":
            d_residual / evaluate_h(h_d, s_from_raw),
        "N_chart_residual_relative_at_raw_best":
            n_residual / evaluate_h(h_n, s_from_raw),
        "h_chart_infinity_q": h_n[2] / h_d[2],
        "raw_chart_infinity_q": raw_n[2] / raw_d[2],
        "h_infinity_maps_to_raw_u": gamma * t / (gamma - 1),
        "raw_infinity_maps_to_h_s": -Fraction(1, gamma - 1),
    }


def decimal(value, precision=90):
    with localcontext() as context:
        context.prec = precision
        return str(+(Decimal(value.numerator) / Decimal(value.denominator)))


def main():
    h_artifact = load_bound(H_PATH, H_SHA)
    raw_artifact = load_bound(RAW_PATH, RAW_SHA)
    result = reconcile(h_artifact, raw_artifact)
    # Rebind both artifacts after all arithmetic.
    require(sha(H_PATH.read_bytes()) == H_SHA, "h artifact changed")
    require(sha(RAW_PATH.read_bytes()) == RAW_SHA, "raw artifact changed")
    rendered = {key: decimal(value) for key, value in result.items()}
    rendered.update({
        "status": "NEAR20 CHART RECONCILIATION PASS",
        "rigorous": False,
        "identity":
            "Q_h(s)-lambda(s)^2 Q_raw(u(s))=2(gamma-1)E_Q*s*(1-s)",
        "claim_scope": "serialized MP100 discovery forms only",
        "h_artifact_sha256": H_SHA,
        "raw_artifact_sha256": RAW_SHA,
    })
    print(json.dumps(rendered, indent=2))


if __name__ == "__main__":
    main()
