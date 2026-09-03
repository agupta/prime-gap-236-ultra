#!/usr/bin/env python3
"""Exact cross-form scan of H_r=p2*1_{R=r} against a pure L/Z vector."""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

import numpy as np

from block_whiten_lz import cholesky, dec, inverse_lower
from exact_lz_integrator import c722_support, qtext
from p2_enrichment import P2Entries


def two_dimensional_q(den, a, hh, num, b, bhh):
    A = np.array([[float(den), float(a)], [float(a), float(hh)]])
    B = np.array([[float(num), float(b)], [float(b), float(bhh)]])
    d = np.sqrt(np.diag(A))
    As, Bs = A / d[:, None] / d[None, :], B / d[:, None] / d[None, :]
    L = np.linalg.cholesky(As)
    X = np.linalg.inv(L)
    C = X @ Bs @ X.T
    return float(np.linalg.eigvalsh((C + C.T) / 2)[-1])


def novelty(A, v, hh, precision=100):
    with localcontext() as ctx:
        ctx.prec = precision
        scales = [dec(A[i][i]).sqrt() for i in range(len(A))]
        As = [[dec(A[i][j]) / scales[i] / scales[j]
               for j in range(len(A))] for i in range(len(A))]
        invL = inverse_lower(cholesky(As))
        vs = [dec(v[i]) / scales[i] for i in range(len(v))]
        y = [sum((invL[i][j] * vs[j] for j in range(len(v))), Decimal(0))
             for i in range(len(v))]
        proj = sum((z * z for z in y), Decimal(0))
        return dec(hh) - proj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("matrix", type=Path)
    ap.add_argument("certificate", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--strata", help="optional comma-separated pruned scan")
    args = ap.parse_args()
    mbytes, cbytes = args.matrix.read_bytes(), args.certificate.read_bytes()
    raw, cert = json.loads(mbytes), json.loads(cbytes)
    degree, k = int(raw["parameters"]["degree"]), int(raw["parameters"]["k"])
    if k != 48 or cert.get("k") != 48 or cert.get("degree") != degree:
        raise ValueError("matrix/certificate parameter mismatch")
    base_labels = [tuple(x) for x in raw["labels"]]
    if [tuple(x) for x in cert["labels"]] != base_labels:
        raise ValueError("label mismatch")
    I = [[Q(x) for x in row] for row in raw["I"]]
    J = [[Q(x) for x in row] for row in raw["J"]]
    c = [Q(x) for x in cert["coefficients"]]
    den, jform = Q(cert["I_form"]), Q(cert["J_form"])
    num, q = k * jform, Q(cert["quotient"])
    engine = P2Entries(c722_support(k), degree)
    if tuple(base_labels) != engine.base.labels:
        raise ValueError("matrix labels disagree with exact engine")

    rows = []
    strata = (engine.s.active_strata() if args.strata is None else
              tuple(int(x) for x in args.strata.split(",") if x != ""))
    if len(set(strata)) != len(strata) or any(
            r not in engine.s.active_strata() for r in strata):
        raise ValueError("invalid/repeated scan stratum")
    for r in strata:
        h = engine.p2(r)
        relevant_i = [i for i, (rr, _, _) in enumerate(base_labels)
                      if rr == r and I[i][i] > 0]
        relevant_j = [i for i, (rr, _, _) in enumerate(base_labels)
                      if abs(rr - r) <= 1]
        iv = {i: engine.i_entry(h, engine.lz(*base_labels[i]))
              for i in relevant_i}
        jv = {i: engine.j_entry(h, engine.lz(*base_labels[i]))
              for i in relevant_j}
        a = sum(c[i] * v for i, v in iv.items())
        b = k * sum(c[i] * v for i, v in jv.items())
        hh = engine.i_entry(h, h)
        bhh = k * engine.j_entry(h, h)
        residual = b - q * a
        block = [[I[i][j] for j in relevant_i] for i in relevant_i]
        cross = [iv[i] for i in relevant_i]
        novel = novelty(block, cross, hh)
        if novel <= 0:
            raise ArithmeticError(f"nonpositive p2 novelty at r={r}: {novel}")
        score = float(float(abs(residual)) /
                      np.sqrt(float(den) * float(novel)))
        q2 = two_dimensional_q(den, a, hh, num, b, bhh)
        rows.append({
            "r": r,
            "I_cross_vector": qtext(a),
            "kJ_cross_vector": qtext(b),
            "residual_kJ_minus_qI": qtext(residual),
            "I_hh": qtext(hh),
            "kJ_hh": qtext(bhh),
            "I_novelty_decimal100": str(novel),
            "normalized_residual_score": repr(score),
            "two_vector_heuristic_q": repr(q2),
            "two_vector_gain": repr(q2 - float(q)),
        })
        print(r, "score", format(score, ".9g"), "two_gain", format(q2-float(q), ".9g"))
    rows.sort(key=lambda x: float(x["normalized_residual_score"]), reverse=True)
    out = {
        "format": "exact-p2-residual-scan-v1",
        "matrix_sha256": hashlib.sha256(mbytes).hexdigest(),
        "certificate_sha256": hashlib.sha256(cbytes).hexdigest(),
        "degree": degree,
        "base_exact_quotient": qtext(q),
        "ranking": rows,
        "note": ("cross forms and residuals exact; I novelty uses Decimal100 "
                 "block Cholesky; two-vector quotient is heuristic"),
    }
    encoded = (json.dumps(out, sort_keys=True, separators=(",", ":")) + "\n").encode()
    args.output.write_bytes(encoded)
    print("top", [(x["r"], x["normalized_residual_score"], x["two_vector_gain"])
                  for x in rows[:8]])
    print("sha256", hashlib.sha256(encoded).hexdigest())


if __name__ == "__main__":
    main()
