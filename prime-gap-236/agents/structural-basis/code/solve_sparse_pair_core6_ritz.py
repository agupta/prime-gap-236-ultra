#!/usr/bin/env python3
"""Fail-closed reconstruction of the serialized MP100 six-core Ritz pencil.

The output is exact relative to the serialized Decimal forms, but those forms
are discovery values, not rigorous integrals.  The solver never infers positive
definiteness: it verifies the particular denominator matrix by exact Fraction
LDL before applying two independent Decimal-precision Jacobi solves.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


PAIR_MANIFEST_SHA = "32d7e86840b0ba8a859cd41b30f3242bcde3cc8518e0a598f30a304e741ca4ad"
PAIR_BUILDER_SHA = "ac8186bd7d6e3b569e0b02b4385f8b55f9e5abb4b96cd89f68cef217fe9d2667"
COORDINATE_MANIFEST_SHA = "967a004ed5f02dc08d07bd9ab8f5af1050b345427327935b96d0979ae531787f"
PREFLIGHT_SHA = "38a5963fa24827fbe83593fc1dd663666cf9cc43363e74704969c138be588c25"
CORE_AUDIT_SHA = "88bdbf0de9c4cac7ce0a81cda7978f21e15d36d52c7df12bd80a294943114077"
GROUPED_SHA = "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
INTEGRATOR_SHA = "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
ORDER = (10, 9, 6, 8, 5, 11)
PARAMETERS = {"alpha": "79247/300000", "delta": "1/100",
              "eta": "76247/300000", "beta1": "3/20",
              "beta2": "3/20", "beta3plus": "97/625"}
RESULT_KEYS = {
    "status", "rigorous", "decimal_dps", "input_json", "k", "parameters",
    "basis_dimension", "workers", "i_orbit_groups", "i_faces",
    "marginal_components", "j_branch_integrals", "input_sha256",
    "i_seconds", "j_seconds", "total_seconds", "peak_rss_kib",
    "child_peak_rss_kib", "peak_rss_note", "denominator_positive",
    "margin_positive", "denominator", "j_value", "numerator", "quotient",
    "quotient_decimal_display", "margin", "script_sha256",
    "integrator_sha256",
}
STAGE_KEYS = {
    "status", "i_complete", "rigorous", "decimal_dps", "input_json",
    "input_sha256", "script_sha256", "integrator_sha256", "parameters",
    "i_orbit_groups", "i_faces", "i_seconds", "denominator_positive",
    "denominator", "peak_rss_kib", "child_peak_rss_kib",
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw, what):
    def pairs(items):
        out = {}
        for key, value in items:
            require(type(key) is str and key not in out,
                    f"{what}: duplicate/non-string key")
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ValueError(f"{what}: nonfinite {token}")))


def load(path, expected_sha, what):
    path = Path(path).resolve()
    raw = path.read_bytes()
    require(sha(raw) == expected_sha, f"{what}: SHA mismatch")
    return path, raw, strict_json(raw, what)


def q(value, what="rational"):
    require(type(value) is str and value and value == value.strip(),
            f"{what}: rational string")
    try:
        return Fraction(value)
    except Exception as exc:
        raise ValueError(f"{what}: malformed rational") from exc


def exact_ldl_positive(matrix):
    """Return exact unit-lower L and pivots, rejecting non-SPD A."""
    n = len(matrix)
    require(n and all(len(row) == n for row in matrix), "LDL dimensions")
    require(all(matrix[i][j] == matrix[j][i]
                for i in range(n) for j in range(n)), "LDL symmetry")
    lower = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    pivots = [Fraction(0) for _ in range(n)]
    for i in range(n):
        lower[i][i] = Fraction(1)
        pivot = matrix[i][i]-sum(lower[i][k]*lower[i][k]*pivots[k]
                                 for k in range(i))
        require(pivot > 0, f"denominator matrix is not SPD at pivot {i}")
        pivots[i] = pivot
        for j in range(i+1, n):
            numerator = matrix[j][i]-sum(lower[j][k]*lower[i][k]*pivots[k]
                                          for k in range(i))
            lower[j][i] = numerator/pivot
    return lower, pivots


def matmul(left, right):
    rows, inner, cols = len(left), len(right), len(right[0])
    require(all(len(row) == inner for row in left) and
            all(len(row) == cols for row in right), "matmul dimensions")
    return [[sum(left[i][k]*right[k][j] for k in range(inner))
             for j in range(cols)] for i in range(rows)]


def transpose(matrix):
    return [list(row) for row in zip(*matrix)]


def inverse_lower(lower):
    n = len(lower)
    inverse = [[Decimal(0) for _ in range(n)] for _ in range(n)]
    for column in range(n):
        for i in range(n):
            rhs = Decimal(1) if i == column else Decimal(0)
            inverse[i][column] = (rhs-sum(lower[i][k]*inverse[k][column]
                                           for k in range(i)))/lower[i][i]
    return inverse


def jacobi_symmetric(matrix, precision):
    n = len(matrix)
    a = [row[:] for row in matrix]
    vectors = [[Decimal(1) if i == j else Decimal(0) for j in range(n)]
               for i in range(n)]
    tolerance = Decimal(10) ** Decimal(-(precision-25))
    max_iterations = 10000
    for iteration in range(max_iterations):
        p, r = max(((i, j) for i in range(n) for j in range(i+1, n)),
                   key=lambda ij: abs(a[ij[0]][ij[1]]))
        off = a[p][r]
        if abs(off) <= tolerance:
            return [a[i][i] for i in range(n)], vectors, iteration, abs(off)
        tau = (a[r][r]-a[p][p])/(2*off)
        sign = Decimal(1) if tau >= 0 else Decimal(-1)
        t = sign/(abs(tau)+(Decimal(1)+tau*tau).sqrt())
        cosine = Decimal(1)/(Decimal(1)+t*t).sqrt()
        sine = t*cosine
        app, arr = a[p][p], a[r][r]
        for k in range(n):
            if k in (p, r):
                continue
            akp, akr = a[k][p], a[k][r]
            a[k][p] = a[p][k] = cosine*akp-sine*akr
            a[k][r] = a[r][k] = sine*akp+cosine*akr
        a[p][p] = cosine*cosine*app-2*sine*cosine*off+sine*sine*arr
        a[r][r] = sine*sine*app+2*sine*cosine*off+cosine*cosine*arr
        a[p][r] = a[r][p] = Decimal(0)
        for k in range(n):
            vkp, vkr = vectors[k][p], vectors[k][r]
            vectors[k][p] = cosine*vkp-sine*vkr
            vectors[k][r] = sine*vkp+cosine*vkr
    raise ValueError("Jacobi iteration limit")


def solve_generalized(A_fraction, B_fraction, precision):
    exact_ldl_positive(A_fraction)
    n = len(A_fraction)
    with localcontext() as context:
        context.prec = precision
        convert = lambda x: Decimal(x.numerator)/Decimal(x.denominator)
        A = [[convert(value) for value in row] for row in A_fraction]
        B = [[convert(value) for value in row] for row in B_fraction]
        lower = [[Decimal(0) for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(i+1):
                residual = A[i][j]-sum(lower[i][k]*lower[j][k]
                                        for k in range(j))
                if i == j:
                    require(residual > 0, "Decimal Cholesky pivot")
                    lower[i][j] = residual.sqrt()
                else:
                    lower[i][j] = residual/lower[j][j]
        inverse = inverse_lower(lower)
        transformed = matmul(matmul(inverse, B), transpose(inverse))
        # Roundoff should not be hidden by trusting one triangle.
        asymmetry = max(abs(transformed[i][j]-transformed[j][i])
                        for i in range(n) for j in range(n))
        require(asymmetry < Decimal(10) ** Decimal(-(precision-20)),
                "transformed symmetry loss")
        transformed = [[(transformed[i][j]+transformed[j][i])/2
                        for j in range(n)] for i in range(n)]
        eigenvalues, eigenvectors, iterations, last_off = jacobi_symmetric(
            transformed, precision)
        index = max(range(n), key=lambda i: eigenvalues[i])
        value = eigenvalues[index]
        y = [eigenvectors[i][index] for i in range(n)]
        # L^T x = y.
        x = [Decimal(0) for _ in range(n)]
        for i in range(n-1, -1, -1):
            x[i] = (y[i]-sum(lower[k][i]*x[k] for k in range(i+1, n)))/lower[i][i]
        scale = max(abs(value) for value in x)
        require(scale > 0, "zero generalized eigenvector")
        x = [value/scale for value in x]
        Ax = [sum(A[i][j]*x[j] for j in range(n)) for i in range(n)]
        Bx = [sum(B[i][j]*x[j] for j in range(n)) for i in range(n)]
        residual = max(abs(Bx[i]-value*Ax[i]) for i in range(n))
        norm = max(max(abs(v) for v in Ax), max(abs(v) for v in Bx), Decimal(1))
        return {"eigenvalue": value, "vector": x,
                "relative_residual": residual/norm,
                "transformed_asymmetry": asymmetry,
                "jacobi_iterations": iterations, "last_offdiagonal": last_off}


def quadratic(matrix, vector):
    return sum(vector[i]*matrix[i][j]*vector[j]
               for i in range(len(vector)) for j in range(len(vector)))


def validate_grouped_pair(entry, payload, stage, result):
    require(set(stage) == STAGE_KEYS and set(result) == RESULT_KEYS,
            "pair output exact schemas")
    counts = entry["expected_grouped_counts"]
    require(stage["status"] == "grouped-fixed-vector-I-stage" and
            stage["i_complete"] is True and stage["rigorous"] is False and
            result["status"] == "multiprecision-grouped-fixed-vector-discovery" and
            result["rigorous"] is False and
            stage["decimal_dps"] == result["decimal_dps"] == 100 and
            stage["input_sha256"] == result["input_sha256"] == entry["input_sha256"] and
            stage["script_sha256"] == result["script_sha256"] == GROUPED_SHA and
            stage["integrator_sha256"] == result["integrator_sha256"] == INTEGRATOR_SHA and
            stage["parameters"] == result["parameters"] == PARAMETERS and
            stage["i_orbit_groups"] == result["i_orbit_groups"] == counts["i_orbit_groups"] and
            stage["i_faces"] == result["i_faces"] == counts["i_faces"] and
            result["marginal_components"] == counts["marginal_components"] and
            result["j_branch_integrals"] == counts["j_branch_integrals"] and
            result["basis_dimension"] == payload["basis_dimension"] == 2 and
            result["workers"] == 1 and
            stage["denominator"] == result["denominator"] and
            stage["denominator_positive"] is result["denominator_positive"] is True,
            "pair provenance/count/status gate")
    with localcontext() as context:
        context.prec = 100
        D, J = Decimal(result["denominator"]), Decimal(result["j_value"])
        N = Decimal(48)*J
        quotient, margin = N/D, N-D
        require(str(N) == result["numerator"] and
                str(quotient) == result["quotient"] and
                str(margin) == result["margin"] and
                result["margin_positive"] is (margin > 0) and
                result["quotient_decimal_display"] == float(quotient),
                "pair Decimal100 replay")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair-manifest", required=True)
    parser.add_argument("--pair-builder", required=True)
    parser.add_argument("--coordinate-manifest", required=True)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--core-audit", required=True)
    parser.add_argument("--diagonal-results-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    pair_path, pair_raw, pair_manifest = load(
        args.pair_manifest, PAIR_MANIFEST_SHA, "pair manifest")
    builder_path = Path(args.pair_builder).resolve()
    builder_raw = builder_path.read_bytes()
    require(sha(builder_raw) == PAIR_BUILDER_SHA, "pair builder SHA")
    coordinate_path, coordinate_raw, coordinate_manifest = load(
        args.coordinate_manifest, COORDINATE_MANIFEST_SHA, "coordinate manifest")
    preflight_path, preflight_raw, preflight = load(
        args.preflight, PREFLIGHT_SHA, "preflight")
    core_path, core_raw, core = load(args.core_audit, CORE_AUDIT_SHA, "core audit")
    require(pair_manifest.get("status") ==
            "c10-D12-sparse-core6-polarization-tier" and
            pair_manifest.get("rigorous") is False and
            pair_manifest.get("theorem_ready") is False and
            pair_manifest.get("coordinates") == list(ORDER) and
            pair_manifest.get("pair_semantics") == "unscaled_sum" and
            pair_manifest.get("ritz", {}).get("continuation_gate_value") == "1/10000" and
            pair_manifest.get("provenance", {}).get("builder_sha256") == PAIR_BUILDER_SHA and
            preflight.get("status") == core.get("status") == "AUDIT PASS",
            "package verdict/provenance")
    entries = {item["coordinate"]: item for item in coordinate_manifest["full_ranking"]}
    core_records = {item["coordinate"]: item for item in core["records"]}
    require(set(core_records) == set(range(12)), "core audit coverage")
    trusted = {pair_path: pair_raw, builder_path: builder_raw,
               coordinate_path: coordinate_raw, preflight_path: preflight_raw,
               core_path: core_raw}

    n = 1+len(ORDER)
    A = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    B = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    diagonal_dir = Path(args.diagonal_results_dir).resolve()
    D0 = N0 = None
    diagonal_forms = {}
    direction_payloads = {}
    for offset, coordinate in enumerate(ORDER, 1):
        direction_path = Path(entries[coordinate]["path"]).resolve()
        direction_raw = direction_path.read_bytes()
        require(sha(direction_raw) == entries[coordinate]["sha256"],
                f"d{coordinate}: direction SHA")
        direction = strict_json(direction_raw, f"d{coordinate}")
        direction_payloads[coordinate] = direction
        trusted[direction_path] = direction_raw
        result_path = diagonal_dir/f"c10_D12_sparse_c{coordinate:02d}_self_mp100.json"
        result_raw = result_path.read_bytes()
        require(sha(result_raw) == core_records[coordinate]["result_sha256"],
                f"d{coordinate}: diagonal result SHA")
        result = strict_json(result_raw, f"d{coordinate} diagonal")
        trusted[result_path] = result_raw
        Ai, Bi = q(result["denominator"]), q(result["numerator"])
        diagonal_forms[coordinate] = (Ai, Bi)
        A[offset][offset], B[offset][offset] = Ai, Bi
        cross = direction["cross_action"]
        this_D0, this_N0 = q(cross["denominator_D0"]), q(cross["numerator_N0"])
        if D0 is None:
            D0, N0 = this_D0, this_N0
        require((this_D0, this_N0) == (D0, N0), "base form mismatch")
        A[0][offset] = A[offset][0] = q(cross["A_cross_a01"])
        B[0][offset] = B[offset][0] = q(cross["B48_cross_b01"])
    require(D0 is not None and N0 is not None and D0 > N0 > 0, "base forms")
    A[0][0], B[0][0] = D0, N0

    pair_results = []
    seen = set()
    index = {coordinate: i+1 for i, coordinate in enumerate(ORDER)}
    for entry in pair_manifest["pairs"]:
        coordinates = tuple(entry["coordinates"])
        require(coordinates == (entry["i"], entry["j"]) and
                coordinates[0] in index and coordinates[1] in index and
                tuple(sorted(coordinates)) not in seen,
                "pair coordinate coverage/duplicate")
        seen.add(tuple(sorted(coordinates)))
        input_path = Path(entry["input_path"]).resolve()
        input_raw = input_path.read_bytes()
        require(sha(input_raw) == entry["input_sha256"], "pair input SHA")
        payload = strict_json(input_raw, "pair input")
        left, right = (direction_payloads[x] for x in coordinates)
        require(payload["combination"] == "unscaled signed sum d_i+d_j" and
                payload["basis"] == left["basis"]+right["basis"] and
                payload["rational_vector"] ==
                left["rational_vector"]+right["rational_vector"] and
                payload["expected_grouped_counts"] == entry["expected_grouped_counts"],
                "pair exact sum reconstruction")
        stage_path, result_path = Path(entry["i_stage_path"]).resolve(), Path(
            entry["result_path"]).resolve()
        stage_raw, result_raw = stage_path.read_bytes(), result_path.read_bytes()
        stage, result = strict_json(stage_raw, "pair stage"), strict_json(
            result_raw, "pair result")
        validate_grouped_pair(entry, payload, stage, result)
        trusted.update({input_path: input_raw, stage_path: stage_raw,
                        result_path: result_raw})
        Ai, Bi = diagonal_forms[coordinates[0]]
        Aj, Bj = diagonal_forms[coordinates[1]]
        Aij = (q(result["denominator"])-Ai-Aj)/2
        Bij = (q(result["numerator"])-Bi-Bj)/2
        ii, jj = index[coordinates[0]], index[coordinates[1]]
        A[ii][jj] = A[jj][ii] = Aij
        B[ii][jj] = B[jj][ii] = Bij
        pair_results.append({
            "coordinates": list(coordinates), "input_sha256": sha(input_raw),
            "i_stage_sha256": sha(stage_raw), "result_sha256": sha(result_raw),
            "Aij": str(Aij), "Bij": str(Bij),
            "total_seconds": result["total_seconds"],
        })
    require(len(seen) == 15, "incomplete pair clique")
    _, pivots = exact_ldl_positive(A)
    low, high = solve_generalized(A, B, 120), solve_generalized(A, B, 190)
    with localcontext() as context:
        context.prec = 115
        require(abs(low["eigenvalue"]-high["eigenvalue"]) < Decimal("1e-105"),
                "two-precision eigenvalue stability")
        require(low["relative_residual"] < Decimal("1e-90") and
                high["relative_residual"] < Decimal("1e-155"),
                "generalized eigen residual")
    # Treat the high-precision Decimal vector as an exact rational trial.
    rational_vector = [Fraction(str(value)) for value in high["vector"]]
    denominator = quadratic(A, rational_vector)
    numerator = quadratic(B, rational_vector)
    require(denominator > 0, "particular-vector denominator")
    quotient = numerator/denominator
    base = N0/D0
    gain = quotient-base
    continuation = gain >= Fraction(1, 10000)
    # Exact relative residual of the rationalized particular vector.
    residual = [sum(B[i][j]*rational_vector[j] for j in range(n))-
                quotient*sum(A[i][j]*rational_vector[j] for j in range(n))
                for i in range(n)]
    with localcontext() as context:
        context.prec = 180
        base_decimal = Decimal(base.numerator)/Decimal(base.denominator)
        ritz_gain_decimal = high["eigenvalue"]-base_decimal
        shortfall_decimal = Decimal(1)-high["eigenvalue"]
    answer = {
        "status": "serialized-MP100-core6-Ritz-discovery",
        "rigorous": False, "theorem_ready": False,
        "exact_only_relative_to_serialized_forms": True,
        "basis_order": ["base"]+[f"d{x}" for x in ORDER],
        "A_exact_fraction": [[str(value) for value in row] for row in A],
        "B48_exact_fraction": [[str(value) for value in row] for row in B],
        "A_exact_LDL_pivots": [str(value) for value in pivots],
        "A_positive_definite_exact": True,
        "decimal_solve": {
            "precision_low": 120, "precision_high": 190,
            "eigenvalue_low": str(low["eigenvalue"]),
            "eigenvalue_high": str(high["eigenvalue"]),
            "relative_residual_low": str(low["relative_residual"]),
            "relative_residual_high": str(high["relative_residual"]),
            "iterations_low": low["jacobi_iterations"],
            "iterations_high": high["jacobi_iterations"],
        },
        "top_ritz_quotient_decimal": str(high["eigenvalue"]),
        "base_quotient_decimal": str(base_decimal),
        "ritz_gain_decimal": str(ritz_gain_decimal),
        "shortfall_to_one_decimal": str(shortfall_decimal),
        "rational_candidate_emitted": quotient > 1,
        "candidate_policy": "emit an exact rational vector only when its quotient is >1",
        "continuation_gate": "1/10000",
        "continuation_gate_pass": continuation,
        "pair_results": pair_results,
        "provenance": {
            "pair_manifest_sha256": PAIR_MANIFEST_SHA,
            "pair_builder_sha256": PAIR_BUILDER_SHA,
            "coordinate_manifest_sha256": COORDINATE_MANIFEST_SHA,
            "preflight_sha256": PREFLIGHT_SHA,
            "core_audit_sha256": CORE_AUDIT_SHA,
            "solver_sha256": sha(Path(__file__).read_bytes()),
        },
    }
    if quotient > 1:
        answer["positive_rational_candidate"] = {
            "vector": [str(value) for value in rational_vector],
            "denominator": str(denominator), "numerator": str(numerator),
            "quotient": str(quotient), "gain_over_base": str(gain),
            "exact_generalized_residual": [str(value) for value in residual],
        }
    rendered = (json.dumps(answer, indent=2)+"\n").encode()
    output = Path(args.output).resolve()
    require(output not in trusted and not output.exists(), "output collision")
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
    try:
        os.write(fd, rendered); os.fsync(fd)
        require(os.fstat(fd).st_size == len(rendered), "short output")
        for path, raw in trusted.items():
            require(path.read_bytes() == raw, f"trusted bytes changed: {path}")
    except Exception as exc:
        rejection = (json.dumps({"status": "REJECTED", "error": str(exc)})+"\n").encode()
        try:
            os.ftruncate(fd, 0); os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, rejection); os.fsync(fd)
        except Exception:
            pass
        raise
    finally:
        os.close(fd)
    print(json.dumps({"status": answer["status"],
                      "output_sha256": sha(rendered),
                      "top_ritz_quotient_decimal": str(high["eigenvalue"]),
                      "ritz_gain_decimal": str(ritz_gain_decimal),
                      "rational_candidate_emitted": quotient > 1,
                      "continuation_gate_pass": continuation}, indent=2))


if __name__ == "__main__":
    main()
