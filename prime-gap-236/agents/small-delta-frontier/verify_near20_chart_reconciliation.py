#!/usr/bin/env python3
"""Exact reconciliation of raw-direction and trial-chord near20 charts."""

import argparse
import hashlib
import json
from decimal import Decimal, localcontext
from fractions import Fraction as F
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
FILES = {
    "trial": (PROJECT / "agents/structural-basis/results/c10_D12_h12_near_20pct_v3.json",
              "88c1d26f6cf46bbdd12dc000eb802cac8efe91be0ad003d6827f2ccdc6c0ff47"),
    "recovery": (PROJECT / "agents/structural-basis/results/c10_D12_band_sparse_gradient_recovered_v2.json",
                 "6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43"),
    "result": (PROJECT / "agents/structural-basis/results/c10_D12_h12_near_20pct_v3_grouped_mp100.json",
               "feb5e858a7e74a17ca9a60c79b21f079571ac9a4fabb7e3c0001ebb2efffc03f"),
    "post": (PROJECT / "agents/structural-basis/results/c10_D12_h12_near20_quadratic_from_mp100.json",
             "bf227a7f76bc6e54194b2e225291efde917a951b9b0958871e44a651fecfedb1"),
    "raw_audit": (PROJECT / "agents/small-delta-frontier/results/near20_scalar_line_independent.json",
                  "6046a35ccdee0e10f7e81303e984024deab0fd1b4fe23c9a39c3b02eebfc1464"),
}


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def dec(value, digits=100):
    with localcontext() as context:
        context.prec = digits
        return Decimal(value.numerator) / Decimal(value.denominator)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    parsed = {}
    for name, (path, expected) in FILES.items():
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected, f"{name} SHA")
        parsed[name] = json.loads(raw)
    trial, recovery, result = parsed["trial"], parsed["recovery"], parsed["result"]
    post, raw_audit = parsed["post"], parsed["raw_audit"]
    theta = list(map(F, recovery["theta"]))
    y = list(map(F, trial["compressed_theta"]))
    h = [right - left for left, right in zip(theta, y)]
    a = list(map(F, recovery["a_theta_exact_fraction_half"]))
    b = list(map(F, recovery["b_theta_exact_fraction_half"]))
    D0, N0 = F(recovery["denominator"]), F(recovery["numerator"])
    Dy, Ny = F(result["denominator"]), F(result["numerator"])
    Ah, Bh = sum(x*z for x, z in zip(h, a)), sum(x*z for x, z in zip(h, b))
    A2, B2 = Dy-D0-2*Ah, Ny-N0-2*Bh
    expected_D, expected_N = [D0, 2*Ah, A2], [N0, 2*Bh, B2]
    require(list(map(F, post["quadratic"]["D_coefficients"])) == expected_D,
            "postprocessor D chord coefficients")
    require(list(map(F, post["quadratic"]["N_coefficients"])) == expected_N,
            "postprocessor N chord coefficients")
    c = [Bh*D0-Ah*N0, B2*D0-A2*N0, B2*Ah-A2*Bh]
    require(list(map(F, post["quadratic"]["stationary_polynomial_coefficients"])) ==
            [2*x for x in c], "postprocessor stationary coefficients")

    identity = raw_audit["projective_identity"]
    t, scale = F(identity["t"]), F(identity["scale"])
    direction = list(map(F, identity["direction"]))
    require(y == [scale*(x+t*d) for x, d in zip(theta, direction)],
            "exact projective trial identity")
    # theta+s(y-theta) is proportional to theta+u*d under this exact map.
    # u=s*scale*t/(1+s*(scale-1)); inverse as below.
    raw_forms = raw_audit["raw_line_forms"]
    Araw = list(map(F, raw_forms["A00_A01_A11"]))
    Braw = list(map(F, raw_forms["B00_B01_B11"]))
    raw_infinity = Braw[2] / Araw[2]
    chord_infinity = B2 / A2
    require(F(post["ranked_projective_candidates"][1]["quotient_exact"]) ==
            chord_infinity, "chord infinity quotient")
    require(raw_infinity != chord_infinity, "the two chart infinities must differ")

    raw_best = raw_audit["stationary"]["finite_real_roots_with_D_positive"][0]
    u = Decimal(raw_best["u_decimal"])
    with localcontext() as context:
        context.prec = 100
        zd, td = dec(scale), dec(t)
        mapped_s = u / (zd*td-u*(zd-1))
        chord_s = dec(F(post["ranked_projective_candidates"][0]["s"]))
        require(abs(mapped_s-chord_s) < Decimal("1e-60"),
                "stationary points fail chart map beyond action-rounding scale")
        raw_q = Decimal(raw_best["quotient_decimal"])
        chord_q = Decimal(post["ranked_projective_candidates"][0]
                          ["quotient_decimal"])
        require(abs(raw_q-chord_q) < Decimal("1e-60"),
                "stationary values differ beyond action-rounding scale")

    output = {
        "status": "NEAR20 CHART RECONCILIATION PASS",
        "rigorous": False,
        "raw_chart": "theta+u*d",
        "chord_chart": "theta+s*(y-theta)",
        "mobius": "u=s*scale*t/(1+s*(scale-1))",
        "inverse_mobius": "s=u/(scale*t-u*(scale-1))",
        "raw_infinity_quotient": str(raw_infinity),
        "raw_infinity_decimal": str(dec(raw_infinity)),
        "chord_infinity_quotient": str(chord_infinity),
        "chord_infinity_decimal": str(dec(chord_infinity)),
        "mapped_best_s_decimal": str(mapped_s),
        "direct_chord_best_s_decimal": str(chord_s),
        "raw_best_q_decimal": str(raw_q),
        "direct_chord_best_q_decimal": str(chord_q),
        "best_q_chart_discrepancy_decimal": str(raw_q-chord_q),
        "explanation": (
            "Different affine charts send different projective points to "
            "infinity. The residual ~1e-62 stationary discrepancy comes from "
            "the separately serialized ~1e-60 Euler/action homogeneity defect."
        ),
        "claim_scope": "Decimal100 discovery forms only",
    }
    rendered = json.dumps(output, indent=2) + "\n"
    if args.output:
        path = Path(args.output).resolve()
        require(path not in {item[0].resolve() for item in FILES.values()},
                "output aliases input")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = __import__("os").open(
            path, __import__("os").O_WRONLY | __import__("os").O_CREAT |
            __import__("os").O_EXCL, 0o600)
        try:
            payload = rendered.encode()
            offset = 0
            while offset < len(payload):
                offset += __import__("os").write(descriptor, payload[offset:])
            __import__("os").fsync(descriptor)
        finally:
            __import__("os").close(descriptor)
        require(path.read_text() == rendered, "published output changed")
    print(rendered, end="")


if __name__ == "__main__":
    main()
