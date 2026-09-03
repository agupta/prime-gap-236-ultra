#!/usr/bin/env python3
r"""Exact large-count diagnostic for the wide volume-ramp outer shell.

The function studied here is the constant on

    S(alpha2, B_outer) \ S(alpha1, B_outer).

It is split by the exact total count ``R`` of coordinates exceeding delta.
The I form is diagonal in R.  In J the distinguished coordinate changes R
by at most one, so the exact shell-only matrix is tridiagonal.  Four
cross-support marginal tables implement inclusion--exclusion; no D16 base
cross form is evaluated here.

The Decimal eigensolve is discovery only.  Every emitted matrix entry and
the particular rational-vector contraction are exact Fractions.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import resource
import sys
import time
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
HERE = FILE.parent
REPO = FILE.parents[2]
EI_SRC = REPO / "agents/exact-integrator/src"
EI_DIR = REPO / "agents/exact-integrator"
sys.path[:0] = [str(EI_SRC), str(EI_DIR)]

PINNED = {
    EI_SRC / "exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    EI_SRC / "stratum_integrator.py":
        "0566f77860b0b61ce0ed342b5bb3a4743990725099d8b0cd6e685efad3c7394f",
    EI_DIR / "grouped_fixed_vector.py":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    REPO / "agents/audit/results/wide_c722_volume_ramp_analytic_audit.json":
        "88b6e1aeb04bd2e7d8600e5f4a7bcca8726b5307b95e5a4e9337a20c8f7afa96",
}


def sha256(path_or_bytes) -> str:
    data = (path_or_bytes if isinstance(path_or_bytes, bytes)
            else Path(path_or_bytes).read_bytes())
    return hashlib.sha256(data).hexdigest()


def require_pins() -> dict[str, str]:
    found = {}
    for path, expected in PINNED.items():
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"pinned dependency changed: {path}: {actual}")
        found[str(path.relative_to(REPO))] = actual
    return found


require_pins()
import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import GroupedEvaluator, add_poly  # noqa: E402

_STRATUM_PATH = EI_SRC / "stratum_integrator.py"
_spec = importlib.util.spec_from_file_location("wide_shell_stratum_core",
                                               _STRATUM_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError("cannot load exact stratum integrator")
stratum_core = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = stratum_core
_spec.loader.exec_module(stratum_core)


K = 48
DELTA = Q(361, 50000)
EPSILON = Q(3, 400)
A1 = Q(1, 4)
A2 = Q(3121, 12000)
ALPHA1 = A1 + EPSILON
ALPHA2 = A2 + EPSILON
ETA2 = A2 - EPSILON
SCHEDULE = tuple(min(Q(49, 625) + (m - 1) * DELTA, Q(1599, 10000))
                 for m in range(1, 24))
BRANCHES = ("Sdelta", "Stotal", "Ltotal", "Lbig")


@dataclass(frozen=True)
class ScheduledStratumSupport(stratum_core.StratumSupport):
    schedule: tuple[Q, ...] = ()

    @classmethod
    def make(cls, k: int, alpha: Q, eta: Q,
             delta: Q, schedule: tuple[Q, ...]):
        schedule = tuple(schedule)
        if not 1 <= len(schedule) <= k:
            raise ValueError("invalid schedule length")
        if any(not isinstance(x, Q) or x <= delta for x in schedule):
            raise ValueError("invalid schedule capacity")
        if any(right < left or right > left + delta
               for left, right in zip(schedule, schedule[1:])):
            raise ValueError("schedule violates Definition 1 transitions")
        return cls(k, alpha, delta, eta, schedule[0],
                   schedule[min(1, len(schedule) - 1)],
                   schedule[min(2, len(schedule) - 1)], schedule)

    def beta(self, r: int) -> Q:
        if r <= 0:
            raise ValueError("beta requires positive count")
        return self.schedule[min(r, len(self.schedule)) - 1]


def branch_total_r(common_r: int, branch: str) -> int:
    if branch in ("Sdelta", "Stotal"):
        return common_r
    if branch in ("Ltotal", "Lbig"):
        return common_r + 1
    raise ValueError("unknown marginal branch")


def constant_branch(support, r: int, h: int, branch: str):
    constraints = support._branch_constraints(r, h, branch)
    if constraints is None:
        return None
    polynomial = dict(support._marginal_poly(r, h, branch, 0, 0))
    return (polynomial, constraints) if polynomial else None


def cross_constant_stratum_table(left, right, common_eta: Q,
                                 *, integrate: bool = True,
                                 common_strata=None):
    """All J cross entries indexed by the two total large counts.

    Each literal marginal branch has a unique total stratum.  Consequently a
    single shared-coordinate traversal assembles the complete table without
    repeating any branch-domain integral.
    """
    if (left.k, left.delta) != (right.k, right.delta):
        raise ValueError("cross supports disagree in k or delta")
    dimension = left.k - 1
    max_r = min(dimension, left.max_large(), right.max_large())
    table = [[Q(0) for _ in range(left.k + 1)]
             for _ in range(left.k + 1)]
    dummy = GroupedEvaluator(left, [], [], Q)
    domains = 0
    selected = (range(max_r + 1) if common_strata is None else
                sorted(set(common_strata)))
    if any(type(r) is not int or not 0 <= r <= max_r for r in selected):
        raise ValueError("invalid selected common stratum")
    for r in selected:
        max_h = int(common_eta // left.delta) - r
        if max_h < 0:
            continue
        for h in range(max_h + 1):
            outer = common_eta - (r + h) * left.delta
            if outer <= 0:
                continue
            left_branches = {name: constant_branch(left, r, h, name)
                             for name in BRANCHES}
            right_branches = {name: constant_branch(right, r, h, name)
                              for name in BRANCHES}
            density = dummy.orbit_density(dimension, (), r, h, max_h)
            if not density:
                continue
            for lb, ldata in left_branches.items():
                if ldata is None:
                    continue
                lp, lc = ldata
                for rb, rdata in right_branches.items():
                    if rdata is None:
                        continue
                    rp, rc = rdata
                    domains += 1
                    if not integrate:
                        continue
                    integrand = ei._poly_mul(density, ei._poly_mul(lp, rp))
                    value = dummy.integrate_domain(
                        integrand, dimension, r, outer, lc + rc)
                    table[branch_total_r(r, lb)][branch_total_r(r, rb)] += value
            dummy.clear_face_caches(clear_marginals=True)
        dummy.clear_radial_caches()
    return table, domains


def matrix_add(*terms):
    """Linear combination ``sum(coefficient * matrix)``."""
    if not terms:
        raise ValueError("empty matrix sum")
    n = len(terms[0][1])
    if any(len(matrix) != n or any(len(row) != n for row in matrix)
           for _, matrix in terms):
        raise ValueError("matrix dimensions disagree")
    return [[sum((coefficient * matrix[i][j]
                  for coefficient, matrix in terms), Q(0))
             for j in range(n)] for i in range(n)]


def exact_quadratic(matrix, vector):
    return sum((vector[i] * matrix[i][j] * vector[j]
                for i in range(len(vector)) for j in range(len(vector))), Q(0))


def tridiagonal_upper_bound_ldl(a_diag, b_diag, b_super, upper_bound: Q):
    """Exact LDL pivots of ``upper_bound*A-B``.

    Strict positivity of every returned pivot proves the corresponding
    generalized Rayleigh quotient is strictly below ``upper_bound`` for every
    nonzero vector; no numerical eigenvalue or positive-definiteness assumption
    is used.
    """
    n = len(a_diag)
    if (len(b_diag) != n or len(b_super) != max(0, n - 1) or
            not isinstance(upper_bound, Q)):
        raise ValueError("invalid tridiagonal pencil")
    pivots = []
    for i in range(n):
        value = upper_bound * a_diag[i] - b_diag[i]
        if i:
            if pivots[-1] == 0:
                raise ArithmeticError("zero preceding LDL pivot")
            value -= b_super[i - 1] * b_super[i - 1] / pivots[-1]
        pivots.append(value)
    return pivots


def decimal_jacobi_diagonal_gram(a_diag, b_matrix, precision: int):
    """Discovery solve after exact diagonal whitening."""
    with localcontext() as context:
        context.prec = precision

        def dec(value: Q) -> Decimal:
            return Decimal(value.numerator) / Decimal(value.denominator)

        n = len(a_diag)
        scales = [dec(x).sqrt() for x in a_diag]
        if any(x <= 0 for x in scales):
            raise ArithmeticError("nonpositive exact I diagonal")
        matrix = [[dec(b_matrix[i][j]) / scales[i] / scales[j]
                   for j in range(n)] for i in range(n)]
        zero, one = Decimal(0), Decimal(1)
        vectors = [[one if i == j else zero for j in range(n)]
                   for i in range(n)]
        tolerance = Decimal(10) ** (-(precision - 25))
        max_rotations = 20000 * max(1, n)
        for rotation in range(max_rotations):
            p, q, largest = 0, 0, zero
            for i in range(n):
                for j in range(i):
                    if abs(matrix[i][j]) > largest:
                        p, q, largest = j, i, abs(matrix[i][j])
            scale = max(one, max(abs(matrix[i][i]) for i in range(n)))
            if largest <= tolerance * scale:
                values = [matrix[i][i] for i in range(n)]
                winner = max(range(n), key=values.__getitem__)
                y = [vectors[i][winner] for i in range(n)]
                original = [y[i] / scales[i] for i in range(n)]
                normalization = max(abs(x) for x in original)
                original = [x / normalization for x in original]
                av = [dec(a_diag[i]) * original[i] for i in range(n)]
                bv = [sum((dec(b_matrix[i][j]) * original[j]
                           for j in range(n)), zero) for i in range(n)]
                denominator = sum((original[i] * av[i]
                                   for i in range(n)), zero)
                quotient = sum((original[i] * bv[i]
                                for i in range(n)), zero) / denominator
                residual = max(abs(bv[i] - quotient * av[i]) for i in range(n))
                residual_scale = max(one, max(abs(x) for x in bv),
                                     abs(quotient) * max(abs(x) for x in av))
                return {"precision": precision,
                        "eigenvalue": str(values[winner]),
                        "rayleigh_quotient": str(quotient),
                        "relative_residual_bound": str(residual / residual_scale),
                        "jacobi_rotations": rotation,
                        "vector": [str(x) for x in original]}
            apq, app, aqq = matrix[p][q], matrix[p][p], matrix[q][q]
            tau = (aqq - app) / (2 * apq)
            sign = one if tau >= 0 else -one
            t = sign / (abs(tau) + (one + tau * tau).sqrt())
            c = one / (one + t * t).sqrt()
            s = t * c
            for index in range(n):
                if index in (p, q):
                    continue
                aip, aiq = matrix[index][p], matrix[index][q]
                matrix[index][p] = matrix[p][index] = c * aip - s * aiq
                matrix[index][q] = matrix[q][index] = s * aip + c * aiq
            matrix[p][p] = app - t * apq
            matrix[q][q] = aqq + t * apq
            matrix[p][q] = matrix[q][p] = zero
            for index in range(n):
                vip, viq = vectors[index][p], vectors[index][q]
                vectors[index][p] = c * vip - s * viq
                vectors[index][q] = s * vip + c * viq
        raise ArithmeticError("Decimal Jacobi did not converge")


def validate_analytic_artifact() -> str:
    path = REPO / "agents/audit/results/wide_c722_volume_ramp_analytic_audit.json"
    data = json.loads(path.read_bytes())
    parameters = data.get("parameters", {})
    if (data.get("status") != "AUDIT PASS" or
            data.get("schedule_id") != "volume-ramp" or
            parameters.get("k") != K or
            parameters.get("epsilon") != str(EPSILON) or
            parameters.get("delta") != str(DELTA) or
            parameters.get("A") != [str(-EPSILON), str(A1), str(A2)] or
            parameters.get("outer_active") != list(range(23)) or
            parameters.get("outer_start") != str(SCHEDULE[0]) or
            parameters.get("outer_cap") != str(SCHEDULE[-1]) or
            data.get("c1") != "0" or data.get("c2") != "0"):
        raise ValueError("analytic volume-ramp identity changed")
    return sha256(path)


def mem_available_kib() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    raise RuntimeError("MemAvailable missing")


def make_supports(k: int = K):
    schedule = SCHEDULE if k == K else SCHEDULE[:k]
    hi = ScheduledStratumSupport.make(k, ALPHA2, ETA2, DELTA, schedule)
    lo = ScheduledStratumSupport.make(k, ALPHA1, ETA2, DELTA, schedule)
    return hi, lo


def exact_i_masses():
    hi, lo = make_supports()
    max_r = max(hi.max_large(), lo.max_large())
    masses = [hi.basis_m1_in_strata(r, (0, ()), r, (0, ())) -
              lo.basis_m1_in_strata(r, (0, ()), r, (0, ()))
              for r in range(max_r + 1)]
    if any(value < 0 for value in masses):
        raise ArithmeticError("nested-shell I mass is negative")
    expected = (hi.basis_m1((0, ()), (0, ())) -
                lo.basis_m1((0, ()), (0, ())))
    if sum(masses, Q(0)) != expected:
        raise ArithmeticError("tagged I masses do not reconstruct shell")
    return hi, lo, masses


def parameter_record():
    return {"k": K, "epsilon": str(EPSILON), "delta": str(DELTA),
            "A": [str(-EPSILON), str(A1), str(A2)],
            "alpha1": str(ALPHA1), "alpha2": str(ALPHA2),
            "eta2": str(ETA2),
            "outer_schedule": [str(x) for x in SCHEDULE]}


def i_mass_record(masses):
    total = sum(masses, Q(0))
    if total <= 0:
        raise ArithmeticError("shell has nonpositive exact mass")
    ranking = sorted(range(len(masses)), key=lambda r: masses[r],
                     reverse=True)
    return {
        "active_strata": [r for r, value in enumerate(masses) if value > 0],
        "I_total_shell": str(total),
        "mass_rank_descending": ranking,
        "top_mass_strata": ranking[:8],
        "stratum_I_rows": [
            {"R": r, "I_mass": str(value),
             "I_mass_fraction": str(value / total)}
            for r, value in enumerate(masses) if value > 0],
    }


def build_i_only_result():
    start_self_sha = sha256(FILE)
    start_pins = require_pins()
    analytic_sha = validate_analytic_artifact()
    _, _, masses = exact_i_masses()
    if require_pins() != start_pins or sha256(FILE) != start_self_sha:
        raise RuntimeError("dependency changed during exact I traversal")
    return {
        "status": "wide-volume-ramp-shell-exact-I-by-stratum",
        "claim_scope": "exact shell I mass decomposition only; no J or quotient",
        "script_sha256": start_self_sha,
        "dependency_sha256": start_pins,
        "analytic_artifact_sha256": analytic_sha,
        "parameters": parameter_record(),
        **i_mass_record(masses),
        "theorem_ready": False,
    }


def domain_inventory() -> dict[str, object]:
    validate_analytic_artifact()
    hi, lo = make_supports()
    counts = {}
    total = 0
    # J symmetry gives LH=HL^T exactly, so only three traversals are needed.
    for name, left, right in (("hh", hi, hi), ("hl", hi, lo),
                              ("ll", lo, lo)):
        _, count = cross_constant_stratum_table(
            left, right, ETA2, integrate=False)
        counts[name] = count
        total += count
    return {"domain_counts": counts, "total_domain_count": total}


def preflight() -> dict[str, object]:
    inventory = domain_inventory()
    available = mem_available_kib()
    # The traversal has one low-degree exact integral per counted domain and
    # stores only three 49x49 Fraction tables.  This deliberately conservative
    # gate is frozen before target timing is observed.
    gate = (inventory["total_domain_count"] <= 30_000 and
            available >= 1_500_000)
    return {"status": "wide-shell-stratum-diagnostic-preflight",
            **inventory,
            "mem_available_kib": available,
            "predeclared_limits": {"domains": 30_000,
                                   "minimum_mem_available_kib": 1_500_000,
                                   "estimated_wall_seconds_upper": 120,
                                   "estimated_peak_rss_kib_upper": 131072},
            "gate_pass": gate}


def build_result(precisions=(100, 160), rational_denominator=10**12):
    start_self_sha = sha256(FILE)
    start_pins = require_pins()
    analytic_sha = validate_analytic_artifact()
    before = preflight()
    if not before["gate_pass"]:
        raise RuntimeError("predeclared resource/domain gate failed")
    hi, lo, a_shell = exact_i_masses()

    tables = {}
    domain_counts = {}
    for name, left, right in (("hh", hi, hi), ("hl", hi, lo),
                              ("ll", lo, lo)):
        tables[name], domain_counts[name] = cross_constant_stratum_table(
            left, right, ETA2)
    hl_transpose = [list(row) for row in zip(*tables["hl"])]
    j_shell = matrix_add((Q(1), tables["hh"]), (Q(-1), tables["hl"]),
                         (Q(-1), hl_transpose), (Q(1), tables["ll"]))
    b_shell = [[K * value for value in row] for row in j_shell]
    if any(b_shell[i][j] != b_shell[j][i]
           for i in range(K + 1) for j in range(K + 1)):
        raise ArithmeticError("shell kJ table is not symmetric")
    if any(b_shell[i][j] != 0 for i in range(K + 1)
           for j in range(K + 1) if abs(i - j) > 1):
        raise ArithmeticError("shell kJ table is not tridiagonal")
    active = [r for r, value in enumerate(a_shell) if value > 0]
    if not active or active != list(range(active[-1] + 1)):
        raise ArithmeticError("unexpected shell I active strata")
    a_active = [a_shell[r] for r in active]
    b_active = [[b_shell[r][s] for s in active] for r in active]
    b_diag = [b_active[i][i] for i in range(len(active))]
    b_super = [b_active[i][i + 1] for i in range(len(active) - 1)]
    rigorous_upper = Q(1, 16)
    upper_pivots = tridiagonal_upper_bound_ldl(
        a_active, b_diag, b_super, rigorous_upper)
    if not all(pivot > 0 for pivot in upper_pivots):
        raise ArithmeticError("exact shell-space upper bound failed")
    solves = [decimal_jacobi_diagonal_gram(a_active, b_active, p)
              for p in precisions]
    discovered = [Q(x).limit_denominator(rational_denominator)
                  for x in solves[-1]["vector"]]
    denominator = sum((a_active[i] * discovered[i] * discovered[i]
                       for i in range(len(active))), Q(0))
    numerator = exact_quadratic(b_active, discovered)
    if denominator <= 0:
        raise ArithmeticError("rationalized shell vector has nonpositive I")
    total_mass = sum(a_active, Q(0))
    mass_order = sorted(active, key=lambda r: a_shell[r], reverse=True)
    particular_i = [a_active[i] * discovered[i] * discovered[i]
                    for i in range(len(active))]
    priority_order = sorted(active,
                            key=lambda r: particular_i[active.index(r)],
                            reverse=True)
    rows = [{"R": r, "I_mass": str(a_shell[r]),
             "I_mass_fraction": str(a_shell[r] / total_mass),
             "kJ_diagonal": str(b_shell[r][r]),
             "single_stratum_quotient":
                 str(b_shell[r][r] / a_shell[r]),
             "particular_vector_coefficient":
                 str(discovered[active.index(r)]),
             "particular_I_fraction":
                 str(particular_i[active.index(r)] / denominator),
             "kJ_super": str(b_shell[r][r + 1]) if r + 1 <= active[-1] else "0"}
            for r in active]
    if require_pins() != start_pins or sha256(FILE) != start_self_sha:
        raise RuntimeError("dependency changed during exact traversal")
    stable_gate = {
        "domain_counts": before["domain_counts"],
        "total_domain_count": before["total_domain_count"],
        "predeclared_limits": before["predeclared_limits"],
        "gate_passed_at_launch": True,
    }
    return {
        "status": "wide-volume-ramp-shell-stratum-exact-diagnostic",
        "claim_scope": (
            "exact shell-only tagged-constant I/kJ pencil and exact particular "
            "vector; no D16 cross form and no sieve quotient"),
        "script_sha256": start_self_sha,
        "dependency_sha256": start_pins,
        "analytic_artifact_sha256": analytic_sha,
        "parameters": parameter_record(),
        "active_strata": active,
        "I_total_shell": str(total_mass),
        "mass_rank_descending": mass_order,
        "top_mass_strata": mass_order[:8],
        "particular_I_rank_descending": priority_order,
        "suggested_first_cross_strata": priority_order[:6],
        "stratum_rows": rows,
        "I_diagonal": [str(x) for x in a_active],
        "kJ_diagonal": [str(x) for x in b_diag],
        "kJ_superdiagonal": [str(x) for x in b_super],
        "rigorous_all_vector_quotient_upper_bound": str(rigorous_upper),
        "upper_bound_LDL_pivots": [str(x) for x in upper_pivots],
        "upper_bound_LDL_all_positive": True,
        "finite_tagged_constant_space_no_crossing_rigorous": True,
        "domain_counts": domain_counts,
        # The exact MemAvailable observation is deliberately excluded so that
        # normal and -O artifacts can be required byte-for-byte identical.
        "resource_gate": stable_gate,
        "cross_precision_discovery": solves,
        "rational_denominator_limit": rational_denominator,
        "rational_vector": [str(x) for x in discovered],
        "exact_particular_denominator": str(denominator),
        "exact_particular_numerator": str(numerator),
        "exact_particular_quotient": str(numerator / denominator),
        "exact_particular_margin": str(numerator - denominator),
        "eigenvalue_optimality_rigorous": False,
        "particular_vector_forms_rigorous": True,
        "theorem_ready": False,
    }


def publish(path: Path, payload: bytes) -> None:
    target = path.resolve()
    protected = {FILE, *(path.resolve() for path in PINNED)}
    if target in protected:
        raise ValueError("output collides with a protected input")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb", closefd=True) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--i-only", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--precisions", default="100,160")
    parser.add_argument("--rational-denominator", type=int, default=10**12)
    args = parser.parse_args()
    if args.preflight_only:
        print(json.dumps(preflight(), sort_keys=True, indent=2))
        return
    if args.output is None:
        parser.error("--output is required unless --preflight-only")
    precisions = tuple(int(x) for x in args.precisions.split(","))
    if len(precisions) != 2 or min(precisions) < 80:
        parser.error("give exactly two comma-separated precisions >=80")
    if not 10**6 <= args.rational_denominator <= 10**18:
        parser.error("rational denominator outside frozen bounds")
    started = time.monotonic()
    result = (build_i_only_result() if args.i_only else
              build_result(precisions, args.rational_denominator))
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    publish(args.output, payload)
    print(json.dumps({"artifact_sha256": sha256(payload),
                      "exact_particular_quotient":
                          result.get("exact_particular_quotient"),
                      "top_mass_strata": result["top_mass_strata"],
                      "elapsed_seconds": time.monotonic() - started,
                      "peak_rss_kib":
                          resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
