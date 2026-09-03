#!/usr/bin/env python3
"""Fail-closed exact checker for a source-bound BV vector certificate.

The default mode is intentionally fast: it loads every exact moment from the
named version-2 SQLite cache without inserting missing rows.  It checks the
cache-file hash, the source hash embedded in every cache key, the reconstructed
matrix hash, and both exact quadratic forms.  ``--cache-free`` instead
recomputes every moment from ``exact_integrator.py`` and does not read SQLite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matrix_sha(m1, m2) -> str:
    h = hashlib.sha256()
    for name, matrix in (("M1", m1), ("M2", m2)):
        h.update((name + "\n").encode())
        for row in matrix:
            h.update(("\t".join(str(x) for x in row) + "\n").encode())
    return h.hexdigest()


def load_cache_fail_closed(support, basis, path: Path, source_hash: str):
    """Read, but never repair, the exact source-bound cache."""
    uri = "file:" + str(path.resolve()) + "?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    try:
        n = len(basis)
        m1 = [[Q(0) for _ in range(n)] for _ in range(n)]
        m2 = [[Q(0) for _ in range(n)] for _ in range(n)]
        params = [source_hash, support.k,
                  str(support.alpha), str(support.delta), str(support.eta),
                  str(support.beta1), str(support.beta2),
                  str(support.beta3plus)]
        for i in range(n):
            for j in range(i + 1):
                key = json.dumps(
                    [rb.MOMENT_CACHE_VERSION, params, basis[i], basis[j]],
                    separators=(",", ":"))
                rows = db.execute(
                    "select m1,m2 from entries where cache_key=?", (key,)
                ).fetchall()
                if len(rows) != 1:
                    raise ValueError(
                        f"cache key ({i},{j}) has {len(rows)} rows, expected one")
                try:
                    x, y = Q(rows[0][0]), Q(rows[0][1])
                except Exception as exc:
                    raise ValueError(f"malformed cache fraction at ({i},{j})") from exc
                m1[i][j] = m1[j][i] = x
                m2[i][j] = m2[j][i] = y
        return m1, m2
    finally:
        db.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("certificate", type=Path,
                    help="compact certificate, or run_basis result with --raw-run")
    ap.add_argument("run_result", type=Path, nargs="?",
                    help="source run for a compact certificate")
    ap.add_argument("--raw-run", action="store_true",
                    help="check the run_basis artifact's own rational vector")
    ap.add_argument("--expected-cache-sha",
                    help="required in --raw-run cache mode because old run_basis "
                         "artifacts did not store the cache-file SHA")
    ap.add_argument("--cache", type=Path)
    ap.add_argument("--cache-free", action="store_true")
    args = ap.parse_args()
    if args.cache_free == (args.cache is not None):
        ap.error("choose exactly one of --cache PATH or --cache-free")

    cert_bytes = args.certificate.read_bytes()
    cert = json.loads(cert_bytes)
    if args.raw_run:
        if args.run_result is not None:
            ap.error("--raw-run takes only one positional artifact")
        run_bytes, run = cert_bytes, cert
        if args.cache is not None and not args.expected_cache_sha:
            ap.error("--raw-run --cache requires --expected-cache-sha")
    else:
        if args.run_result is None:
            ap.error("compact certificate mode requires the source run_result")
        run_bytes = args.run_result.read_bytes()
        run = json.loads(run_bytes)
        if cert.get("format") != "bv-even-exact-vector-v1":
            raise ValueError("unexpected certificate format")

    source_path = EI_DIR / "src" / "exact_integrator.py"
    source_hash = sha256(source_path)
    run_basis_hash = sha256(Path(rb.__file__))
    if args.raw_run:
        required_equal = {
            "run integrator": (run.get("integrator_sha256"), source_hash),
        }
        expected_matrix_sha = run.get("exact_matrices_sha256")
    else:
        required_equal = {
            "integrator source": (cert.get("integrator_sha256"), source_hash),
            "run_basis source": (cert.get("run_basis_sha256"), run_basis_hash),
            "source run": (cert.get("source_run_sha256"),
                           hashlib.sha256(run_bytes).hexdigest()),
            "run integrator": (run.get("integrator_sha256"), source_hash),
            "k": (cert.get("k"), run.get("k")),
            "degree": (cert.get("degree"), run.get("degree")),
            "parameters": (cert.get("parameters"), run.get("parameters")),
            "basis": (cert.get("basis"), run.get("basis")),
            "matrix provenance": (cert.get("matrix_sha256"),
                                  run.get("exact_matrices_sha256")),
        }
        expected_matrix_sha = cert.get("matrix_sha256")
    for name, (left, right) in required_equal.items():
        if left != right:
            raise ValueError(f"{name} mismatch")

    basis = [(int(a), tuple(int(x) for x in lam))
             for a, lam in cert["basis"]]
    if len(basis) != len(set(basis)) or len(basis) != len(cert["rational_vector"]):
        raise ValueError("duplicate basis label or vector-length mismatch")
    p = cert["parameters"]
    support = ei.OneStratumSupport(
        int(cert["k"]), Q(p["alpha"]), Q(p["delta"]), Q(p["eta"]),
        Q(p["beta1"]), Q(p["beta2"]), Q(p["beta3plus"]))

    if args.cache_free:
        m1, m2 = support.matrices(basis)
        mode = "cache-free"
    else:
        assert args.cache is not None
        expected_cache_sha = (args.expected_cache_sha if args.raw_run
                              else cert.get("cache_file_sha256"))
        if expected_cache_sha != sha256(args.cache):
            raise ValueError("cache file SHA mismatch")
        m1, m2 = load_cache_fail_closed(support, basis, args.cache, source_hash)
        mode = "read-only-cache"
    got_matrix_sha = matrix_sha(m1, m2)
    if got_matrix_sha != expected_matrix_sha:
        raise ValueError("reconstructed matrix SHA mismatch")

    try:
        vector = [Q(x) for x in cert["rational_vector"]]
    except Exception as exc:
        raise ValueError("malformed rational vector") from exc
    den = ei.exact_quadratic(m1, vector)
    num = ei.exact_quadratic(m2, vector)
    if args.raw_run:
        exact_checks = {
            "denominator": (str(den), cert.get("exact_quadratic_denominator")),
            "numerator": (str(num), cert.get("exact_quadratic_numerator")),
            "quotient": (str(num / den), cert.get("exact_quotient")),
            "margin": (str(num - den), cert.get("exact_margin")),
            "denominator sign": (den > 0,
                                 cert.get("exact_denominator_positive")),
            "margin sign": (num > den, cert.get("exact_margin_positive")),
        }
    else:
        exact_checks = {
            "denominator": (str(den), cert.get("exact_denominator")),
            "numerator": (str(num), cert.get("exact_numerator")),
            "quotient": (str(num / den), cert.get("exact_quotient")),
            "margin": (str(num - den), cert.get("exact_margin")),
            "denominator sign": (den > 0, cert.get("denominator_positive")),
            "margin sign": (num > den, cert.get("margin_positive")),
        }
    for name, (got, expected) in exact_checks.items():
        if got != expected:
            raise ValueError(f"exact {name} mismatch")
    if den <= 0:
        raise ArithmeticError("certificate denominator is not positive")

    print("BV VECTOR FAIL-CLOSED AUDIT PASS")
    print("mode", mode)
    print("dimension", len(basis))
    print("matrix_sha256", got_matrix_sha)
    print("certificate_sha256", hashlib.sha256(cert_bytes).hexdigest())
    print("quotient", format(float(num / den), ".17g"))
    print("margin_sign", "positive" if num > den else "negative")


if __name__ == "__main__":
    main()
