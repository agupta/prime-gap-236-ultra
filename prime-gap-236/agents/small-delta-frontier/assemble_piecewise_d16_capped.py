#!/usr/bin/env python3
"""Assemble count-tagged piecewise capped stages into a finite pencil.

The arithmetic assembly is scalar-generic (Fraction or Decimal).  A stage
producer supplies raw J bilinear integrals; this module applies the factor
``k=48`` exactly once and supplies the factor two only when contracting the
symmetric matrix.  The command-line consumer is discovery-only until every
requested stage exists and is caller-SHA-pinned.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import re


FILE = Path(__file__).resolve()
DRIVER = FILE.with_name("piecewise_d16_capped_target.py")
PIECEWISE_REFERENCE = FILE.parents[2] / (
    "results/wide_c722_D16_piecewise_cinner1_couter_natural_exact.json")
PINNED_DRIVER_SHA256 = \
    "cb84d4eb6d24c7be2315b8195b8e0c1a6a9bc52e68e4e5f6a656ea41252e667c"
PINNED_REFERENCE_SHA256 = \
    "e30a9a5f356b0303559bd1d3c1cb7a48474e973ec97b164c00832c919f761cb7"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
DECIMAL_RE = re.compile(
    r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:E[+-][1-9][0-9]*)?$")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json(data: bytes, name: str):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"{name}: duplicate key {key!r}")
            answer[key] = value
        return answer

    def reject(token):
        raise ValueError(f"{name}: floating/nonfinite JSON token {token!r}")

    return json.loads(data, object_pairs_hook=pairs, parse_float=reject,
                      parse_constant=reject)


def canonical_decimal(text, name):
    if not isinstance(text, str) or DECIMAL_RE.fullmatch(text) is None:
        raise ValueError(f"{name}: noncanonical Decimal string")
    value = Decimal(text)
    if not value.is_finite() or str(value) != text:
        raise ValueError(f"{name}: Decimal spelling changed")
    return value


def canonical_q(text, name):
    if not isinstance(text, str):
        raise ValueError(f"{name}: rational is not a string")
    value = Q(text)
    if str(value) != text:
        raise ValueError(f"{name}: noncanonical rational")
    return value


def add_table(destination, table, factor):
    for key, value in table.items():
        destination[key] = destination.get(key, value * 0) + factor * value


def assemble_pencil(inner_i, inner_b, counts, i_by_count,
                    j_tables_by_common_count, k):
    """Return symmetric I and kJ matrices for inner + selected counts."""
    counts = tuple(counts)
    if (isinstance(k, bool) or not isinstance(k, int) or k < 1 or
            len(counts) != len(set(counts)) or
            any(isinstance(r, bool) or not isinstance(r, int) or r < 0
                for r in counts)):
        raise ValueError("invalid finite-pencil count list")
    if inner_i <= 0:
        raise ArithmeticError("nonpositive inner I")
    zero = inner_i * 0
    dimension = len(counts) + 1
    index = {r: i + 1 for i, r in enumerate(counts)}
    A = [[zero for _ in range(dimension)] for _ in range(dimension)]
    B = [[zero for _ in range(dimension)] for _ in range(dimension)]
    A[0][0], B[0][0] = inner_i, inner_b
    if set(i_by_count) != set(counts):
        raise ValueError("I stages do not exactly match selected counts")
    for r in counts:
        if i_by_count[r] <= 0:
            raise ArithmeticError(f"nonpositive shell I at R={r}")
        A[index[r]][index[r]] = i_by_count[r]

    required_common = set()
    for r in counts:
        if r:
            required_common.add(r - 1)
        if r < k:
            required_common.add(r)
    if set(j_tables_by_common_count) != required_common:
        raise ValueError("J stages do not exactly match required common counts")
    tags = ("fh", "fl", "hh", "hl", "lh", "ll")
    for common_r, tables in j_tables_by_common_count.items():
        if set(tables) != set(tags):
            raise ValueError(f"common R={common_r}: incomplete J tag set")
        # Inner-shell: the left total count belongs to the inner coordinate;
        # only the right shell count is retained.
        for r in counts:
            cross = sum((value for (_, right), value in tables["fh"].items()
                         if right == r), zero)
            cross -= sum((value for (_, right), value in tables["fl"].items()
                          if right == r), zero)
            B[0][index[r]] += k * cross
            B[index[r]][0] += k * cross
        # Shell-shell entries are already ordered bilinear entries.  Do not
        # average the two orientations or add a second matrix factor here.
        for r in counts:
            for s in counts:
                key = (r, s)
                value = (tables["hh"].get(key, zero) -
                         tables["hl"].get(key, zero) -
                         tables["lh"].get(key, zero) +
                         tables["ll"].get(key, zero))
                B[index[r]][index[s]] += k * value
    for i in range(dimension):
        for j in range(i):
            if B[i][j] != B[j][i]:
                raise ArithmeticError(
                    f"assembled kJ is not symmetric at ({i},{j})")
    return A, B


def contract(A, B, vector):
    n = len(A)
    if len(B) != n or len(vector) != n:
        raise ValueError("contraction shape mismatch")
    denominator = sum(vector[i] * A[i][j] * vector[j]
                      for i in range(n) for j in range(n))
    numerator = sum(vector[i] * B[i][j] * vector[j]
                    for i in range(n) for j in range(n))
    if denominator <= 0:
        raise ArithmeticError("nonpositive particular denominator")
    return denominator, numerator, numerator / denominator


def stable_float_eigenvector(A, B):
    """Float64 discovery only; exact/Decimal contraction remains authoritative."""
    import numpy as np

    diagonal = np.array([float(A[i][i]) for i in range(len(A))])
    if np.any(~np.isfinite(diagonal)) or np.any(diagonal <= 0):
        raise ArithmeticError("invalid I diagonal for whitening")
    scale = np.sqrt(diagonal)
    whitened = np.array([[float(B[i][j]) / (scale[i] * scale[j])
                          for j in range(len(A))]
                         for i in range(len(A))])
    if not np.allclose(whitened, whitened.T, rtol=0, atol=1e-12):
        raise ArithmeticError("float-whitened pencil is not symmetric")
    values, vectors = np.linalg.eigh(whitened)
    order = np.argsort(values)
    top = int(order[-1])
    coefficients = vectors[:, top] / scale
    coefficients /= max(abs(coefficients))
    return float(values[top]), tuple(float(x) for x in coefficients)


def parse_stage(path, expected_sha, expected_driver_sha):
    if not isinstance(expected_sha, str) or SHA_RE.fullmatch(expected_sha) is None:
        raise ValueError("stage expected SHA is invalid")
    data = Path(path).read_bytes()
    if sha256(data) != expected_sha:
        raise ValueError(f"stage SHA mismatch: {path}")
    # The current discovery producer serializes timing fields as JSON floats.
    # Parse those tokens as strings so no arithmetic field is silently rounded.
    raw = json.loads(data, parse_float=str,
                     object_pairs_hook=lambda pairs: _unique(pairs, str(path)),
                     parse_constant=lambda token: (_ for _ in ()).throw(
                         ValueError(f"nonfinite stage token: {token}")))
    if (raw.get("status") !=
            "piecewise-capped-volume-ramp-D16-Decimal-stage" or
            raw.get("rigorous") is not False or
            raw.get("theorem_ready") is not False or
            raw.get("script_sha256") != expected_driver_sha or
            raw.get("complete_stage") is not True or
            raw.get("cost_probe_h") is not None or
            raw.get("parameters", {}).get("inner_c") != "1" or
            raw.get("parameters", {}).get("outer_c") != "3090/3211" or
            raw.get("basis_dimension") != 307):
        raise ValueError(f"stage status/parameters incomplete: {path}")
    return raw


def _unique(pairs, name):
    answer = {}
    for key, value in pairs:
        if key in answer:
            raise ValueError(f"{name}: duplicate key {key!r}")
        answer[key] = value
    return answer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sha256(DRIVER.read_bytes()) != PINNED_DRIVER_SHA256:
        raise RuntimeError("frozen stage driver changed")
    if sha256(PIECEWISE_REFERENCE.read_bytes()) != PINNED_REFERENCE_SHA256:
        raise RuntimeError("piecewise reference changed")
    manifest_data = args.manifest.read_bytes()
    manifest = strict_json(manifest_data, "stage manifest")
    required = {"format", "driver_sha256", "decimal_dps", "counts",
                "stages"}
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise ValueError("stage manifest schema mismatch")
    if (manifest["format"] != "piecewise-D16-capped-stage-manifest-v1" or
            manifest["driver_sha256"] != PINNED_DRIVER_SHA256 or
            manifest["decimal_dps"] not in (80, 100)):
        raise ValueError("stage manifest identity mismatch")
    counts = tuple(manifest["counts"])
    stage_specs = manifest["stages"]
    if not isinstance(stage_specs, list):
        raise ValueError("stage manifest list missing")
    stages = [parse_stage(item["path"], item["sha256"],
                          PINNED_DRIVER_SHA256) for item in stage_specs]
    dps = manifest["decimal_dps"]
    if any(stage.get("decimal_dps") != dps for stage in stages):
        raise ValueError("mixed stage precision")
    i_by_count = {}
    j_by_common = {}
    for stage in stages:
        if stage.get("i_stage") is not None:
            row = stage["i_stage"]
            r = row["total_count"]
            if r in i_by_count:
                raise ValueError("duplicate I count stage")
            i_by_count[r] = canonical_decimal(
                row["shell_difference"], f"I R={r}")
        if stage.get("j_stage") is not None:
            row = stage["j_stage"]
            r = row["common_count"]
            if r in j_by_common:
                raise ValueError("duplicate J common-count stage")
            parsed = {}
            for tag, entries in row["tables"].items():
                table = {}
                for entry in entries:
                    key = (entry["left_total_count"],
                           entry["right_total_count"])
                    if key in table:
                        raise ValueError("duplicate J table key")
                    table[key] = canonical_decimal(
                        entry["value"], f"J R={r} {tag} {key}")
                parsed[tag] = table
            j_by_common[r] = parsed

    reference = strict_json(PIECEWISE_REFERENCE.read_bytes(), "reference")
    inner_i_q = canonical_q(reference["I_matrix"][0][0], "inner I")
    inner_b_q = canonical_q(reference["kJ_matrix"][0][0], "inner kJ")
    with localcontext() as context:
        context.prec = dps
        inner_i = Decimal(inner_i_q.numerator) / Decimal(inner_i_q.denominator)
        inner_b = Decimal(inner_b_q.numerator) / Decimal(inner_b_q.denominator)
        A, B = assemble_pencil(inner_i, inner_b, counts, i_by_count,
                               j_by_common, 48)
        eigenvalue, float_vector = stable_float_eigenvector(A, B)
        # Fixed 10^18 grid is discovery rationalization, not a proof of
        # optimality.  The serialized particular Decimal contraction is the
        # only sign reported by this consumer.
        grid = 10 ** 18
        integer_vector = tuple(int(round(x * grid)) for x in float_vector)
        denominator, numerator, quotient = contract(A, B, integer_vector)
        output = {
            "status": "piecewise-D16-capped-Decimal-discovery",
            "rigorous": False, "theorem_ready": False,
            "never_implies": ["rigorous interval sign", "H1<=236"],
            "manifest_sha256": sha256(manifest_data),
            "driver_sha256": PINNED_DRIVER_SHA256,
            "reference_sha256": PINNED_REFERENCE_SHA256,
            "decimal_dps": dps, "counts": list(counts),
            "I_matrix": [[str(x) for x in row] for row in A],
            "kJ_matrix": [[str(x) for x in row] for row in B],
            "float64_top_eigenvalue": repr(eigenvalue),
            "integer_vector_grid": grid,
            "integer_vector": list(integer_vector),
            "particular_denominator": str(denominator),
            "particular_numerator": str(numerator),
            "particular_quotient": str(quotient),
            "particular_margin": str(numerator - denominator),
            "particular_margin_positive": numerator > denominator,
        }
    payload = (json.dumps(output, sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_bytes(payload)
    print(json.dumps({"output_sha256": sha256(payload),
                      "particular_quotient": output["particular_quotient"],
                      "margin_positive": output["particular_margin_positive"]},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
