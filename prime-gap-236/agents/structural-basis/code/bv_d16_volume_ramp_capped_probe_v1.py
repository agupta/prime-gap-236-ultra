#!/usr/bin/env python3
"""Staged capped evaluation of a dilated BV D16 polynomial.

This is discovery infrastructure.  It evaluates the *audited* volume-ramp
geometry, but Decimal arithmetic is not a certificate.  The important
decomposition is

    inner = full simplex(alpha_1),
    shell = scheduled(alpha_2) - scheduled(alpha_1).

Thus the inner block is never confused with the scheduled low subtraction.
Cross-support J integrals are assembled from ordered literal marginal
branches, with no polarization factor hidden in the orbit product.

The command is deliberately staged by a single large-count index.  A cheap
cost probe can therefore be run before authorizing the complete k=48
traversal.  Every output records the separate I total-count and J
common-count pieces needed for a later Definition-5 amplitude pencil and for
the finer count-amplitude matrix.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction as Q
import hashlib
import json
from math import comb
import os
from pathlib import Path
import resource
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
EI_DIR = REPO / "agents/exact-integrator"
EI_SRC = EI_DIR / "src"
sys.path[:0] = [str(EI_SRC), str(EI_DIR), str(FILE.parent)]

import exact_integrator as ei  # noqa: E402
import grouped_fixed_vector as grouped  # noqa: E402
import fixed_vector_support_kernel as kernel_core  # noqa: E402


K = 48
DEGREE = 16
DELTA = Q(361, 50000)
ALPHA_INNER = Q(103, 400)
ETA_INNER = Q(97, 400)
ALPHA_OUTER = Q(3211, 12000)
ETA_OUTER = Q(3031, 12000)
NATURAL_C = ALPHA_INNER / ALPHA_OUTER
BRANCHES = ("Sdelta", "Stotal", "Ltotal", "Lbig")

CERT = REPO / "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json"
UNCAPPED = REPO / (
    "agents/structural-basis/results/"
    "bv_D16_dilation_Definition5_two_band_exact_v2.json")
PIECEWISE_SCRIPT = REPO / "scripts/evaluate_two_band_piecewise_dilations.py"
PIECEWISE = REPO / (
    "results/wide_c722_D16_piecewise_cinner1_couter_natural_exact.json")
ANALYTIC = REPO / (
    "agents/audit/results/wide_c722_volume_ramp_analytic_audit.json")
SHELL_DIAGNOSTIC = REPO / (
    "agents/small-delta-frontier/results/"
    "wide_volume_ramp_shell_stratum_pencil_v3.json")

PINNED = {
    EI_SRC / "exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    EI_DIR / "grouped_fixed_vector.py":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    FILE.parent / "fixed_vector_support_kernel.py":
        "774b8f3a09d77d79d6e4abe56cce4ed1eb82fc5f71ca08cb033bd383091073a3",
    CERT:
        "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62",
    UNCAPPED:
        "05410084611a86d04877ebe2b73a17899e45915fdf1b9b466a25996d28db3171",
    PIECEWISE_SCRIPT:
        "f3bbc9c6c35e2cb8b1ac7ce6accf56144c01099be81dfe288407b4552165b7bb",
    PIECEWISE:
        "e30a9a5f356b0303559bd1d3c1cb7a48474e973ec97b164c00832c919f761cb7",
    ANALYTIC:
        "88b6e1aeb04bd2e7d8600e5f4a7bcca8726b5307b95e5a4e9337a20c8f7afa96",
    SHELL_DIAGNOSTIC:
        "5ad7b42edfcae72b27a0e6221a1f5c1296695749c56d69309e01f0d505abdaf9",
}


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def canonical_q(value: Q) -> str:
    value = Q(value)
    return (str(value.numerator) if value.denominator == 1 else
            f"{value.numerator}/{value.denominator}")


def parse_q(text: str) -> Q:
    if not isinstance(text, str):
        raise TypeError("rational must be a string")
    value = Q(text)
    if canonical_q(value) != text:
        raise ValueError("noncanonical rational")
    return value


def strict_json_bytes(data: bytes):
    def pairs(items):
        answer = {}
        for key, value in items:
            if key in answer:
                raise ValueError(f"duplicate JSON key: {key}")
            answer[key] = value
        return answer

    def reject(token):
        raise ValueError(f"non-exact JSON token: {token}")

    return json.loads(data, object_pairs_hook=pairs, parse_float=reject,
                      parse_constant=reject)


def require_pins():
    found = {}
    for path, expected in PINNED.items():
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"pinned dependency changed: {path}: {actual}")
        found[str(path.relative_to(REPO))] = actual
    return found


def volume_ramp_schedule():
    return tuple(min(Q(49, 625) + (m - 1) * DELTA, Q(1599, 10000))
                 for m in range(1, 24))


SCHEDULE = volume_ramp_schedule()


@dataclass(frozen=True)
class ScheduledSupport(ei.OneStratumSupport):
    schedule: tuple = ()

    @classmethod
    def make(cls, k, alpha, delta, eta, schedule):
        schedule = tuple(schedule)
        if (isinstance(k, bool) or not isinstance(k, int) or k < 1 or
                not schedule or len(schedule) > k or
                any(value <= delta for value in schedule)):
            raise ValueError("invalid scheduled support")
        if any(right < left or right > left + delta
               for left, right in zip(schedule, schedule[1:])):
            raise ValueError("invalid scheduled transition")
        return cls(k, alpha, delta, eta, schedule[0],
                   schedule[min(1, len(schedule) - 1)],
                   schedule[min(2, len(schedule) - 1)], schedule)

    def beta(self, r):
        if isinstance(r, bool) or not isinstance(r, int) or r <= 0:
            raise ValueError("beta requires positive integer count")
        return self.schedule[min(r, len(self.schedule)) - 1]


def validate_geometry_sources():
    analytic = strict_json_bytes(ANALYTIC.read_bytes())
    expected_parameters = {
        "A": ["-3/400", "1/4", "3121/12000"],
        "delta": "361/50000", "epsilon": "3/400",
        "iic_aux_width": "288800001/40000000000",
        "inner_active": list(range(36)),
        "inward": "1/100000000000", "k": K,
        "outer_active": list(range(23)),
        "outer_cap": "1599/10000", "outer_start": "49/625",
        "source_zeta_max": "1/10000000000000",
    }
    if (analytic.get("status") != "AUDIT PASS" or
            analytic.get("parameters") != expected_parameters or
            analytic.get("schedule_id") != "volume-ramp"):
        raise ValueError("analytic volume-ramp artifact changed schema")
    diagnostic = strict_json_bytes(SHELL_DIAGNOSTIC.read_bytes())
    if (diagnostic.get("active_strata") != list(range(23)) or
            tuple(parse_q(x) for x in
                  diagnostic.get("parameters", {}).get(
                      "outer_schedule", ())) !=
            SCHEDULE):
        raise ValueError("shell diagnostic schedule changed")


def load_piecewise_exact_base():
    """Bind the exact c_inner=1, c_outer=NATURAL_C uncapped pencil.

    In particular the inner entries are independently tied back to the
    certificate's exact forms; no natural-c inner block can be substituted.
    """
    raw = strict_json_bytes(PIECEWISE.read_bytes())
    cert = strict_json_bytes(CERT.read_bytes())
    if (raw.get("status") != "exact-search-point" or
            raw.get("script_sha256") != PINNED[PIECEWISE_SCRIPT] or
            raw.get("certificate_sha256") != PINNED[CERT] or
            raw.get("parameters") != {
                "alpha1": "103/400", "alpha2": "3211/12000",
                "delta": "361/50000", "eta1": "97/400",
                "eta2": "3031/12000", "inner_c": "1", "k": K,
                "outer_c": canonical_q(NATURAL_C)}):
        raise ValueError("piecewise exact artifact changed schema")
    a = [[parse_q(x) for x in row] for row in raw.get("I_matrix", ())]
    b = [[parse_q(x) for x in row] for row in raw.get("kJ_matrix", ())]
    if (len(a) != 2 or len(b) != 2 or any(len(row) != 2 for row in a + b)
            or a[0][1] or a[1][0] or b[0][1] != b[1][0] or
            a[0][0] != parse_q(cert["exact_denominator"]) or
            b[0][0] != parse_q(cert["exact_numerator"])):
        raise ArithmeticError("piecewise exact form binding failed")
    return {"I_matrix": [[canonical_q(x) for x in row] for row in a],
            "kJ_matrix": [[canonical_q(x) for x in row] for row in b],
            "inner_exact_quotient": canonical_q(b[0][0] / a[0][0]),
            "best_uncapped_row": raw["rows"][1],
            "artifact_sha256": PINNED[PIECEWISE]}


def load_source():
    require_pins()
    validate_geometry_sources()
    raw = strict_json_bytes(CERT.read_bytes())
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in raw.get("basis", ()))
    vector = tuple(parse_q(x) for x in raw.get("rational_vector", ()))
    if (raw.get("k") != K or raw.get("degree") != DEGREE or
            basis != tuple(ei.even_basis(DEGREE)) or len(vector) != 307 or
            raw.get("parameters") != {
                "alpha": "103/400", "beta1": "103/400",
                "beta2": "103/400", "beta3plus": "103/400",
                "delta": "7/250", "eta": "97/400"}):
        raise ValueError("source certificate schema changed")
    return basis, vector


def dilate(basis, vector, c):
    c = Q(c)
    if not Q(9, 10) < c < Q(11, 10):
        raise ValueError("dilation outside frozen discovery interval")
    index = {label: i for i, label in enumerate(basis)}
    if len(index) != len(basis):
        raise ValueError("duplicate basis labels")
    answer = [Q(0)] * len(basis)
    for coefficient, (a, lam) in zip(vector, basis):
        for b in range(a + 1):
            target = index.get((b, lam))
            if target is None:
                raise ValueError("dilation left finite basis")
            answer[target] += (coefficient * comb(a, b) *
                               (1 - c) ** (a - b) *
                               c ** (b + sum(lam)))
    return tuple(answer)


def transformed_source_bytes(c):
    basis, source = load_source()
    vector = dilate(basis, source, c)
    payload = {
        "basis": [[a, list(lam)] for a, lam in basis],
        "basis_dimension": len(basis),
        "degree": DEGREE,
        "k": K,
        "rational_vector": [canonical_q(x) for x in vector],
    }
    return ((json.dumps(payload, sort_keys=True, separators=(",", ":")) +
             "\n").encode("ascii"), basis, vector)


def as_scalar(value, scalar):
    value = Q(value)
    return scalar(value.numerator) / scalar(value.denominator)


def prepare_decimal(inner_c, outer_c, dps):
    inner_bytes, basis, inner_vector = transformed_source_bytes(inner_c)
    outer_bytes, outer_basis, outer_vector = transformed_source_bytes(outer_c)
    if outer_basis != basis:
        raise ArithmeticError("inner/outer transformed bases differ")
    # Compile every exact orbit product before Decimal monkeypatching.
    inner_kernel = kernel_core.compile_kernel_bytes(inner_bytes)
    outer_kernel = kernel_core.compile_kernel_bytes(outer_bytes)
    if inner_kernel.orbit_products != outer_kernel.orbit_products:
        raise ArithmeticError("inner/outer orbit algebras differ")
    orbit_table = dict(outer_kernel.orbit_products)
    scalar = grouped.install_decimal(orbit_table, dps)
    return ({"inner": inner_kernel, "outer": outer_kernel}, scalar, basis,
            {"inner": inner_vector, "outer": outer_vector},
            {"inner": sha256(inner_bytes), "outer": sha256(outer_bytes)})


def make_supports(scalar):
    convert = lambda x: as_scalar(x, scalar)
    schedule = tuple(convert(x) for x in SCHEDULE)
    inner_eta1 = ei.OneStratumSupport(
        K, convert(ALPHA_INNER), convert(DELTA), convert(ETA_INNER),
        convert(ALPHA_INNER), convert(ALPHA_INNER), convert(ALPHA_INNER))
    inner_eta2 = ei.OneStratumSupport(
        K, convert(ALPHA_INNER), convert(DELTA), convert(ETA_OUTER),
        convert(ALPHA_INNER), convert(ALPHA_INNER), convert(ALPHA_INNER))
    high = ScheduledSupport.make(
        K, convert(ALPHA_OUTER), convert(DELTA), convert(ETA_OUTER), schedule)
    low = ScheduledSupport.make(
        K, convert(ALPHA_INNER), convert(DELTA), convert(ETA_OUTER), schedule)
    return {"inner_eta1": inner_eta1, "inner_eta2": inner_eta2,
            "high": high, "low": low}


def component_data(evaluator):
    components = evaluator.marginal_components()
    lrs = tuple(sorted({lr for lr, _, _ in components}))
    by_lr = {lr: tuple((e, a, value)
                       for (other, e, a), value in components.items()
                       if other == lr)
             for lr in lrs}
    return lrs, by_lr


def active_branch_blocks(evaluator, data, r, h, dimension, outer):
    """Marginal orbit polynomials on every positive-measure branch."""
    lrs, by_lr = data
    answer = {}
    for branch in BRANCHES:
        constraints = evaluator.support._branch_constraints(r, h, branch)
        if dimension == 0:
            interval = evaluator.support._branch_interval(0, 0, branch)
            active = (interval is not None and
                      interval[0] <= evaluator.zero <= interval[1])
        else:
            active = (constraints is not None and evaluator.integrate_domain(
                {(0, 0): evaluator.one}, dimension, r, outer,
                constraints) > evaluator.zero)
        block = {}
        if active:
            for lr in lrs:
                polynomial = defaultdict(evaluator.scalar)
                for e, a, coefficient in by_lr[lr]:
                    grouped.add_poly(
                        polynomial,
                        dict(evaluator.support._marginal_poly(
                            r, h, branch, e, a)), coefficient)
                if polynomial:
                    block[lr] = dict(polynomial)
        answer[branch] = (block, constraints) if block else ({}, constraints)
    return answer


def branch_total_r(common_r, branch):
    if branch in ("Sdelta", "Stotal"):
        return common_r
    if branch in ("Ltotal", "Lbig"):
        return common_r + 1
    raise ValueError("unknown branch")


def ordered_orbit_product(left, right, evaluator):
    """Product of two ordered marginal blocks; deliberately no factor two."""
    combined = {}
    for left_orbit, left_poly in left.items():
        for right_orbit, right_poly in right.items():
            product = ei._poly_mul(left_poly, right_poly)
            for nu, multiplicity in evaluator.kernel.orbit_lookup(
                    left_orbit, right_orbit):
                destination = combined.setdefault(
                    nu, defaultdict(evaluator.scalar))
                grouped.add_poly(destination, product,
                                 evaluator.scalar(multiplicity))
    return {nu: dict(poly) for nu, poly in combined.items() if poly}


def cross_bundle_r(supports, kernels, scalar, pair_names, r, progress=False,
                   selected_h=None):
    """Evaluate ordered J cross tables for one common large count.

    The returned sparse tables are indexed by the *total* large counts of the
    left and right marginal.  Hence shell count amplitudes can be assembled
    without re-running the branch traversal.
    """
    support_k = next(iter(supports.values())).k
    if isinstance(r, bool) or not isinstance(r, int) or not 0 <= r < support_k:
        raise ValueError("invalid common count")
    if isinstance(kernels, kernel_core.FixedVectorKernel):
        kernel_by_name = {name: kernels for name in supports}
    else:
        kernel_by_name = dict(kernels)
        if set(kernel_by_name) != set(supports):
            raise ValueError("support/kernel name inventory differs")
    evaluators = {
        name: kernel_core.KernelEvaluator(
            support, kernel_by_name[name], scalar)
        for name, support in supports.items()}
    data = {name: component_data(evaluator)
            for name, evaluator in evaluators.items()}
    if any(support.k != support_k for support in supports.values()):
        raise ValueError("cross support dimensions disagree")
    tables = {tag: defaultdict(scalar) for tag, _, _ in pair_names}
    counts = {tag: 0 for tag, _, _ in pair_names}
    dimension = support_k - 1
    max_h = int(supports[next(iter(supports))].eta /
                supports[next(iter(supports))].delta) - r
    if max_h < 0:
        return {tag: {} for tag in pair_names}, counts, 0
    dummy = next(iter(evaluators.values()))
    faces = 0
    h_values = range(max_h + 1)
    if selected_h is not None:
        if (isinstance(selected_h, bool) or not isinstance(selected_h, int) or
                not 0 <= selected_h <= max_h):
            raise ValueError("selected h outside common-count face range")
        h_values = (selected_h,)
    for h in h_values:
        if dimension == 0 and (r or h):
            continue
        outer = dummy.support.eta - (r + h) * dummy.support.delta
        if outer <= dummy.zero:
            continue
        blocks = {name: active_branch_blocks(
            evaluators[name], data[name], r, h, dimension, outer)
                  for name in supports}
        faces += 1
        for tag, left_name, right_name in pair_names:
            left_eval = evaluators[left_name]
            right_eval = evaluators[right_name]
            if (left_eval.support.delta != right_eval.support.delta or
                    left_eval.support.eta != right_eval.support.eta):
                raise ValueError("cross supports disagree in delta/eta")
            for left_branch in BRANCHES:
                left_block, left_constraints = blocks[left_name][left_branch]
                if not left_block or left_constraints is None:
                    continue
                for right_branch in BRANCHES:
                    right_block, right_constraints = \
                        blocks[right_name][right_branch]
                    if not right_block or right_constraints is None:
                        continue
                    constraints = left_constraints + right_constraints
                    if dimension != 0 and dummy.integrate_domain(
                            {(0, 0): dummy.one}, dimension, r, outer,
                            constraints) <= dummy.zero:
                        continue
                    combined = ordered_orbit_product(
                        left_block, right_block, dummy)
                    integrand = defaultdict(scalar)
                    for nu, marginal_poly in combined.items():
                        density = dummy.orbit_density(
                            dimension, nu, r, h, max_h)
                        if density:
                            grouped.add_poly(
                                integrand,
                                ei._poly_mul(density, marginal_poly),
                                dummy.one)
                    if not integrand:
                        continue
                    value = dummy.integrate_domain(
                        dict(integrand), dimension, r, outer, constraints)
                    key = (branch_total_r(r, left_branch),
                           branch_total_r(r, right_branch))
                    tables[tag][key] += value
                    counts[tag] += 1
        if progress:
            print(f"J common_r={r} h={h}/{max_h} counts={counts}",
                  file=sys.stderr, flush=True)
        # All support pairs have consumed this face.  Bound global caches now.
        dummy.clear_face_caches(clear_marginals=True)
    dummy.clear_radial_caches()
    return ({tag: {key: value for key, value in table.items() if value}
             for tag, table in tables.items()}, counts, faces)


def i_shell_r(supports, kernel, scalar, r, progress=False):
    high = kernel_core.KernelEvaluator(supports["high"], kernel, scalar)
    low = kernel_core.KernelEvaluator(supports["low"], kernel, scalar)
    high_value, high_faces = high.evaluate_i_r(
        high.square_residual_terms(), r, progress)
    low_value, low_faces = low.evaluate_i_r(
        low.square_residual_terms(), r, progress)
    return high_value, low_value, high_value - low_value, {
        "high": high_faces, "low": low_faces}


def encode_scalar(value):
    return str(value)


def encode_table(table):
    return [{"left_total_count": left, "right_total_count": right,
             "value": encode_scalar(value)}
            for (left, right), value in sorted(table.items())]


def run_stage(inner_c, outer_c, dps, total_r, common_r, block_tags,
              progress=False, selected_h=None):
    started = time.monotonic()
    pins = require_pins()
    self_start = sha256(FILE)
    kernels, scalar, _, _, transformed_sha = prepare_decimal(
        inner_c, outer_c, dps)
    supports = make_supports(scalar)
    preparation_seconds = time.monotonic() - started
    result = {
        "status": "capped-volume-ramp-dilated-D16-Decimal-stage",
        "rigorous": False,
        "theorem_ready": False,
        "scope": ("one staged I total-count and/or J common-count; fresh "
                  "full Decimal traversal is required for every omitted row"),
        "parameters": {
            "k": K, "degree": DEGREE,
            "inner_dilation_c": canonical_q(inner_c),
            "outer_dilation_c": canonical_q(outer_c),
            "alpha_inner": canonical_q(ALPHA_INNER),
            "eta_inner": canonical_q(ETA_INNER),
            "alpha_outer": canonical_q(ALPHA_OUTER),
            "eta_outer": canonical_q(ETA_OUTER),
            "delta": canonical_q(DELTA),
            "schedule": [canonical_q(x) for x in SCHEDULE],
        },
        "decimal_dps": dps,
        "transformed_source_sha256": transformed_sha,
        "piecewise_exact_base": (load_piecewise_exact_base()
                                  if (inner_c, outer_c) ==
                                  (Q(1), NATURAL_C) else None),
        "source_hashes": pins,
        "script_sha256": self_start,
        "preparation_seconds": preparation_seconds,
        "i_stage": None,
        "j_stage": None,
    }
    if total_r is not None:
        before = time.monotonic()
        hi, lo, shell, faces = i_shell_r(
            supports, kernels["outer"], scalar, total_r, progress)
        result["i_stage"] = {
            "total_count": total_r, "high": encode_scalar(hi),
            "scheduled_low": encode_scalar(lo),
            "shell_difference": encode_scalar(shell), "faces": faces,
            "shell_nonnegative_observed": shell >= scalar(0),
            "seconds": time.monotonic() - before,
        }
    if common_r is not None:
        pair_catalog = {
            "fh": ("inner_eta2", "high"),
            "fl": ("inner_eta2", "low"),
            "hh": ("high", "high"),
            "hl": ("high", "low"),
            "ll": ("low", "low"),
        }
        selected = tuple((tag, *pair_catalog[tag]) for tag in block_tags)
        needed = {name: supports[name]
                  for _, left, right in selected
                  for name in (left, right)}
        needed_kernels = {
            name: kernels["inner" if name == "inner_eta2" else "outer"]
            for name in needed}
        before = time.monotonic()
        tables, counts, faces = cross_bundle_r(
            needed, needed_kernels, scalar, selected, common_r, progress,
            selected_h)
        result["j_stage"] = {
            "common_count": common_r,
            "selected_inclusion_exclusion_h": selected_h,
            "complete_common_count": selected_h is None,
            "ordered_cross_semantics": True,
            "hidden_factor_two": False,
            "tables": {tag: encode_table(tables[tag]) for tag in block_tags},
            "branch_domain_integrals": counts,
            "faces": faces,
            "seconds": time.monotonic() - before,
        }
    result["wall_seconds"] = time.monotonic() - started
    result["peak_rss_kib"] = resource.getrusage(
        resource.RUSAGE_SELF).ru_maxrss
    result["child_peak_rss_kib"] = resource.getrusage(
        resource.RUSAGE_CHILDREN).ru_maxrss
    if sha256(FILE) != self_start or require_pins() != pins:
        raise RuntimeError("source changed during staged traversal")
    return result


def write_new(path, payload):
    target = Path(path).resolve()
    protected = {FILE, *PINNED}
    if target in protected:
        raise ValueError("output aliases protected input")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inner-c", default="1")
    parser.add_argument("--outer-c", default=canonical_q(NATURAL_C))
    parser.add_argument("--decimal-dps", type=int, choices=(80, 100),
                        default=80)
    parser.add_argument("--total-r", type=int)
    parser.add_argument("--common-r", type=int)
    parser.add_argument("--j-h", type=int)
    parser.add_argument("--blocks", default="fh,fl,hh,hl,ll")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    inner_c = parse_q(args.inner_c)
    outer_c = parse_q(args.outer_c)
    tags = tuple(x for x in args.blocks.split(",") if x)
    if len(tags) != len(set(tags)) or any(
            x not in {"fh", "fl", "hh", "hl", "ll"} for x in tags):
        parser.error("--blocks is a unique CSV subset of fh,fl,hh,hl,ll")
    if args.preflight_only:
        pins = require_pins()
        validate_geometry_sources()
        print(json.dumps({
            "status": "preflight-pass", "script_sha256": sha256(FILE),
            "source_hashes": pins,
            "inner_dilation_c": canonical_q(inner_c),
            "outer_dilation_c": canonical_q(outer_c),
            "decimal_dps": args.decimal_dps,
            "active_total_counts": list(range(23)),
            "target_run_started": False,
        }, sort_keys=True, indent=2))
        return
    if args.output is None or (args.total_r is None and args.common_r is None):
        parser.error("stage requires --output and --total-r and/or --common-r")
    for name, value in (("total-r", args.total_r),
                        ("common-r", args.common_r)):
        if value is not None and not 0 <= value <= 22:
            parser.error(f"--{name} must lie in 0..22")
    if args.j_h is not None and args.common_r is None:
        parser.error("--j-h requires --common-r")
    result = run_stage(inner_c, outer_c, args.decimal_dps, args.total_r,
                       args.common_r, tags, args.progress, args.j_h)
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    write_new(args.output, payload)
    print(json.dumps({"artifact_sha256": sha256(payload),
                      "wall_seconds": result["wall_seconds"],
                      "peak_rss_kib": result["peak_rss_kib"],
                      "i_stage": result["i_stage"],
                      "j_counts": (None if result["j_stage"] is None else
                                   result["j_stage"][
                                       "branch_domain_integrals"])},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
