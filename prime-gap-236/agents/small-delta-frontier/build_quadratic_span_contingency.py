#!/usr/bin/env python3
"""Build an exact D4 multiplier H=Q+s*1 for the D12 span contingency.

The production CLI always performs both an exact contraction of the frozen
six-channel blocks and a fresh exact geometric ``evaluate_direct`` traversal.
It never copies the source artifact's form values or pass booleans.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EI = ROOT / "agents" / "exact-integrator"
sys.path.insert(0, str(EI))
sys.path.insert(0, str(EI / "src"))

import exact_integrator as exact  # noqa: E402
from stratum_quadratic import StratumQuadraticEvaluator  # noqa: E402


SOURCE_SHA = "fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86"
INPUT_SHA = "2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b"
PARAMETERS = {
    "alpha": "79247/300000",
    "delta": "1/100",
    "eta": "76247/300000",
    "beta1": "3/20",
    "beta2": "3/20",
    "beta3plus": "97/625",
}
CHANNELS = ("1", "L", "Z", "L^2", "LZ", "Z^2")
CHANNEL_POWERS = ((0, 0), (1, 0), (0, 1), (2, 0), (1, 1), (0, 2))
NULL_LABELS = ((0, "L"), (0, "L^2"), (0, "LZ"))
DEPENDENCIES = {
    "quadratic": (EI / "stratum_quadratic.py",
                  "62dad8c96005bdb06945552a36b6dc35cecea6633daa5f3cf06e514a6aa77234"),
    "linear": (EI / "stratum_linear.py",
               "7400369a2e0e321ed032374f1e45f35785b0f0c53a085af18bf5ec2cb3c80162"),
    "grouped": (EI / "grouped_fixed_vector.py",
                "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"),
    "integrator": (EI / "src" / "exact_integrator.py",
                   "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"),
    "robust_solver": (EI / "robust_generalized_solve.py",
                      "2086244acb674e5bd92e4880fb38d32d6dd981cd0272db595de2578554da257e"),
}
FRACTION_RE = re.compile(r"^(?:0|-?[1-9][0-9]*)(?:/[1-9][0-9]*)?$")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha256(Path(path).read_bytes())


def strict_json(data):
    require(isinstance(data, bytes) and len(data) <= 8_000_000,
            "JSON input is not bounded bytes")

    def pairs_hook(pairs):
        answer = {}
        for key, value in pairs:
            require(isinstance(key, str) and key not in answer,
                    "duplicate or non-string JSON key")
            answer[key] = value
        return answer

    def reject_constant(_token):
        raise ValueError("nonfinite JSON token")

    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs_hook,
                      parse_constant=reject_constant)


def canonical_fraction(value, name):
    require(not isinstance(value, bool) and isinstance(value, (int, str)),
            f"{name} is not an exact scalar")
    text = str(value)
    require(FRACTION_RE.fullmatch(text) is not None,
            f"{name} is not a canonical integer/fraction")
    answer = Fraction(text)
    require(str(answer) == text, f"{name} is not reduced/canonical")
    return answer


def read_pinned(path, expected, name):
    data = Path(path).read_bytes()
    require(sha256(data) == expected, f"{name} byte SHA mismatch")
    return data, strict_json(data)


def parse_source(raw):
    require(isinstance(raw, dict), "source top level must be an object")
    require(raw.get("status") == "exact-stratum-quadratic-rational-vector",
            "wrong source status")
    require(raw.get("rigorous_forms") is True and
            raw.get("block_direct_bitwise_equal") is True,
            "source exact gates did not pass")
    require(type(raw.get("k")) is int and raw["k"] == 48,
            "source must have exact k=48")
    require(raw.get("parameters") == PARAMETERS, "source parameters changed")
    require(type(raw.get("quadratic_basis_dimension")) is int and
            raw["quadratic_basis_dimension"] == 96,
            "source quadratic dimension changed")
    require(raw.get("channel_powers") == [list(x) for x in CHANNEL_POWERS],
            "source channel powers/order changed")
    labels = [[r, channel] for r in range(16) for channel in CHANNELS]
    require(raw.get("quadratic_labels") == labels,
            "source channel labels/order changed")
    require(raw.get("discarded_gram_dependent_labels") ==
            [[r, channel] for r, channel in NULL_LABELS],
            "source null-label list changed")
    active = [label for label in labels if tuple(label) not in NULL_LABELS]
    require(raw.get("active_quadratic_labels") == active,
            "source active-label list changed")

    vector_raw = raw.get("rational_vector")
    require(isinstance(vector_raw, list) and len(vector_raw) == 96,
            "source vector must contain 96 coordinates")
    vector = tuple(canonical_fraction(x, f"source vector[{i}]")
                   for i, x in enumerate(vector_raw))
    for r, channel in NULL_LABELS:
        require(vector[6 * r + CHANNELS.index(channel)] == 0,
                "source null label has a nonzero coordinate")
    require(max(abs(x) for x in vector) == 1,
            "source multiplier maximum absolute coefficient changed")

    blocks_raw = raw.get("i_blocks")
    require(isinstance(blocks_raw, dict) and
            list(blocks_raw) == [str(r) for r in range(16)],
            "source I block strata/order changed")
    blocks = []
    for r in range(16):
        block_raw = blocks_raw[str(r)]
        require(isinstance(block_raw, list) and len(block_raw) == 6 and
                all(isinstance(row, list) and len(row) == 6
                    for row in block_raw),
                f"source I block {r} is not 6 by 6")
        block = tuple(tuple(canonical_fraction(
            value, f"I[{r},{p},{q}]") for q, value in enumerate(row))
                      for p, row in enumerate(block_raw))
        require(all(block[p][q] == block[q][p]
                    for p in range(6) for q in range(6)),
                f"source I block {r} is not symmetric")
        blocks.append(block)

    entries_raw = raw.get("j_entries")
    require(isinstance(entries_raw, dict) and len(entries_raw) == 876,
            "source J entry count changed")
    entries = {}
    for text, raw_value in entries_raw.items():
        try:
            key = ast.literal_eval(text)
        except (SyntaxError, ValueError) as error:
            raise ValueError("malformed J label key") from error
        require(str(key) == text and isinstance(key, tuple) and len(key) == 2,
                "J label key is not canonical")
        left, right = key
        require(all(isinstance(label, tuple) and len(label) == 2 and
                    type(label[0]) is int and type(label[1]) is int and
                    0 <= label[0] < 16 and 0 <= label[1] < 6
                    for label in (left, right)),
                "J label lies outside the 96-channel basis")
        require(left <= right, "J key is not in upper-triangle order")
        entries[(left, right)] = canonical_fraction(raw_value, f"J[{text}]")
    require(len(entries) == 876, "duplicate parsed J entry")

    source_denominator = canonical_fraction(raw.get("denominator"),
                                            "source denominator")
    source_numerator = canonical_fraction(raw.get("numerator"),
                                          "source numerator")
    return {
        "vector": vector,
        "i_blocks": tuple(blocks),
        "j_entries": entries,
        "source_denominator": source_denominator,
        "source_numerator": source_numerator,
    }


def dense_matrices(parsed):
    size = 96
    a = [[Fraction(0) for _ in range(size)] for _ in range(size)]
    b = [[Fraction(0) for _ in range(size)] for _ in range(size)]
    for r, block in enumerate(parsed["i_blocks"]):
        for p in range(6):
            for q in range(6):
                a[6 * r + p][6 * r + q] = block[p][q]
    for (left, right), value in parsed["j_entries"].items():
        i, j = 6 * left[0] + left[1], 6 * right[0] + right[1]
        b[i][j] += 48 * value
        if i != j:
            b[j][i] += 48 * value
    return a, b


def dense_bilinear(matrix, left, right):
    require(len(matrix) == len(left) == len(right),
            "dense contraction dimension mismatch")
    return sum(left[i] * matrix[i][j] * right[j]
               for i in range(len(left)) for j in range(len(right)))


def sparse_forms(parsed, vector):
    denominator = Fraction(0)
    for r, block in enumerate(parsed["i_blocks"]):
        local = vector[6 * r:6 * r + 6]
        denominator += sum(local[p] * block[p][q] * local[q]
                           for p in range(6) for q in range(6))
    numerator = Fraction(0)
    for (left, right), value in parsed["j_entries"].items():
        i, j = 6 * left[0] + left[1], 6 * right[0] + right[1]
        numerator += 48 * value * vector[i] * vector[j] * (
            1 if i == j else 2)
    return denominator, numerator


def construct_h(parsed, constant_scale):
    require(constant_scale != 0 and
            constant_scale.numerator.bit_length() <= 128 and
            constant_scale.denominator.bit_length() <= 128,
            "s must be a nonzero bounded exact rational")
    q = parsed["vector"]
    constant = tuple(Fraction(1) if i % 6 == 0 else Fraction(0)
                     for i in range(96))
    h = tuple(q[i] + constant_scale * constant[i] for i in range(96))
    require(all(h[6 * r] == q[6 * r] + constant_scale for r in range(16)),
            "constant-channel addition failed")
    require(all(h[i] == q[i] for i in range(96) if i % 6),
            "nonconstant channel changed")
    return constant, h


def d4_span_stationary(result):
    """Rank both finite stationary roots and infinity at Decimal 160."""
    d0, n0 = result["base_forms"]
    d1, n1 = result["q_forms"]
    dc, nc = result["cross_forms"]
    coefficients = (
        nc * d0 - n0 * dc,
        n1 * d0 - n0 * d1,
        n1 * dc - nc * d1,
    )
    discriminant = coefficients[1] ** 2 - 4 * coefficients[0] * coefficients[2]
    require(coefficients[2] != 0 and discriminant > 0,
            "frozen D4 span does not have two distinct finite roots")
    with localcontext() as context:
        context.prec = 160

        def decimal_fraction(value):
            return Decimal(value.numerator) / Decimal(value.denominator)

        a, b, c = (decimal_fraction(x) for x in coefficients)
        square_root = decimal_fraction(discriminant).sqrt()
        roots = ((-b + square_root) / (2 * c),
                 (-b - square_root) / (2 * c))
        ranked = []
        for root in roots:
            denominator = (decimal_fraction(d0) + 2 * root *
                           decimal_fraction(dc) + root * root *
                           decimal_fraction(d1))
            numerator = (decimal_fraction(n0) + 2 * root *
                         decimal_fraction(nc) + root * root *
                         decimal_fraction(n1))
            require(denominator > 0, "D4 stationary denominator is not positive")
            ranked.append({
                "point": "finite",
                "t": str(root),
                "denominator": str(denominator),
                "quotient": str(numerator / denominator),
            })
        require(d1 > 0, "D4 infinity denominator is not positive")
        ranked.append({
            "point": "infinity",
            "denominator": str(decimal_fraction(d1)),
            "quotient": str(decimal_fraction(n1) / decimal_fraction(d1)),
        })
        ranked.sort(key=lambda item: Decimal(item["quotient"]), reverse=True)
    return {
        "stationary_polynomial_coefficients_ascending":
            [str(x) for x in coefficients],
        "discriminant": str(discriminant),
        "decimal_precision": 160,
        "ranked_projective_points": ranked,
        "maximum_point": ranked[0],
    }


def reconstruct(parsed, constant_scale=Fraction(1)):
    constant, h = construct_h(parsed, constant_scale)
    q = parsed["vector"]
    a, b = dense_matrices(parsed)
    q_dense = (dense_bilinear(a, q, q), dense_bilinear(b, q, q))
    q_sparse = sparse_forms(parsed, q)
    require(q_dense == q_sparse == (
        parsed["source_denominator"], parsed["source_numerator"]),
        "source Q forms do not reconstruct exactly (including factor 48)")

    base = (dense_bilinear(a, constant, constant),
            dense_bilinear(b, constant, constant))
    cross = (dense_bilinear(a, constant, q),
             dense_bilinear(b, constant, q))
    h_dense = (dense_bilinear(a, h, h), dense_bilinear(b, h, h))
    h_sparse = sparse_forms(parsed, h)
    identity = tuple(q_dense[i] + 2 * constant_scale * cross[i] +
                     constant_scale * constant_scale * base[i]
                     for i in range(2))
    require(h_dense == h_sparse == identity,
            "H block/sparse/polarization forms disagree")
    require(h_dense[0] > 0, "H exact D4 denominator is not positive")
    return {
        "constant": constant,
        "h": h,
        "base_forms": base,
        "q_forms": q_dense,
        "cross_forms": cross,
        "h_forms": h_dense,
        "block_sparse_bitwise_equal": True,
        "polarization_identity_exact": True,
    }


def fresh_direct(input_path, vector):
    data, raw = read_pinned(input_path, INPUT_SHA, "fixed D4 polynomial")
    require(type(raw.get("k")) is int and raw["k"] == 48,
            "fixed D4 input is not k=48")
    basis = raw.get("basis")
    coefficients_raw = raw.get("rational_vector")
    require(isinstance(basis, list) and isinstance(coefficients_raw, list) and
            len(basis) == len(coefficients_raw) == 12,
            "fixed D4 basis/vector mismatch")
    labels = []
    for i, label in enumerate(basis):
        require(isinstance(label, list) and len(label) == 2 and
                type(label[0]) is int and isinstance(label[1], list),
                f"malformed D4 basis label {i}")
        labels.append((label[0], tuple(label[1])))
    coefficients = [canonical_fraction(x, f"D4 coefficient[{i}]")
                    for i, x in enumerate(coefficients_raw)]
    support = exact.OneStratumSupport(
        48, *[Fraction(PARAMETERS[key]) for key in
              ("alpha", "delta", "eta", "beta1", "beta2", "beta3plus")])
    evaluator = StratumQuadraticEvaluator(
        support, labels, coefficients, Fraction)
    start = time.perf_counter()
    direct = evaluator.evaluate_direct(vector, progress=False)
    return direct, time.perf_counter() - start, sha256(data)


def dependency_snapshot():
    answer = {}
    for name, (path, expected) in DEPENDENCIES.items():
        actual = file_sha(path)
        require(actual == expected, f"{name} dependency SHA changed")
        answer[name] = actual
    return answer


def canonical_bytes(payload):
    return (json.dumps(payload, indent=2, sort_keys=True,
                       allow_nan=False) + "\n").encode("utf-8")


def reserve_output(path):
    output = Path(path)
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
    stat = os.fstat(fd)
    return fd, (stat.st_dev, stat.st_ino)


def owned_path(path, identity):
    try:
        stat = os.stat(path, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return (stat.st_dev, stat.st_ino) == identity


def publish_reserved(fd, path, identity, data):
    require(owned_path(path, identity), "reserved output inode was replaced")
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, data)
    os.ftruncate(fd, len(data))
    os.fsync(fd)
    require(owned_path(path, identity), "output inode changed during publish")
    os.lseek(fd, 0, os.SEEK_SET)
    require(os.read(fd, len(data) + 1) == data,
            "published output bytes did not round trip")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--expect-source-sha256", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--expect-input-sha256", required=True)
    parser.add_argument("--constant-scale-s", dest="constant_scale_text",
                        required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    require(args.expect_source_sha256 == SOURCE_SHA,
            "caller did not request the frozen source SHA")
    require(args.expect_input_sha256 == INPUT_SHA,
            "caller did not request the frozen D4 input SHA")
    constant_scale = canonical_fraction(args.constant_scale_text, "s")
    require(constant_scale != 0 and
            constant_scale.numerator.bit_length() <= 128 and
            constant_scale.denominator.bit_length() <= 128,
            "s must be a nonzero bounded exact rational")
    resolved = [Path(x).resolve() for x in
                (args.source, args.input, args.output, __file__)]
    require(len(set(resolved)) == len(resolved),
            "source/input/output/driver paths must be pairwise distinct")

    fd, identity = reserve_output(args.output)
    published = False
    source_bytes = input_bytes = b""
    try:
        source_bytes, raw = read_pinned(
            args.source, SOURCE_SHA, "quadratic multiplier source")
        input_bytes, _ = read_pinned(args.input, INPUT_SHA, "fixed D4 input")
        dependencies = dependency_snapshot()
        driver_start = file_sha(__file__)
        parsed = parse_source(raw)
        result = reconstruct(parsed, constant_scale)
        span_stationary = d4_span_stationary(result)
        direct, direct_seconds, _ = fresh_direct(args.input, result["h"])
        require(direct[2:] == (312, 1200),
                "fresh direct D4 traversal counts changed")
        require(direct[:2] == result["h_forms"],
                "fresh direct D4 forms disagree with block reconstruction")

        gates = {
            "source_q_forms_reconstructed": True,
            "block_sparse_bitwise_equal":
                result["block_sparse_bitwise_equal"],
            "polarization_identity_exact":
                result["polarization_identity_exact"],
            "fresh_direct_bitwise_equal": direct[:2] == result["h_forms"],
            "direct_counts_complete": direct[2:] == (312, 1200),
            "denominator_positive": result["h_forms"][0] > 0,
        }
        require(all(gates.values()), "not every exact D4 gate passed")
        output = {
            "status": "exact-stratum-quadratic-rational-vector",
            "construction": "H=Q+s*1 exact D4 span contingency",
            "rigorous_forms": all(gates.values()),
            "eigenvector_discovery_rigorous": False,
            "theorem_ready": False,
            "k": 48,
            "parameters": PARAMETERS,
            "fixed_basis_dimension": 12,
            "quadratic_basis_dimension": 96,
            "discovery_basis_dimension": 93,
            "channel_powers": [list(x) for x in CHANNEL_POWERS],
            "quadratic_labels": [[r, channel] for r in range(16)
                                 for channel in CHANNELS],
            "active_quadratic_labels": [
                [r, channel] for r in range(16) for channel in CHANNELS
                if (r, channel) not in NULL_LABELS],
            "discarded_gram_dependent_labels": [list(x) for x in NULL_LABELS],
            "constant_scale_s": str(constant_scale),
            "source_multiplier_json": str(Path(args.source)),
            "source_multiplier_sha256": SOURCE_SHA,
            "input_json": str(Path(args.input)),
            "input_sha256": INPUT_SHA,
            "script_sha256": driver_start,
            "dependency_hashes": dependencies,
            "rational_vector": [str(x) for x in result["h"]],
            "base_denominator": str(result["base_forms"][0]),
            "base_numerator": str(result["base_forms"][1]),
            "q_denominator": str(result["q_forms"][0]),
            "q_numerator": str(result["q_forms"][1]),
            "base_q_i_cross": str(result["cross_forms"][0]),
            "base_q_n_cross": str(result["cross_forms"][1]),
            "denominator": str(result["h_forms"][0]),
            "numerator": str(result["h_forms"][1]),
            "quotient": str(result["h_forms"][1] / result["h_forms"][0]),
            "margin": str(result["h_forms"][1] - result["h_forms"][0]),
            "denominator_positive": result["h_forms"][0] > 0,
            "margin_positive": result["h_forms"][1] > result["h_forms"][0],
            "block_direct_bitwise_equal": all(gates.values()),
            "i_orbit_groups": 20,
            "i_faces": 312,
            "marginal_components": 19,
            "j_branch_domains": 1200,
            "direct_i_faces": direct[2],
            "direct_j_branch_domains": direct[3],
            "direct_seconds": direct_seconds,
            "exact_gates": gates,
            "d4_span_stationary": span_stationary,
            "note": ("fresh exact D4 multiplier calibration only; a future "
                     "D12 Decimal transfer remains discovery output"),
        }
        # Fail closed on every read dependency immediately before publishing.
        require(sha256(Path(args.source).read_bytes()) == SOURCE_SHA,
                "source mutated during construction")
        require(sha256(Path(args.input).read_bytes()) == INPUT_SHA,
                "fixed input mutated during construction")
        require(dependency_snapshot() == dependencies,
                "arithmetic dependency mutated during construction")
        require(file_sha(__file__) == driver_start,
                "builder mutated during construction")
        data = canonical_bytes(output)
        publish_reserved(fd, args.output, identity, data)
        published = True
        print(json.dumps({
            "status": output["status"],
            "output": args.output,
            "output_sha256": sha256(data),
            "quotient": output["quotient"],
            "margin": output["margin"],
            "direct_seconds": direct_seconds,
            "exact_gates": gates,
        }, indent=2))
    finally:
        os.close(fd)
        if not published and owned_path(args.output, identity):
            os.unlink(args.output)


if __name__ == "__main__":
    main()
