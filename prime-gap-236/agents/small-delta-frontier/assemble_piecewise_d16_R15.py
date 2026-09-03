#!/usr/bin/env python3
"""Fail-closed Decimal discovery assembly for inner plus outer R=15."""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import re


FILE = Path(__file__).resolve()
HERE = FILE.parent
REPO = FILE.parents[2]
I_DRIVER = HERE / "piecewise_d16_capped_target.py"
J_DRIVER = HERE / "piecewise_d16_R15_specialized.py"
REFERENCE = REPO / (
    "results/wide_c722_D16_piecewise_cinner1_couter_natural_exact.json")
PINNED_I_DRIVER_SHA256 = \
    "cb84d4eb6d24c7be2315b8195b8e0c1a6a9bc52e68e4e5f6a656ea41252e667c"
PINNED_J_DRIVER_SHA256 = \
    "5086a4a381d301ae3a5b321f5e5afba685b677d6851694ef555f6ec76d7fdc58"
PINNED_REFERENCE_SHA256 = \
    "e30a9a5f356b0303559bd1d3c1cb7a48474e973ec97b164c00832c919f761cb7"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def unique(pairs, name):
    answer = {}
    for key, value in pairs:
        if key in answer:
            raise ValueError(f"{name}: duplicate key {key!r}")
        answer[key] = value
    return answer


def load_json_bytes(data, name, *, float_as_string=False):
    return json.loads(
        data, object_pairs_hook=lambda pairs: unique(pairs, name),
        parse_float=(str if float_as_string else
                     lambda token: (_ for _ in ()).throw(
                         ValueError(f"{name}: JSON float {token}"))),
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"{name}: nonfinite {token}")))


def exact_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name}: not an exact integer")
    return value


def decimal_text(value, name):
    if not isinstance(value, str):
        raise ValueError(f"{name}: not Decimal text")
    answer = Decimal(value)
    if not answer.is_finite() or str(answer) != value:
        raise ValueError(f"{name}: noncanonical/nonfinite Decimal")
    return answer


def read_pinned(path, expected_sha, name, *, float_as_string=False):
    if not isinstance(expected_sha, str) or SHA_RE.fullmatch(expected_sha) is None:
        raise ValueError(f"{name}: invalid caller SHA")
    data = Path(path).read_bytes()
    if sha256(data) != expected_sha:
        raise ValueError(f"{name}: byte SHA mismatch")
    return data, load_json_bytes(data, name, float_as_string=float_as_string)


def stationary_candidates(a00, a11, b00, b01, b11):
    if a00 <= 0 or a11 <= 0:
        raise ArithmeticError("I diagonal is not positive")
    aa = a11 * b01
    bb = a11 * b00 - b11 * a00
    cc = -b01 * a00
    candidates = [("inner", Decimal(0), b00 / a00),
                  ("outer_infinity", None, b11 / a11)]
    if aa:
        discriminant = bb * bb - Decimal(4) * aa * cc
        if discriminant < 0:
            raise ArithmeticError("negative stationary discriminant")
        root = discriminant.sqrt()
        for sign, name in ((1, "stationary_plus"), (-1, "stationary_minus")):
            amplitude = (-bb + sign * root) / (Decimal(2) * aa)
            denominator = a00 + amplitude * amplitude * a11
            numerator = b00 + Decimal(2) * amplitude * b01 + \
                amplitude * amplitude * b11
            candidates.append((name, amplitude, numerator / denominator))
    elif bb:
        amplitude = -cc / bb
        denominator = a00 + amplitude * amplitude * a11
        numerator = b00 + Decimal(2) * amplitude * b01 + \
            amplitude * amplitude * b11
        candidates.append(("stationary_linear", amplitude,
                           numerator / denominator))
    return candidates


def assemble(inner_i, inner_b, shell_i, rows):
    zero = inner_i * 0
    cross = sum((row["fh"] - row["fl"] for row in rows), zero) * 48
    shell_b = sum((row["hh"] + row["ll"] - 2 * row["hl"]
                   for row in rows), zero) * 48
    if shell_i <= 0 or shell_b < 0:
        raise ArithmeticError("invalid R15 shell diagonal")
    return [[inner_i, zero], [zero, shell_i]], \
        [[inner_b, cross], [cross, shell_b]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sha256(I_DRIVER) != PINNED_I_DRIVER_SHA256:
        raise RuntimeError("I driver changed")
    if sha256(J_DRIVER) != PINNED_J_DRIVER_SHA256:
        raise RuntimeError("J driver changed")
    if sha256(REFERENCE) != PINNED_REFERENCE_SHA256:
        raise RuntimeError("exact reference changed")
    manifest_data = args.manifest.read_bytes()
    manifest = load_json_bytes(manifest_data, "manifest")
    if (not isinstance(manifest, dict) or set(manifest) !=
            {"format", "decimal_dps", "i_stage", "j_stages"} or
            manifest["format"] != "piecewise-D16-R15-stage-manifest-v1" or
            manifest["decimal_dps"] not in (80, 100)):
        raise ValueError("manifest schema/identity mismatch")
    dps = manifest["decimal_dps"]
    i_spec = manifest["i_stage"]
    if not isinstance(i_spec, dict) or set(i_spec) != {"path", "sha256"}:
        raise ValueError("I stage specification malformed")
    _, i_stage = read_pinned(i_spec["path"], i_spec["sha256"], "I stage",
                             float_as_string=True)
    if (i_stage.get("status") !=
            "piecewise-capped-volume-ramp-D16-Decimal-stage" or
            i_stage.get("script_sha256") != PINNED_I_DRIVER_SHA256 or
            i_stage.get("rigorous") is not False or
            i_stage.get("theorem_ready") is not False or
            i_stage.get("decimal_dps") != dps or
            i_stage.get("complete_stage") is not True or
            i_stage.get("cost_probe_h") is not None or
            i_stage.get("i_stage", {}).get("total_count") != 15 or
            i_stage.get("j_stage") is not None):
        raise ValueError("I stage is not complete R15 data")
    shell_i = decimal_text(
        i_stage["i_stage"]["shell_difference"], "R15 shell I")

    j_specs = manifest["j_stages"]
    if not isinstance(j_specs, list) or len(j_specs) != 2:
        raise ValueError("exactly two J stages are required")
    rows = {}
    for spec in j_specs:
        if not isinstance(spec, dict) or set(spec) != {"path", "sha256"}:
            raise ValueError("J stage specification malformed")
        _, stage = read_pinned(spec["path"], spec["sha256"], "J stage",
                               float_as_string=True)
        parameters = stage.get("parameters", {})
        common = parameters.get("common_count")
        if (stage.get("status") !=
                "piecewise-D16-R15-specialized-Decimal-J-stage" or
                stage.get("script_sha256") != PINNED_J_DRIVER_SHA256 or
                stage.get("target_driver_sha256") != PINNED_I_DRIVER_SHA256 or
                stage.get("rigorous") is not False or
                stage.get("theorem_ready") is not False or
                stage.get("decimal_dps") != dps or
                stage.get("selected_h") is not None or
                stage.get("complete_common_count") is not True or
                parameters.get("target_total_count") != 15 or
                common not in (14, 15) or common in rows):
            raise ValueError("J stage is not complete canonical R15 data")
        raw = stage.get("raw_J_bilinear")
        if (not isinstance(raw, dict) or set(raw) !=
                {"fh", "fl", "hh", "hl", "ll"}):
            raise ValueError("J stage tag inventory mismatch")
        rows[common] = {tag: decimal_text(value, f"J{common}:{tag}")
                        for tag, value in raw.items()}
    if set(rows) != {14, 15}:
        raise ValueError("J common-count inventory mismatch")

    reference = load_json_bytes(REFERENCE.read_bytes(), "reference")
    inner_i_q = Q(reference["I_matrix"][0][0])
    inner_b_q = Q(reference["kJ_matrix"][0][0])
    with localcontext() as context:
        context.prec = dps
        inner_i = Decimal(inner_i_q.numerator) / Decimal(inner_i_q.denominator)
        inner_b = Decimal(inner_b_q.numerator) / Decimal(inner_b_q.denominator)
        A, B = assemble(inner_i, inner_b, shell_i,
                        [rows[14], rows[15]])
        candidates = stationary_candidates(
            A[0][0], A[1][1], B[0][0], B[0][1], B[1][1])
        best = max(candidates, key=lambda item: item[2])
        output = {
            "status": "piecewise-D16-inner-plus-R15-Decimal-discovery",
            "rigorous": False, "theorem_ready": False,
            "never_implies": ["rigorous interval sign", "H1<=236"],
            "manifest_sha256": sha256(manifest_data),
            "I_driver_sha256": PINNED_I_DRIVER_SHA256,
            "J_driver_sha256": PINNED_J_DRIVER_SHA256,
            "reference_sha256": PINNED_REFERENCE_SHA256,
            "decimal_dps": dps,
            "I_matrix": [[str(x) for x in row] for row in A],
            "kJ_matrix": [[str(x) for x in row] for row in B],
            "candidates": [
                {"name": name,
                 "outer_R15_amplitude": (None if amplitude is None else
                                         str(amplitude)),
                 "quotient": str(quotient)}
                for name, amplitude, quotient in candidates],
            "best": {"name": best[0],
                     "outer_R15_amplitude": (None if best[1] is None else
                                             str(best[1])),
                     "quotient": str(best[2]),
                     "above_one": best[2] > 1},
        }
    payload = (json.dumps(output, sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_bytes(payload)
    print(json.dumps({"output_sha256": sha256(payload),
                      "best": output["best"]}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
