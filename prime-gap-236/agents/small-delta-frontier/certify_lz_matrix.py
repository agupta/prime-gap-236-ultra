#!/usr/bin/env python3
"""Discovery plus exact fixed-vector certification for an exact LZ matrix.

The eigensolve is explicitly heuristic and is used only to choose coefficients.
The reported quotient is then recomputed from serialized exact Fractions.  A
separate reconstruction checker in ``verify_c722_lz.py`` does not trust those
matrix entries.
"""

from __future__ import annotations

import argparse
import json
from fractions import Fraction as Q
from pathlib import Path

import numpy as np


def qtext(x: Q) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def quadratic(M, c):
    n = len(c)
    # Exploit symmetry while also failing on a malformed nonsymmetric matrix.
    ans = Q(0)
    for i in range(n):
        if len(M[i]) != n:
            raise ValueError("non-square matrix")
        ans += c[i] * M[i][i] * c[i]
        for j in range(i):
            if M[i][j] != M[j][i]:
                raise ValueError("nonsymmetric matrix")
            ans += 2 * c[i] * M[i][j] * c[j]
    return ans


def discover(I, J, k):
    If = np.array([[float(x) for x in row] for row in I])
    Jf = np.array([[float(x) for x in row] for row in J])
    diagonal = np.diag(If)
    active = np.isfinite(diagonal) & (diagonal > 0)
    Ia, Ja = If[np.ix_(active, active)], Jf[np.ix_(active, active)]
    d = np.sqrt(np.diag(Ia))
    Is = Ia / (d[:, None] * d[None, :])
    Js = k * Ja / (d[:, None] * d[None, :])
    vals, vecs = np.linalg.eigh((Is + Is.T) / 2)
    keep = vals > max(vals[-1] * 1e-12, 1e-13)
    W = vecs[:, keep] / np.sqrt(vals[keep])
    op = W.T @ Js @ W
    eig, evec = np.linalg.eigh((op + op.T) / 2)
    z = W @ evec[:, -1]
    ca = z / d
    c = np.zeros(len(active))
    c[active] = ca
    return float(eig[-1]), int(np.sum(active)), int(np.sum(keep)), vals, c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("matrix", type=Path)
    ap.add_argument("--digits", type=int, default=14)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    raw = json.loads(args.matrix.read_text())
    if raw.get("format") != "exact-lz-matrices-v1":
        raise ValueError("wrong matrix format")
    I = [[Q(x) for x in row] for row in raw["I"]]
    J = [[Q(x) for x in row] for row in raw["J"]]
    labels = [tuple(x) for x in raw["labels"]]
    if len(I) != len(J) or len(I) != len(labels):
        raise ValueError("dimension mismatch")
    k = int(raw["parameters"]["k"])
    estimate, ndiag, rank, ivals, cf = discover(I, J, k)
    # Decimal scientific notation is an exact rationalization, retaining the
    # dynamic range of rare strata without an arbitrary common float scale.
    c = [Q(format(float(x), f".{args.digits}e")) if x else Q(0) for x in cf]
    den = quadratic(I, c)
    jform = quadratic(J, c)
    num = k * jform
    if den <= 0:
        raise ArithmeticError("nonpositive exact I form")
    quotient = num / den
    gap = den - num
    out = {
        "format": "exact-lz-vector-v1",
        "matrix_sha256": __import__("hashlib").sha256(args.matrix.read_bytes()).hexdigest(),
        "k": k,
        "degree": int(raw["parameters"]["degree"]),
        "labels": [list(x) for x in labels],
        "coefficients": [qtext(x) for x in c],
        "I_form": qtext(den),
        "J_form": qtext(jform),
        "kJ_form": qtext(num),
        "I_minus_kJ": qtext(gap),
        "quotient": qtext(quotient),
        "heuristic_eigenvalue": repr(estimate),
        "positive_diagonals": ndiag,
        "numerical_retained_rank": rank,
        "rationalization_significant_digits": args.digits,
    }
    encoded = (json.dumps(out, sort_keys=True, separators=(",", ":")) + "\n").encode()
    args.output.write_bytes(encoded)
    print("HEURISTIC eig", repr(estimate), "active", ndiag, "rank", rank)
    print("exact quotient decimal", format(float(quotient), ".17g"))
    print("exact quotient", qtext(quotient))
    print("exact I-kJ sign/bits", "positive" if gap > 0 else "negative" if gap < 0 else "zero",
          abs(gap.numerator).bit_length(), gap.denominator.bit_length())
    print("wrote", args.output)
    print("sha256", __import__("hashlib").sha256(encoded).hexdigest())


if __name__ == "__main__":
    main()
