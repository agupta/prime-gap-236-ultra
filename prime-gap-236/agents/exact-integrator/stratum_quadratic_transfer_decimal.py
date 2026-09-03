#!/usr/bin/env python3
"""Direct Decimal transfer of one exact D4 degree-two multiplier to D12.

The rational multiplier is inserted before both I integration and marginal
branch squaring.  This evaluates one candidate only; it does not construct or
optimize the D12 multiplier matrix.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import time
from collections import defaultdict
from decimal import getcontext
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import (  # noqa: E402
    add_poly,
    install_decimal,
    precompute_orbits,
)
from stratum_quadratic import StratumQuadraticEvaluator  # noqa: E402


PINNED = {
    "quadratic":
        "62dad8c96005bdb06945552a36b6dc35cecea6633daa5f3cf06e514a6aa77234",
    "stratum_amplitude":
        "d23d42315d7b518ae5d3f200a6192f47f3500d6eebd3a73fb6aa4ce7a23c7887",
    "stratum_linear":
        "7400369a2e0e321ed032374f1e45f35785b0f0c53a085af18bf5ec2cb3c80162",
    "grouped":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    "integrator":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "robust_solver":
        "2086244acb674e5bd92e4880fb38d32d6dd981cd0272db595de2578554da257e",
    "scheduled_basis":
        "06f79a13dbf172f40716d603ae8d824b5f65d2d69ed08dee59bd5c091821c4d0",
    "scheduled_verifier":
        "97f36696712f9cbe0cc0fff1fab6c4dc5ec4850220c12ebcc63f9c794aff1a1a",
}
PARAMETERS = {
    "alpha": "79247/300000",
    "delta": "1/100",
    "eta": "76247/300000",
    "beta1": "3/20",
    "beta2": "3/20",
    "beta3plus": "97/625",
}


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_pinned_bytes(path, expected_sha256, description):
    raw = Path(path).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        raise SystemExit(
            f"{description} SHA-256 mismatch: expected {expected_sha256}, "
            f"got {actual}")
    return raw, actual


def require_pinned_dependencies(hashes):
    for key, expected in PINNED.items():
        if hashes.get(key) != expected:
            raise SystemExit(
                f"pinned dependency mismatch for {key}: expected "
                f"{expected}, got {hashes.get(key)}")


class DirectQuadraticTransfer(StratumQuadraticEvaluator):
    def evaluate_i_r_transfer(self, grouped, amplitudes, r, progress=False):
        dimension = self.support.k
        max_h = int(self.support.alpha // self.support.delta) - r
        answer, faces = self.zero, 0
        constraints = ()
        if r:
            cap = self.support.beta(r) - r * self.support.delta
            if cap <= 0:
                return answer, faces
            constraints = ((self.one, self.zero, cap),)
        for h in range(max_h + 1):
            outer = self.support.alpha - (r + h) * self.support.delta
            if outer <= 0:
                continue
            base = self._i_face_polynomial(
                grouped, dimension, r, h, max_h, outer)
            amplitude = defaultdict(self.scalar)
            for p, phi in enumerate(self._phi_polynomials(r, h)):
                add_poly(amplitude, phi, amplitudes[r][p])
            integrand = ei._poly_mul(
                base, ei._poly_mul(dict(amplitude), dict(amplitude)))
            answer += self.integrate_domain(
                integrand, dimension, r, outer, constraints)
            faces += 1
            if progress:
                print(f"quadratic transfer I r={r} h={h} faces={faces}",
                      flush=True)
            self.clear_face_caches()
        self.clear_radial_caches()
        return answer, faces

    def evaluate_j_r_transfer(self, lrs, by_lr, amplitudes, r,
                              progress=False):
        branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
        dimension = self.support.k - 1
        max_h = int(self.support.eta // self.support.delta) - r
        answer, domains = self.zero, 0
        for h in range(max_h + 1):
            outer = self.support.eta - (r + h) * self.support.delta
            if outer <= 0:
                continue
            channels = self._channel_branch_blocks(
                lrs, by_lr, r, h, dimension, outer)
            combined = {}
            for branch in branches:
                total_r = r if branch in self.SMALL_BRANCHES else r + 1
                vector = amplitudes.get(total_r, (self.zero,) * 6)
                combined[branch] = self._combine_channel_blocks(
                    channels[branch], vector)
            for i, left in enumerate(branches):
                for right in branches[:i + 1]:
                    value = self._integrate_branch_pair(
                        combined, left, right, dimension, r, h,
                        outer, max_h)
                    if value is not None:
                        answer += value
                        domains += 1
            if progress:
                print(f"quadratic transfer J r={r} h={h} domains={domains}",
                      flush=True)
            self.clear_face_caches(clear_marginals=True)
        self.clear_radial_caches()
        return answer, domains


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("multiplier_json")
    parser.add_argument("--expect-input-sha256", required=True)
    parser.add_argument("--expect-multiplier-sha256", required=True)
    parser.add_argument("--decimal-dps", type=int, default=100)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.decimal_dps < 90:
        parser.error("require decimal-dps>=90")

    paths = {
        "driver": Path(__file__),
        "quadratic": HERE / "stratum_quadratic.py",
        "stratum_amplitude": HERE / "stratum_amplitude.py",
        "stratum_linear": HERE / "stratum_linear.py",
        "grouped": HERE / "grouped_fixed_vector.py",
        "integrator": HERE / "src/exact_integrator.py",
        "robust_solver": HERE / "robust_generalized_solve.py",
        "scheduled_basis": HERE / "run_scheduled_basis.py",
        "scheduled_verifier": HERE / "verify_scheduled_fixed_vector.py",
    }
    hashes_start = {key: file_sha(path) for key, path in paths.items()}
    require_pinned_dependencies(hashes_start)
    input_bytes, input_sha = read_pinned_bytes(
        args.input_json, args.expect_input_sha256, "fixed-polynomial input")
    multiplier_bytes, multiplier_sha = read_pinned_bytes(
        args.multiplier_json, args.expect_multiplier_sha256,
        "transferred multiplier")
    raw = json.loads(input_bytes)
    multiplier = json.loads(multiplier_bytes)
    if int(raw.get("k", -1)) != 48 or int(multiplier.get("k", -1)) != 48:
        raise SystemExit("this transfer probe is pinned to k=48")
    if multiplier.get("status") != \
            "exact-stratum-quadratic-rational-vector" or \
            not multiplier.get("rigorous_forms") or \
            not multiplier.get("block_direct_bitwise_equal"):
        raise SystemExit("multiplier source did not pass exact gates")
    channels = StratumQuadraticEvaluator.CHANNELS
    source_labels = [(int(r), channels.index(channel))
                     for r, channel in multiplier["quadratic_labels"]]
    if source_labels != [(r, p) for r in range(16) for p in range(6)]:
        raise SystemExit("quadratic multiplier labels are malformed")
    source_vector = [Fraction(x) for x in multiplier["rational_vector"]]
    if len(source_vector) != 96:
        raise SystemExit("quadratic multiplier vector dimension mismatch")

    getcontext().prec = args.decimal_dps
    labels = [(int(a), tuple(int(x) for x in lam)) for a, lam in raw["basis"]]
    rational_base = [Fraction(x) for x in raw["rational_vector"]]
    if len(labels) != len(rational_base) or len(labels) not in (12, 272):
        raise SystemExit("fixed polynomial basis/vector mismatch")
    orbit_table = precompute_orbits(labels, 48)
    scalar = install_decimal(orbit_table, args.decimal_dps)
    support = ei.OneStratumSupport(
        48, *[scalar(Fraction(PARAMETERS[key]).numerator,
                     Fraction(PARAMETERS[key]).denominator)
              for key in ("alpha", "delta", "eta", "beta1", "beta2",
                          "beta3plus")])
    base = [scalar(x.numerator, x.denominator) for x in rational_base]
    evaluator = DirectQuadraticTransfer(support, labels, base, scalar)
    amplitudes = {
        r: tuple(scalar(source_vector[6 * r + p].numerator,
                        source_vector[6 * r + p].denominator)
                 for p in range(6))
        for r in range(16)
    }

    start = time.perf_counter()
    grouped = evaluator.square_residual_terms()
    i_by_r, i_faces = [], 0
    for r in evaluator._r_values_i():
        value, count = evaluator.evaluate_i_r_transfer(
            grouped, amplitudes, r, args.progress)
        i_by_r.append(value)
        i_faces += count
    i_seconds = time.perf_counter() - start
    denominator = sum(i_by_r, evaluator.zero)
    if denominator <= 0:
        raise ArithmeticError("quadratic transfer denominator is not positive")
    i_stage = {
        "status": "multiprecision-quadratic-transfer-I-stage",
        "rigorous": False,
        "complete": True,
        "decimal_dps": args.decimal_dps,
        "input_sha256": input_sha,
        "multiplier_sha256": multiplier_sha,
        "parameters": PARAMETERS,
        "dependency_hashes": hashes_start,
        "i_orbit_groups": len(grouped),
        "i_faces": i_faces,
        "i_by_r": [str(x) for x in i_by_r],
        "denominator": str(denominator),
        "i_seconds": i_seconds,
    }
    stage_path = args.output + ".I-stage.json"
    Path(stage_path).write_text(json.dumps(i_stage, indent=2) + "\n")
    stage_sha = file_sha(stage_path)
    print("I_STAGE_COMPLETE " + json.dumps({
        "path": stage_path, "i_seconds": i_seconds,
        "i_faces": i_faces, "groups": len(grouped)}), flush=True)

    components, lrs, by_lr = evaluator._j_component_data()
    j_start = time.perf_counter()
    j_by_r, domains = [], 0
    for r in evaluator._r_values_j():
        value, count = evaluator.evaluate_j_r_transfer(
            lrs, by_lr, amplitudes, r, args.progress)
        j_by_r.append(value)
        domains += count
    j_seconds = time.perf_counter() - j_start
    numerator = scalar(48) * sum(j_by_r, evaluator.zero)
    quotient = numerator / denominator
    hashes_end = {key: file_sha(path) for key, path in paths.items()}
    gates = {
        "dependencies_unchanged": hashes_start == hashes_end,
        "input_unchanged": file_sha(args.input_json) == input_sha,
        "multiplier_unchanged":
            file_sha(args.multiplier_json) == multiplier_sha,
        "i_stage_unchanged": file_sha(stage_path) == stage_sha,
        "inputs_pinned": True,
        "counts_complete": len(grouped) ==
            (20 if len(labels) == 12 else 1575) and i_faces == 312 and
            len(components) == (19 if len(labels) == 12 else 695) and
            domains == 1200,
        "denominator_positive": denominator > 0,
        "finite": all(x.is_finite() for x in
                      (denominator, numerator, quotient)),
    }
    passed = all(gates.values())
    output = {
        "status": ("multiprecision-transferred-quadratic-candidate" if passed
                   else "rejected-transferred-quadratic-candidate"),
        "rigorous": False,
        "complete": True,
        "space_note": ("one transferred exact-D4 rational D2 multiplier; "
                       "not a D12 multiplier-space optimum"),
        "theorem_ready": False,
        "decimal_dps": args.decimal_dps,
        "input_json": args.input_json,
        "input_sha256": input_sha,
        "multiplier_json": args.multiplier_json,
        "multiplier_sha256": multiplier_sha,
        "parameters": PARAMETERS,
        "dependency_hashes": hashes_start,
        "fixed_basis_dimension": len(labels),
        "multiplier_dimension": 96,
        "i_stage_json": stage_path,
        "i_stage_sha256": stage_sha,
        "i_by_r": [str(x) for x in i_by_r],
        "j_by_common_r": [str(x) for x in j_by_r],
        "denominator": str(denominator),
        "numerator": str(numerator),
        "quotient": str(quotient),
        "margin": str(numerator - denominator),
        "margin_positive": numerator > denominator,
        "i_orbit_groups": len(grouped),
        "i_faces": i_faces,
        "marginal_components": len(components),
        "j_branch_domains": domains,
        "i_seconds": i_seconds,
        "j_seconds": j_seconds,
        "total_seconds": time.perf_counter() - start,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "gates": gates,
        "gates_passed": passed,
    }
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({key: output[key] for key in (
        "status", "quotient", "margin", "margin_positive", "i_seconds",
        "j_seconds", "total_seconds", "peak_rss_kib", "gates_passed")},
        indent=2))
    if not passed:
        raise SystemExit("quadratic transfer failed a gate")


if __name__ == "__main__":
    main()
