#!/usr/bin/env python3
"""Independent exact-polarization / Decimal-Jacobi six-core Ritz solver.

The 7x7 matrices are exact Fractions represented by the serialized Decimal100
base, diagonal, and pair outputs.  Exact LDL proves (or rejects) positive
definiteness of the realized denominator Gram matrix.  Numerical eigenvectors
are discovery aids; one rationalized vector is contracted exactly afterward.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
FULL_SHA = "967a004ed5f02dc08d07bd9ab8f5af1050b345427327935b96d0979ae531787f"
PAIR_SHA = "32d7e86840b0ba8a859cd41b30f3242bcde3cc8518e0a598f30a304e741ca4ad"
PREFLIGHT_SHA = "a67ef637f40cfb83ff26aa45e487af1874d25cddf7ff47769c23a276996063e9"
PREFLIGHT_CODE_SHA = "e43880baff76c4af9b57c6fbc2fe2cf9884a9eb6c2d1c96f2a0f67d1d3a67e5a"
GROUPED_SHA = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
INTEGRATOR_SHA = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
COORDINATES = (10, 9, 6, 8, 5, 11)
PARAMETERS = {"alpha": Fraction(79247, 300000), "delta": Fraction(1, 100),
              "eta": Fraction(76247, 300000), "beta1": Fraction(3, 20),
              "beta2": Fraction(3, 20), "beta3plus": Fraction(97, 625)}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw, description):
    def pairs(items):
        answer = {}
        for key, value in items:
            require(type(key) is str and key not in answer,
                    f"{description}: duplicate/non-string key")
            answer[key] = value
        return answer
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(
                          ValueError(f"{description}: nonfinite {x}")))


def load(path_text, expected, description, trusted):
    path = Path(path_text).resolve(); raw = path.read_bytes()
    require(len(raw) <= 20_000_000 and sha(raw) == expected,
            f"{description}: size/SHA")
    require(path not in trusted, f"{description}: path alias")
    trusted[path] = raw
    return path, strict_json(raw, description)


def load_raw(path_text, expected, description, trusted):
    """Snapshot a non-JSON arithmetic dependency by exact bytes."""
    path = Path(path_text).resolve(); raw = path.read_bytes()
    require(len(raw) <= 20_000_000 and sha(raw) == expected,
            f"{description}: size/SHA")
    require(path not in trusted, f"{description}: path alias")
    trusted[path] = raw
    return path


def snapshot(path_text, description, trusted):
    path = Path(path_text).resolve(); raw = path.read_bytes()
    require(len(raw) <= 20_000_000 and path not in trusted,
            f"{description}: size/path alias")
    trusted[path] = raw
    return path, sha(raw), strict_json(raw, description)


def fraction(value, description):
    require(type(value) is str and value and value == value.strip(),
            f"{description}: rational string")
    try:
        return Fraction(value)
    except Exception as exc:
        raise ValueError(f"{description}: malformed rational") from exc


def validate_parameters(value, description):
    require(type(value) is dict and set(value) == set(PARAMETERS) and
            all(fraction(value[k], f"{description}.{k}") == v
                for k, v in PARAMETERS.items()), f"{description}: C10")


def replay_result(result, expected_input, counts, dimension, description):
    require(result.get("status") == "multiprecision-grouped-fixed-vector-discovery" and
            result.get("rigorous") is False and result.get("decimal_dps") == 100 and
            result.get("k") == 48 and type(result.get("workers")) is int and
            result.get("workers") == 1 and result.get("basis_dimension") == dimension and
            result.get("input_sha256") == expected_input and
            result.get("script_sha256") == GROUPED_SHA and
            result.get("integrator_sha256") == INTEGRATOR_SHA and
            result.get("i_orbit_groups") == counts["i_orbit_groups"] and
            result.get("i_faces") == counts["i_faces"] and
            result.get("marginal_components") == counts["marginal_components"] and
            result.get("j_branch_integrals") == counts["j_branch_integrals"] and
            result.get("denominator_positive") is True,
            f"{description}: result schema/provenance/counts")
    validate_parameters(result.get("parameters"), f"{description} parameters")
    values = {}
    for key in ("denominator", "j_value", "numerator", "quotient", "margin"):
        text = result.get(key)
        require(type(text) is str and text and text == text.strip(),
                f"{description}.{key}: Decimal string")
        try:
            values[key] = Decimal(text)
        except Exception as exc:
            raise ValueError(f"{description}.{key}: Decimal") from exc
        require(values[key].is_finite(), f"{description}.{key}: finite")
    with localcontext() as context:
        context.prec = 100
        expected_N = Decimal(48)*values["j_value"]
        expected_q = values["numerator"]/values["denominator"]
        expected_margin = values["numerator"]-values["denominator"]
    require(values["denominator"] > 0 and values["numerator"] == expected_N and
            values["quotient"] == expected_q and values["margin"] == expected_margin,
            f"{description}: Decimal100 identities/factor48")
    return Fraction(result["denominator"]), Fraction(result["numerator"])


def replay_stage(stage, expected_input, counts, denominator, description):
    require(stage.get("status") == "grouped-fixed-vector-I-stage" and
            stage.get("i_complete") is True and stage.get("rigorous") is False and
            stage.get("decimal_dps") == 100 and stage.get("input_sha256") == expected_input and
            stage.get("script_sha256") == GROUPED_SHA and
            stage.get("integrator_sha256") == INTEGRATOR_SHA and
            stage.get("i_orbit_groups") == counts["i_orbit_groups"] and
            stage.get("i_faces") == counts["i_faces"] and
            stage.get("denominator_positive") is True and
            fraction(stage.get("denominator"), f"{description} denominator") == denominator,
            f"{description}: stage schema/provenance/counts/value")
    validate_parameters(stage.get("parameters"), f"{description} parameters")


def exact_ldl(matrix):
    n = len(matrix); L = [[Fraction(int(i == j)) for j in range(n)] for i in range(n)]
    pivots = []
    for i in range(n):
        pivot = matrix[i][i]-sum((L[i][k]*L[i][k]*pivots[k]
                                  for k in range(i)), Fraction(0))
        require(pivot > 0, f"denominator Gram nonpositive LDL pivot {i}")
        pivots.append(pivot)
        for j in range(i+1, n):
            L[j][i] = (matrix[j][i]-sum((L[j][k]*L[i][k]*pivots[k]
                                         for k in range(i)), Fraction(0)))/pivot
    for i in range(n):
        for j in range(n):
            reconstructed = sum((L[i][k]*pivots[k]*L[j][k]
                                 for k in range(min(i, j)+1)), Fraction(0))
            require(reconstructed == matrix[i][j], "exact LDL reconstruction")
    return L, pivots


def inverse_unit_lower(L):
    n = len(L); inverse = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    for column in range(n):
        for row in range(n):
            inverse[row][column] = (Fraction(int(row == column))-
                sum((L[row][k]*inverse[k][column] for k in range(row)), Fraction(0)))
    return inverse


def multiply(A, B):
    return [[sum((A[i][k]*B[k][j] for k in range(len(B))), Fraction(0))
             for j in range(len(B[0]))] for i in range(len(A))]


def transpose(A):
    return [list(x) for x in zip(*A)]


def decimal_fraction(value):
    return Decimal(value.numerator)/Decimal(value.denominator)


def jacobi_symmetric(matrix, digits):
    n = len(matrix)
    with localcontext() as context:
        context.prec = digits+30
        A = [[+x for x in row] for row in matrix]
        V = [[Decimal(int(i == j)) for j in range(n)] for i in range(n)]
        scale = max(Decimal(1), max(abs(A[i][i]) for i in range(n)))
        tolerance = scale*(Decimal(10)**Decimal(-(digits-15)))
        rotations = 0
        for sweep in range(1000):
            changed = False
            for p in range(n):
                for q in range(p+1, n):
                    apq = A[p][q]
                    if abs(apq) <= tolerance:
                        continue
                    changed = True; rotations += 1
                    tau = (A[q][q]-A[p][p])/(2*apq)
                    if tau == 0:
                        t = Decimal(1)
                    else:
                        t = (Decimal(1) if tau > 0 else Decimal(-1))/(abs(tau)+(1+tau*tau).sqrt())
                    c = 1/(1+t*t).sqrt(); s = t*c
                    app, aqq = A[p][p], A[q][q]
                    A[p][p] = app-t*apq; A[q][q] = aqq+t*apq
                    A[p][q] = A[q][p] = Decimal(0)
                    for r in range(n):
                        if r in (p, q):
                            continue
                        arp, arq = A[r][p], A[r][q]
                        A[r][p] = A[p][r] = c*arp-s*arq
                        A[r][q] = A[q][r] = s*arp+c*arq
                    for r in range(n):
                        vrp, vrq = V[r][p], V[r][q]
                        V[r][p] = c*vrp-s*vrq; V[r][q] = s*vrp+c*vrq
            if not changed:
                break
        else:
            raise ValueError("Decimal Jacobi did not converge")
        residual = max(abs(A[i][j]) for i in range(n) for j in range(i+1, n))
        order = sorted(range(n), key=lambda i: A[i][i])
        context.prec = digits
        return ([+A[i][i] for i in order],
                [[+V[r][i] for i in order] for r in range(n)],
                +residual, rotations)


def solve_precision(A, B, L, pivots, digits):
    Linv = inverse_unit_lower(L)
    M = multiply(multiply(Linv, B), transpose(Linv))
    with localcontext() as context:
        context.prec = digits+30
        roots = [decimal_fraction(x).sqrt() for x in pivots]
        C = [[decimal_fraction(M[i][j])/(roots[i]*roots[j])
              for j in range(len(A))] for i in range(len(A))]
        eigenvalues, eigenvectors, residual, rotations = jacobi_symmetric(C, digits)
        y = [eigenvectors[i][-1] for i in range(len(A))]
        z = [y[i]/roots[i] for i in range(len(A))]
        x = [Decimal(0)]*len(A)
        for i in range(len(A)-1, -1, -1):
            x[i] = z[i]-sum((decimal_fraction(L[k][i])*x[k]
                             for k in range(i+1, len(A))), Decimal(0))
        require(x[0] != 0, "max eigenvector has zero base coordinate")
        x = [v/x[0] for v in x]
        context.prec = digits
        return {"digits": digits, "maximum_eigenvalue": str(+eigenvalues[-1]),
                "normalized_eigenvector": [str(+v) for v in x],
                "jacobi_offdiagonal_residual": str(+residual),
                "jacobi_rotations": rotations}


def quadratic(matrix, vector):
    return sum((vector[i]*matrix[i][j]*vector[j]
                for i in range(len(vector)) for j in range(len(vector))), Fraction(0))


def publish(path_text, value, trusted):
    path = Path(path_text).resolve(); require(path not in trusted, "output alias")
    payload = (json.dumps(value, indent=2)+"\n").encode(); path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT|os.O_EXCL|os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"): flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), "output regular")
        offset = 0
        while offset < len(payload):
            written = os.write(fd, payload[offset:]); require(written > 0, "short write"); offset += written
        os.fsync(fd); fs, ps = os.fstat(fd), os.stat(path, follow_symlinks=False)
        require((fs.st_dev, fs.st_ino) == (ps.st_dev, ps.st_ino) and
                path.read_bytes() == payload, "output ownership/bytes")
        for trusted_path, raw in trusted.items():
            require(trusted_path.read_bytes() == raw, f"trusted bytes changed: {trusted_path}")
    finally:
        os.close(fd)
    print(json.dumps({"status": value["status"], "output_sha256": sha(payload)}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--coordinate-manifest", required=True)
    parser.add_argument("--pair-manifest", required=True)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--grid-digits", type=int, default=80)
    args = parser.parse_args()
    require(type(args.grid_digits) is int and 50 <= args.grid_digits <= 200,
            "rationalization grid digits")
    trusted = {}
    _, full = load(args.coordinate_manifest, FULL_SHA, "coordinate manifest", trusted)
    _, pair = load(args.pair_manifest, PAIR_SHA, "pair manifest", trusted)
    _, preflight = load(args.preflight, PREFLIGHT_SHA, "preflight", trusted)
    preflight_code = HERE/"audit_core6_pair_tier.py"
    load_raw(preflight_code, PREFLIGHT_CODE_SHA, "preflight code", trusted)
    self_path = Path(__file__).resolve(); trusted[self_path] = self_path.read_bytes()
    require(preflight.get("status") == "AUDIT PASS" and preflight.get("pair_count") == 15 and
            preflight.get("pair_manifest_sha256") == PAIR_SHA and
            pair.get("pair_semantics") == "unscaled_sum" and
            pair.get("coordinates") == list(COORDINATES), "preflight/pair gate")
    entries = {x["coordinate"]: x for x in full["full_ranking"]}
    n = 7; A = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    B = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    result_hashes, stage_hashes = {}, {}
    D0 = N0 = None
    for position, coordinate in enumerate(COORDINATES, 1):
        entry = entries[coordinate]
        _, direction = load(entry["path"], entry["sha256"],
                            f"direction c{coordinate}", trusted)
        action = direction["cross_action"]
        d0, n0 = fraction(action["denominator_D0"], "D0"), fraction(action["numerator_N0"], "N0")
        if D0 is None: D0, N0 = d0, n0
        require((d0, n0) == (D0, N0), "base action mismatch")
        A[0][position] = A[position][0] = fraction(action["A_cross_a01"], "a01")
        B[0][position] = B[position][0] = fraction(action["B48_cross_b01"], "b01")
        prefix = HERE/"results/sparse_coordinate_scan_all"/f"c10_D12_sparse_c{coordinate:02d}_self_mp100"
        result_path = Path(str(prefix)+".json"); stage_path = Path(str(prefix)+".I-stage.json")
        diagonal_sha = sha(result_path.read_bytes())
        involving = [record for record in pair["pairs"]
                     if coordinate in record["coordinates"]]
        require(len(involving) == 5 and all(
                    record["diagonal_result_sha256"][
                        record["coordinates"].index(coordinate)] == diagonal_sha
                    for record in involving),
                f"positional diagonal result manifest binding c{coordinate}")
        _, rhash, result = snapshot(result_path, f"diagonal result c{coordinate}", trusted)
        _, shash, stage = snapshot(stage_path, f"diagonal stage c{coordinate}", trusted)
        counts = entry["expected_grouped_counts"]
        di, ni = replay_result(result, entry["sha256"], counts, 1,
                               f"diagonal c{coordinate}")
        replay_stage(stage, entry["sha256"], counts, di, f"diagonal c{coordinate}")
        A[position][position], B[position][position] = di, ni
        result_hashes[f"c{coordinate}"] = rhash; stage_hashes[f"c{coordinate}"] = shash
    A[0][0], B[0][0] = D0, N0
    pair_hashes = {}
    for record in pair["pairs"]:
        i, j = record["i"], record["j"]
        _, ihash, input_value = snapshot(record["input_path"], f"pair input c{i},c{j}", trusted)
        require(ihash == record["input_sha256"] and input_value.get("coordinates") == [i, j],
                f"pair input binding c{i},c{j}")
        _, shash, stage = snapshot(record["i_stage_path"], f"pair stage c{i},c{j}", trusted)
        _, rhash, result = snapshot(record["result_path"], f"pair result c{i},c{j}", trusted)
        asum, bsum = replay_result(result, ihash, record["expected_grouped_counts"], 2,
                                   f"pair c{i},c{j}")
        replay_stage(stage, ihash, record["expected_grouped_counts"], asum,
                     f"pair c{i},c{j}")
        pi, pj = COORDINATES.index(i)+1, COORDINATES.index(j)+1
        A[pi][pj] = A[pj][pi] = (asum-A[pi][pi]-A[pj][pj])/2
        B[pi][pj] = B[pj][pi] = (bsum-B[pi][pi]-B[pj][pj])/2
        pair_hashes[f"c{i}_c{j}"] = {"input": ihash, "stage": shash, "result": rhash}
    require(all(A[i][j] == A[j][i] and B[i][j] == B[j][i]
                for i in range(n) for j in range(n)), "matrix symmetry/completeness")
    L, pivots = exact_ldl(A)
    solves = [solve_precision(A, B, L, pivots, digits) for digits in (100, 160, 220)]
    eigenvalues = [Decimal(x["maximum_eigenvalue"]) for x in solves]
    require(abs(eigenvalues[0]-eigenvalues[1]) < Decimal("1e-80") and
            abs(eigenvalues[1]-eigenvalues[2]) < Decimal("1e-140"),
            "precision stability gate")
    best = [Decimal(x) for x in solves[-1]["normalized_eigenvector"]]
    grid = 10**args.grid_digits
    rational = [Fraction(1)]
    with localcontext() as context:
        context.prec = 300
        for value in best[1:]:
            integer = int((value*Decimal(grid)).to_integral_value(rounding=ROUND_HALF_EVEN))
            rational.append(Fraction(integer, grid))
    exact_D, exact_N = quadratic(A, rational), quadratic(B, rational)
    require(exact_D > 0, "rationalized vector denominator")
    exact_q = exact_N/exact_D
    with localcontext() as context:
        context.prec = 120
        exact_q_decimal = str(decimal_fraction(exact_q))
    value = {"status": "six-core-pair-ritz-independent-discovery",
             "rigorous": False, "theorem_ready": False,
             "coordinate_manifest_sha256": FULL_SHA,
             "pair_manifest_sha256": PAIR_SHA,
             "preflight_sha256": PREFLIGHT_SHA,
             "basis_order": ["base"]+[f"d{x}" for x in COORDINATES],
             "matrix_dimension": n, "pair_count": 15,
             "factor48_applied_once": True,
             "polarization": "Aij=(Asum-Aii-Ajj)/2; Bij=(B48sum-B48ii-B48jj)/2",
             "A_positive_definite_exact_LDL": True,
             "A_LDL_pivots": [str(x) for x in pivots],
             "A_matrix": [[str(x) for x in row] for row in A],
             "B48_matrix": [[str(x) for x in row] for row in B],
             "precision_runs": solves,
             "rationalization_grid_digits": args.grid_digits,
             "rationalized_vector": [str(x) for x in rational],
             "rationalized_denominator": str(exact_D),
             "rationalized_numerator": str(exact_N),
             "rationalized_quotient": str(exact_q),
             "rationalized_quotient_decimal120": exact_q_decimal,
             "rationalized_margin": str(exact_N-exact_D),
             "rationalized_margin_positive": exact_N > exact_D,
             "diagonal_result_sha256": result_hashes,
             "diagonal_stage_sha256": stage_hashes,
             "pair_artifact_sha256": pair_hashes,
             "claim_scope": "exact contraction only inside serialized Decimal100 realized matrices; no rigorous integration error bound"}
    for path, raw in trusted.items():
        require(path.read_bytes() == raw, f"trusted bytes changed before publish: {path}")
    publish(args.output, value, trusted)


if __name__ == "__main__":
    main()
