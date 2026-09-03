#!/usr/bin/env python3
"""Exact two-vector screen of orbit labels against a certified BV core vector.

For each label h outside the core, this computes the exact 2-by-2 pencils on
span{v,h}, where v is the stored rational core vector.  The maximizing scalar
is discovered with Decimal arithmetic and rationalized; the reported improved
quotient is then an exact Fraction contraction.  This is only a lower-bound
screen for the full core-plus-label space, never an optimality claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve().parent
EI_DIR = HERE.parent / "exact-integrator"
sys.path.insert(0, str(EI_DIR))
sys.path.insert(0, str(EI_DIR / "src"))

import exact_integrator as ei
import run_basis as rb


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label_key(label):
    a, lam = label
    return (a + sum(lam), sum(lam), len(lam), tuple(lam), a)


class MomentPool:
    def __init__(self, support, source_hash: str, inputs, output: Path):
        self.support = support
        self.params = [source_hash, support.k,
                       str(support.alpha), str(support.delta), str(support.eta),
                       str(support.beta1), str(support.beta2),
                       str(support.beta3plus)]
        self.inputs = []
        for path in inputs:
            uri = "file:" + str(path.resolve()) + "?mode=ro"
            self.inputs.append((str(path), sqlite3.connect(uri, uri=True)))
        output.parent.mkdir(parents=True, exist_ok=True)
        self.output = sqlite3.connect(output, timeout=300)
        self.output.execute("pragma busy_timeout=300000")
        self.output.execute("create table if not exists entries "
                            "(cache_key text primary key, m1 text not null, "
                            "m2 text not null)")
        self.stats = Counter()
        self.last_commit = time.monotonic()

    def cache_key(self, x, y):
        if label_key(x) < label_key(y):
            x, y = y, x
        return json.dumps([rb.MOMENT_CACHE_VERSION, self.params, x, y],
                          separators=(",", ":"))

    def get(self, x, y):
        key = self.cache_key(x, y)
        row = self.output.execute(
            "select m1,m2 from entries where cache_key=?", (key,)).fetchone()
        if row is not None:
            self.stats["hybrid_cache_hits"] += 1
            return Q(row[0]), Q(row[1])
        for name, db in self.inputs:
            row = db.execute(
                "select m1,m2 from entries where cache_key=?", (key,)).fetchone()
            if row is not None:
                self.stats["input_hits:" + name] += 1
                # Copying a source-bound exact row makes this cache useful for
                # a later full hybrid build without mutating either input.
                self.output.execute("insert into entries values (?,?,?)",
                                    (key, row[0], row[1]))
                return Q(row[0]), Q(row[1])
        m1 = self.support.basis_m1(x, y)
        m2 = self.support.k * self.support.basis_j(x, y)
        self.output.execute("insert into entries values (?,?,?)",
                            (key, str(m1), str(m2)))
        self.stats["computed"] += 1
        if time.monotonic() - self.last_commit >= 5:
            self.output.commit()
            self.last_commit = time.monotonic()
        return m1, m2

    def close(self):
        self.output.commit()
        self.output.close()
        for _, db in self.inputs:
            db.close()


def decimal_root_and_t(D, N, a, b, d, n, precision):
    # det(B-lambda A) = c2 lambda^2 + c1 lambda + c0.
    c2 = D * d - a * a
    c1 = -N * d - n * D + 2 * a * b
    c0 = N * n - b * b
    if c2 <= 0:
        raise ArithmeticError("candidate has nonpositive exact Gram novelty")
    disc = c1 * c1 - 4 * c2 * c0
    if disc < 0:
        raise ArithmeticError("2-by-2 pencil has negative exact discriminant")
    with localcontext() as ctx:
        ctx.prec = precision

        def dec(x):
            return Decimal(x.numerator) / Decimal(x.denominator)

        lam = (-dec(c1) + dec(disc).sqrt()) / (2 * dec(c2))
        first_den = dec(b) - lam * dec(a)
        second_den = dec(n) - lam * dec(d)
        if abs(first_den) >= abs(second_den):
            t = (lam * dec(D) - dec(N)) / first_den
        else:
            t = (lam * dec(a) - dec(b)) / second_den
        return str(lam), t


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("base_certificate", type=Path)
    ap.add_argument("candidate_basis", type=Path,
                    help="explicit [a,[parts]] list; core labels are ignored")
    ap.add_argument("--base-cache", type=Path, required=True)
    ap.add_argument("--input-cache", action="append", type=Path, default=[])
    ap.add_argument("--hybrid-cache", type=Path, required=True)
    ap.add_argument("--precision", type=int, default=120)
    ap.add_argument("--digits", type=int, default=35)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.precision < 80 or args.digits < 20:
        ap.error("use precision>=80 and digits>=20")

    cert_bytes = args.base_certificate.read_bytes()
    cert = json.loads(cert_bytes)
    source_path = EI_DIR / "src" / "exact_integrator.py"
    source_hash = sha(source_path)
    if cert.get("integrator_sha256") != source_hash:
        raise ValueError("base certificate integrator/source mismatch")
    if cert.get("cache_file_sha256") != sha(args.base_cache):
        raise ValueError("base cache SHA mismatch")
    p = cert["parameters"]
    support = ei.OneStratumSupport(
        int(cert["k"]), Q(p["alpha"]), Q(p["delta"]), Q(p["eta"]),
        Q(p["beta1"]), Q(p["beta2"]), Q(p["beta3plus"]))
    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in cert["basis"]]
    vector = [Q(x) for x in cert["rational_vector"]]
    if len(basis) != len(vector) or len(basis) != len(set(basis)):
        raise ValueError("malformed core basis/vector")
    candidates_bytes = args.candidate_basis.read_bytes()
    candidate_all = [(int(a), tuple(int(x) for x in lam))
                     for a, lam in json.loads(candidates_bytes)]
    if len(candidate_all) != len(set(candidate_all)):
        raise ValueError("duplicate candidate label")
    core = set(basis)
    candidates = sorted((x for x in candidate_all if x not in core),
                        key=label_key)
    if not candidates:
        raise ValueError("candidate list adds no labels")

    D, N = Q(cert["exact_denominator"]), Q(cert["exact_numerator"])
    if D <= 0 or N / D != Q(cert["exact_quotient"]):
        raise ValueError("malformed core quadratic forms")
    pool = MomentPool(support, source_hash,
                      [args.base_cache, *args.input_cache], args.hybrid_cache)
    rows = []
    try:
        for index, h in enumerate(candidates, 1):
            d, n = pool.get(h, h)
            a = b = Q(0)
            for coefficient, x in zip(vector, basis):
                if coefficient:
                    ix, jx = pool.get(h, x)
                    a += coefficient * ix
                    b += coefficient * jx
            lam_text, t_dec = decimal_root_and_t(
                D, N, a, b, d, n, args.precision)
            t = Q(format(t_dec, f".{args.digits}E"))
            out_D = D + 2 * t * a + t * t * d
            out_N = N + 2 * t * b + t * t * n
            if out_D <= 0:
                raise ArithmeticError("rationalized two-vector denominator nonpositive")
            q = out_N / out_D
            rows.append({
                "label": [h[0], list(h[1])],
                "cross_I": str(a), "cross_kJ": str(b),
                "self_I": str(d), "self_kJ": str(n),
                "decimal_2d_optimum": lam_text,
                "rational_coefficient": str(t),
                "exact_quotient": str(q),
                "exact_gain": str(q - N / D),
                "exact_quotient_decimal": format(float(q), ".17g"),
                "exact_gain_decimal": format(float(q - N / D), ".17g"),
            })
            print(f"candidate {index}/{len(candidates)} {h}: "
                  f"q={float(q):.16g} gain={float(q-N/D):.6g}",
                  file=sys.stderr, flush=True)
    finally:
        pool.close()
    rows.sort(key=lambda row: Q(row["exact_quotient"]), reverse=True)
    output = {
        "format": "bv-core-single-label-exact-screen-v1",
        "interpretation": ("Each row is an exact particular-vector lower bound "
                           "on span{stored core vector,label}; it is not the full "
                           "core-plus-label optimum."),
        "integrator_sha256": source_hash,
        "script_sha256": sha(Path(__file__)),
        "base_certificate_sha256": hashlib.sha256(cert_bytes).hexdigest(),
        "candidate_basis_sha256": hashlib.sha256(candidates_bytes).hexdigest(),
        "base_cache_sha256": sha(args.base_cache),
        "input_cache_sha256": {str(x): sha(x) for x in args.input_cache},
        "hybrid_cache_sha256": sha(args.hybrid_cache),
        "base_dimension": len(basis),
        "candidate_count": len(candidates),
        "base_exact_quotient": str(N / D),
        "decimal_precision": args.precision,
        "rationalization_significant_digits": args.digits + 1,
        "cache_stats": dict(pool.stats),
        "rows": rows,
    }
    encoded = (json.dumps(output, sort_keys=True, separators=(",", ":")) + "\n").encode()
    args.output.write_bytes(encoded)
    print("artifact_sha256", hashlib.sha256(encoded).hexdigest())
    print("top", [(r["label"], r["exact_quotient_decimal"],
                   r["exact_gain_decimal"]) for r in rows[:10]])


if __name__ == "__main__":
    main()
