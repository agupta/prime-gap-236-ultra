#!/usr/bin/env python3
"""D19 one-band bridge with the natural-D19 A,b projection moments.

The frozen D19 G^2 bridge is instrumented without altering its Markov chain:
the exact same retained points are captured, and the naturally dilated D19
polynomial restricted to the verified cap is evaluated on them.  Under the
frozen D18 h^2 proposal this yields A/I(F), b/I(F), and b^2/(A I(F)), where
``A=I(H)`` and ``b=48J(F,H)=<G,H>``.  Chain dispersion supplies finite-run
standard errors.  No exact target or resume path is exposed.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import sys


os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
D19_BRIDGE = FILE.with_name(
    "active25_d19_truncated_one_band_h2_bridge_v1.py")
D19_BRIDGE_SHA256 = (
    "e1e06fbbc5c79d4708e9adf6911873798bf04368449609a407b41f05cb80bd68")
D19_BRIDGE_TEST = REPO / (
    "agents/structural-basis/tests/"
    "test_active25_d19_truncated_one_band_h2_bridge_v1.py")
D19_BRIDGE_TEST_SHA256 = (
    "2669517674b1b080420e94099784948a48abd8e13ebd592102045fe6390423f3")
MAX_WALL_SECONDS = 180
MAX_RSS_BYTES = 512 * 1024 * 1024
COUNT_MONOMIALS = tuple(
    (a, d) for total in range(6) for a in range(5) for d in range(2)
    if a + d == total)
RANK_RELATIVE_CUTOFF = 1e-8


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load(name, path, expected):
    if sha256(path) != expected:
        raise RuntimeError(f"pinned projection-bridge input changed: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def chain_mean_se(values):
    values = np.asarray(values, dtype=np.longdouble)
    means = np.mean(values, axis=1, dtype=np.longdouble)
    return (float(np.mean(means, dtype=np.longdouble)),
            float(np.std(means, ddof=1) / np.sqrt(len(means))),
            [float(x) for x in means])


def projection_summary(a_moment, b_moment, scale):
    """Summarize already chain-by-draw proposal moments."""
    scale = np.longdouble(scale)
    a_mean, a_se, a_chains0 = chain_mean_se(a_moment)
    b_mean, b_se, b_chains0 = chain_mean_se(b_moment)
    a = float(scale * np.longdouble(a_mean))
    b = float(scale * np.longdouble(b_mean))
    a_se = float(scale * np.longdouble(a_se))
    b_se = float(scale * np.longdouble(b_se))
    a_chains = np.asarray(a_chains0, dtype=np.longdouble) * scale
    b_chains = np.asarray(b_chains0, dtype=np.longdouble) * scale
    if a <= 0:
        raise ArithmeticError("natural-D19 capped I norm is nonpositive")
    projection = b * b / a
    observations = np.stack((a_chains, b_chains), axis=1)
    covariance_of_mean = np.cov(
        observations, rowvar=False, ddof=1) / len(observations)
    gradient = np.asarray(
        (-(b * b) / (a * a), 2 * b / a), dtype=np.longdouble)
    variance = float(gradient @ covariance_of_mean @ gradient)
    projection_se = math.sqrt(max(variance, 0.0))
    per_chain_projection = [
        float(bb * bb / aa) if aa > 0 else None
        for aa, bb in zip(a_chains, b_chains)]
    return {
        "A_over_inner_I": a,
        "A_over_inner_I_standard_error": a_se,
        "b_over_inner_I": b,
        "b_over_inner_I_standard_error": b_se,
        "projected_energy_over_inner_I": projection,
        "projected_energy_over_inner_I_delta_standard_error": projection_se,
        "per_chain_A_over_inner_I": [float(x) for x in a_chains],
        "per_chain_b_over_inner_I": [float(x) for x in b_chains],
        "per_chain_projected_energy_over_inner_I": per_chain_projection,
        "definition": "A=I(H), b=48J(F,H), projected energy=b^2/A",
        "factor_48_note": "b already equals 48J; no additional factor",
    }


def normalized_solve(a_matrix, b_vector, relative_cutoff):
    """Stable pseudoinverse after unit-diagonal column normalization."""
    a_matrix = np.asarray(a_matrix, dtype=np.longdouble)
    b_vector = np.asarray(b_vector, dtype=np.longdouble)
    diagonal = np.sqrt(np.maximum(np.diag(a_matrix), 0))
    live = diagonal > 0
    if not np.any(live):
        return np.zeros(len(b_vector), dtype=np.longdouble), 0, math.inf, []
    corr = np.asarray(
        a_matrix[np.ix_(live, live)] /
        (diagonal[live, None] * diagonal[None, live]), dtype=np.float64)
    rhs = np.asarray(b_vector[live] / diagonal[live], dtype=np.float64)
    eigenvalues, eigenvectors = np.linalg.eigh(corr)
    cutoff = max(float(eigenvalues[-1]) * relative_cutoff,
                 np.finfo(float).eps)
    keep = eigenvalues > cutoff
    rank = int(np.sum(keep))
    normalized = np.zeros(len(rhs), dtype=np.float64)
    if rank:
        normalized = eigenvectors[:, keep] @ (
            (eigenvectors[:, keep].T @ rhs) / eigenvalues[keep])
    coefficients = np.zeros(len(b_vector), dtype=np.longdouble)
    coefficients[live] = normalized.astype(np.longdouble) / diagonal[live]
    condition = (float(eigenvalues[-1] / eigenvalues[keep][0])
                 if rank else math.inf)
    return coefficients, rank, condition, [float(x) for x in eigenvalues]


def greedy_prune(a_matrix, relative_cutoff):
    """Keep the first low-degree monomials with new normalized Gram content."""
    a_matrix = np.asarray(a_matrix, dtype=np.longdouble)
    diagonal = np.sqrt(np.maximum(np.diag(a_matrix), 0))
    candidates = [index for index, value in enumerate(diagonal) if value > 0]
    selected = []
    for index in candidates:
        if not selected:
            selected.append(index)
            continue
        block = np.asarray(
            a_matrix[np.ix_(selected, selected)] /
            (diagonal[selected, None] * diagonal[None, selected]),
            dtype=np.float64)
        cross = np.asarray(
            a_matrix[index, selected] /
            (diagonal[index] * diagonal[selected]), dtype=np.float64)
        residual = 1 - float(cross @ np.linalg.pinv(
            block, rcond=relative_cutoff) @ cross)
        if residual > relative_cutoff:
            selected.append(index)
    return selected


def count_radial_projection(*, radial_points, radial_positions, cap,
                            h18_normalized, g_ratio, scale, module,
                            one_band, chains, draws):
    """Screen count-tagged x^a y^d coordinates on captured chain points."""
    totals = np.sum(radial_points, axis=1, dtype=np.longdouble)
    large = radial_points > module.ld(one_band.DELTA)
    counts = np.sum(large, axis=1)
    large_sums = np.sum(np.where(large, radial_points, 0), axis=1,
                        dtype=np.longdouble)
    chain_index = np.asarray(radial_positions % chains, dtype=np.int64)
    x = ((totals - module.ld(one_band.ALPHA1)) /
         module.ld(one_band.ALPHA2 - one_band.ALPHA1))
    scale = np.longdouble(scale)
    rows = []
    pooled_total = np.longdouble(0)
    heldout_totals = np.zeros(chains, dtype=np.longdouble)
    retained_labels = []
    for count in range(13):
        selected_points = cap & (counts == count)
        per_chain_draws = [int(np.sum(selected_points & (chain_index == c)))
                           for c in range(chains)]
        sample_count = sum(per_chain_draws)
        g2_energy = float(scale * np.sum(
            g_ratio[selected_points] ** 2, dtype=np.longdouble) /
                          (chains * draws))
        if count == 0:
            y = np.ones(sample_count, dtype=np.longdouble)
            denominator = Q(1)
        else:
            bound = one_band.SCHEDULE[count - 1]
            denominator = bound - count * one_band.DELTA
            if denominator <= 0:
                raise ArithmeticError("active count has nonpositive slack scale")
            y = ((module.ld(bound) - large_sums[selected_points]) /
                 module.ld(denominator))
        enough = sample_count >= 80 and min(per_chain_draws) >= 5
        if not enough:
            rows.append({
                "count": count, "capped_draws": sample_count,
                "capped_draws_by_chain": per_chain_draws,
                "G2_energy_over_inner_I": g2_energy,
                "screened": False,
                "reason": "fewer than 80 total or five per-chain draws",
            })
            continue
        local_x = x[selected_points]
        values = np.column_stack([
            local_x ** a * y ** d for a, d in COUNT_MONOMIALS])
        q = values / h18_normalized[selected_points, None]
        local_g = g_ratio[selected_points]
        chain_a = []
        chain_b = []
        local_chain = chain_index[selected_points]
        for chain in range(chains):
            take = local_chain == chain
            chain_a.append((q[take].T @ q[take]) / draws)
            chain_b.append((q[take].T @ local_g[take]) / draws)
        chain_a = np.asarray(chain_a, dtype=np.longdouble)
        chain_b = np.asarray(chain_b, dtype=np.longdouble)
        pooled_a = np.mean(chain_a, axis=0, dtype=np.longdouble)
        pooled_b = np.mean(chain_b, axis=0, dtype=np.longdouble)
        kept = greedy_prune(pooled_a, RANK_RELATIVE_CUTOFF)
        reduced_a = pooled_a[np.ix_(kept, kept)]
        reduced_b = pooled_b[kept]
        coefficient, rank, condition, eigenvalues = normalized_solve(
            reduced_a, reduced_b, RANK_RELATIVE_CUTOFF)
        pooled_energy = scale * (reduced_b @ coefficient)
        scores = []
        for hold in range(chains):
            train_a = np.mean(np.delete(
                chain_a[:, kept][:, :, kept], hold, axis=0),
                axis=0, dtype=np.longdouble)
            train_b = np.mean(np.delete(
                chain_b[:, kept], hold, axis=0),
                axis=0, dtype=np.longdouble)
            local_coefficient, *_ = normalized_solve(
                train_a, train_b, RANK_RELATIVE_CUTOFF)
            test_a = chain_a[hold][np.ix_(kept, kept)]
            test_b = chain_b[hold][kept]
            scores.append(scale * (
                2 * (local_coefficient @ test_b) -
                local_coefficient @ test_a @ local_coefficient))
        scores = np.asarray(scores, dtype=np.longdouble)
        score_mean = np.mean(scores, dtype=np.longdouble)
        score_se = np.std(scores, ddof=1) / np.sqrt(chains)
        pooled_total += pooled_energy
        heldout_totals += scores
        labels = [{"count": count, "radial_power_a": COUNT_MONOMIALS[i][0],
                   "cap_slack_power_d": COUNT_MONOMIALS[i][1]}
                  for i in kept]
        retained_labels.extend(labels)
        rows.append({
            "count": count, "capped_draws": sample_count,
            "capped_draws_by_chain": per_chain_draws,
            "G2_energy_over_inner_I": g2_energy,
            "screened": True,
            "candidate_coordinates": len(COUNT_MONOMIALS),
            "retained_coordinates_after_Gram_prune": labels,
            "numerical_rank": rank,
            "normalized_Gram_condition_on_retained_rank": condition,
            "normalized_Gram_eigenvalues": eigenvalues,
            "pooled_projected_energy_over_inner_I": float(pooled_energy),
            "leave_one_chain_out_objective_mean_over_inner_I": float(score_mean),
            "leave_one_chain_out_objective_standard_error": float(score_se),
            "leave_one_chain_out_objective_by_chain": [float(v) for v in scores],
            "slack_denominator": str(denominator),
        })
    heldout_mean = np.mean(heldout_totals, dtype=np.longdouble)
    heldout_se = np.std(heldout_totals, ddof=1) / np.sqrt(chains)
    return {
        "basis": (
            "1_{V,R=r} x^a y^d, x=(sum(t)-alpha1)/(alpha2-alpha1), "
            "y=(B_r-L)/(B_r-r*delta), a=0..4, d=0..1; y=1 for r=0"),
        "candidate_coordinate_count": 13 * len(COUNT_MONOMIALS),
        "candidate_monomials_per_count": [
            {"radial_power_a": a, "cap_slack_power_d": d}
            for a, d in COUNT_MONOMIALS],
        "Gram_prune_relative_cutoff": RANK_RELATIVE_CUTOFF,
        "retained_coordinate_count": len(retained_labels),
        "retained_coordinates": retained_labels,
        "by_count": rows,
        "pooled_projected_energy_over_inner_I": float(pooled_total),
        "leave_one_chain_out_objective_mean_over_inner_I": float(heldout_mean),
        "leave_one_chain_out_objective_standard_error": float(heldout_se),
        "leave_one_chain_out_objective_by_chain": [
            float(v) for v in heldout_totals],
        "screen_scope": (
            "finite-chain rank/prune discovery only; exact stage must rebuild "
            "the selected rational monomials and all Gram/cross entries"),
    }


def instrument(d19):
    state = {}
    original_configure_hybrid = d19.configure_hybrid_engine

    def configure_hybrid(one_band, basis19, vector19, inner_i19):
        bridge, inner_state = original_configure_hybrid(
            one_band, basis19, vector19, inner_i19)
        original_configure = bridge.configure

        def configure(module, geometry):
            original_configure(module, geometry)
            hybrid = module.MarginalD18

            class CapturingHybrid(hybrid):
                def riesz(self, points):
                    values = super().riesz(points)
                    if module.ETA2 == one_band.ETA:
                        state["radial_points"] = np.asarray(
                            points, dtype=np.longdouble).copy()
                        state["target_g_normalized"] = np.asarray(
                            values, dtype=np.longdouble).copy()
                        state["target_marginal"] = self.target
                    elif len(points) > 1000:
                        state["full_points"] = np.asarray(
                            points, dtype=np.longdouble).copy()
                    return values

            module.MarginalD18 = CapturingHybrid
            state["module"] = module
            state["one_band"] = one_band
            state["basis19"] = basis19
            state["vector19"] = vector19

        bridge.configure = configure
        return bridge, inner_state

    d19.configure_hybrid_engine = configure_hybrid
    return state


def projection_from_capture(row, state, chains, draws):
    required = {"full_points", "radial_points", "target_g_normalized",
                "target_marginal", "module", "one_band", "basis19",
                "vector19"}
    if not required <= state.keys():
        raise RuntimeError("D19 bridge did not expose the expected sample closure")
    module = state["module"]
    one_band = state["one_band"]
    flat = state["full_points"]
    radial_points = state["radial_points"]
    if flat.shape != (chains * draws, module.K):
        raise ArithmeticError("captured full-chain shape changed")
    totals = np.sum(flat, axis=1, dtype=np.longdouble)
    radial = totals <= module.ld(one_band.ALPHA2)
    if (int(np.sum(radial)) != len(radial_points) or
            not np.array_equal(flat[radial], radial_points)):
        raise ArithmeticError("captured radial subset lost sample ordering")
    large = radial_points > module.ld(one_band.DELTA)
    counts = np.sum(large, axis=1)
    large_sums = np.sum(np.where(large, radial_points, 0), axis=1,
                        dtype=np.longdouble)
    cap = counts == 0
    for count, bound in enumerate(one_band.SCHEDULE, start=1):
        if bound > count * one_band.DELTA:
            cap |= ((counts == count) &
                    (large_sums <= module.ld(bound)))

    cert, uncapped, _d0, basis18, vector18, _outer18 = module.load_inputs()
    natural18 = module.ResidualD18(
        basis18, vector18, center=module.ALPHA2,
        dilation=module.ALPHA1 / module.ALPHA2)
    natural19 = module.ResidualD18(
        state["basis19"], state["vector19"], center=one_band.ALPHA2,
        dilation=module.ALPHA1 / one_band.ALPHA2)
    h18 = natural18.evaluate(radial_points)
    h19 = natural19.evaluate(radial_points)
    if np.any(h18 == 0):
        raise ArithmeticError("proposal polynomial vanished at retained sample")
    h_ratio = ((h19 / h18) *
               module.ld(natural19.scale / natural18.scale))
    g_ratio = ((state["target_g_normalized"] / h18) *
               module.ld(state["target_marginal"].normalization /
                         natural18.scale))
    a_flat = np.zeros(chains * draws, dtype=np.longdouble)
    b_flat = np.zeros(chains * draws, dtype=np.longdouble)
    g2_flat = np.zeros(chains * draws, dtype=np.longdouble)
    proposal_a_flat = np.zeros(chains * draws, dtype=np.longdouble)
    proposal_b_flat = np.zeros(chains * draws, dtype=np.longdouble)
    a_flat[radial] = h_ratio * h_ratio * cap
    b_flat[radial] = h_ratio * g_ratio * cap
    g2_flat[radial] = g_ratio * g_ratio * cap
    proposal_a_flat[radial] = cap
    proposal_b_flat[radial] = g_ratio * cap
    to_chains = lambda values: values.reshape(draws, chains).T
    scale = float(Q(row["exact_bridge_forms"]["A11_over_A00"]))
    summary = projection_summary(
        to_chains(a_flat), to_chains(b_flat), scale)
    proposal_summary = projection_summary(
        to_chains(proposal_a_flat), to_chains(proposal_b_flat), scale)
    g2_mean, _g2_se, _g2_chains = chain_mean_se(to_chains(g2_flat))
    reconstructed_g2 = scale * g2_mean
    recorded_g2 = row["screen"]["one_band_capped_G_norm_over_inner_I"]
    if abs(reconstructed_g2 - recorded_g2) > 5e-15:
        raise ArithmeticError("captured samples do not reconstruct G^2 screen")
    summary.update({
        "H": (
            "natural dilation of the explicit D19 vector from alpha1 to "
            "9500917/36000000, restricted to the verified one-band cap"),
        "importance_proposal": "frozen natural-D18 h^2 on old full shell",
        "same_retained_points_as_G2_screen": True,
        "captured_radial_draws": int(np.sum(radial)),
        "captured_capped_draws": int(np.sum(cap)),
        "G2_screen_reconstruction_absolute_error": abs(
            reconstructed_g2 - recorded_g2),
    })
    proposal_summary.update({
        "H": "frozen natural-D18 proposal polynomial restricted to V",
        "importance_proposal": "the same frozen natural-D18 h^2 density",
        "same_retained_points_as_G2_screen": True,
        "exact_A_square_orbit_group_count": 10761,
        "exact_b_left_right_description":
            "568-term D19 marginal times natural-D18 outer coordinate",
        "cost_priority_reason": (
            "A uses fewer square groups than natural D19 and its sampled "
            "ratios have no H/proposal division"),
    })
    radial_positions = np.flatnonzero(radial)
    count_projection = count_radial_projection(
        radial_points=radial_points, radial_positions=radial_positions,
        cap=cap, h18_normalized=h18, g_ratio=g_ratio, scale=scale,
        module=module, one_band=one_band, chains=chains, draws=draws)
    return summary, proposal_summary, count_projection


def run(*, seed, chains, burn, draws):
    start = {path: path.read_bytes()
             for path in (FILE, D19_BRIDGE, D19_BRIDGE_TEST)}
    d19 = load("active25_d19_projection_base", D19_BRIDGE,
               D19_BRIDGE_SHA256)
    state = instrument(d19)
    row = d19.run(seed=seed, chains=chains, burn=burn, draws=draws)
    projection, proposal_projection, count_projection = projection_from_capture(
        row, state, chains, draws)
    if any(path.read_bytes() != payload for path, payload in start.items()):
        raise RuntimeError("projection bridge source closure changed during run")
    row["format"] = "active25-d19-truncated-one-band-projection-bridge-v1"
    row["source_sha256"] = sha256(start[FILE])
    row["G2_bridge_source_sha256"] = D19_BRIDGE_SHA256
    row["natural_D19_projection"] = projection
    row["natural_D18_proposal_projection"] = proposal_projection
    row["count_radial_low_degree_projection"] = count_projection
    threshold = row["screen"]["sufficient_threshold"]
    projected = projection["projected_energy_over_inner_I"]
    projected_se = projection[
        "projected_energy_over_inner_I_delta_standard_error"]
    projection["exact_sufficient_threshold"] = row["screen"][
        "exact_sufficient_threshold"]
    projection["projected_minus_threshold"] = projected - threshold
    projection["projected_minus_threshold_in_naive_SE"] = (
        (projected - threshold) / projected_se
        if projected_se > 0 else None)
    projection["conditional_decision"] = (
        "GATED NATURAL-D19 EXACT A,b COMPUTATION WARRANTED"
        if projected - 2 * projected_se > threshold else
        "NATURAL-D19 PROJECTION INCONCLUSIVE")
    proposal_projected = proposal_projection[
        "projected_energy_over_inner_I"]
    proposal_projected_se = proposal_projection[
        "projected_energy_over_inner_I_delta_standard_error"]
    proposal_projection["exact_sufficient_threshold"] = row["screen"][
        "exact_sufficient_threshold"]
    proposal_projection["projected_minus_threshold"] = (
        proposal_projected - threshold)
    proposal_projection["projected_minus_threshold_in_naive_SE"] = (
        (proposal_projected - threshold) / proposal_projected_se
        if proposal_projected_se > 0 else None)
    proposal_projection["conditional_decision"] = (
        "GATED NATURAL-D18 EXACT A,b COMPUTATION WARRANTED"
        if proposal_projected - 2 * proposal_projected_se > threshold else
        "NATURAL-D18 PROJECTION INCONCLUSIVE")
    count_projection["exact_sufficient_threshold"] = row["screen"][
        "exact_sufficient_threshold"]
    count_projection["pooled_minus_threshold"] = count_projection[
        "pooled_projected_energy_over_inner_I"] - threshold
    count_projection["heldout_minus_threshold"] = count_projection[
        "leave_one_chain_out_objective_mean_over_inner_I"] - threshold
    row["source_hashes"][str(D19_BRIDGE.relative_to(REPO))] = \
        D19_BRIDGE_SHA256
    row["source_hashes"][str(D19_BRIDGE_TEST.relative_to(REPO))] = \
        D19_BRIDGE_TEST_SHA256
    row["launch_authorized"] = False
    row["exact_target_started"] = False
    row["resume_supported"] = False
    row["theorem_ready"] = False
    return row


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def publish_exclusive(path, payload):
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def apply_limits():
    import resource
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    new_hard = hard if hard != resource.RLIM_INFINITY else MAX_RSS_BYTES
    resource.setrlimit(resource.RLIMIT_AS,
                       (min(MAX_RSS_BYTES, new_hard), new_hard))
    signal.alarm(MAX_WALL_SECONDS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--chains", type=int, default=8)
    parser.add_argument("--burn", type=int, default=4000)
    parser.add_argument("--draws", type=int, default=6000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    apply_limits()
    row = run(seed=args.seed, chains=args.chains,
              burn=args.burn, draws=args.draws)
    payload = canonical_json(row)
    publish_exclusive(args.output, payload)
    projection = row["natural_D19_projection"]
    print(json.dumps({
        "output_sha256": sha256(payload), "status": row["status"],
        "G2_over_I": row["screen"]["one_band_capped_G_norm_over_inner_I"],
        "A_over_I": projection["A_over_inner_I"],
        "b_over_I": projection["b_over_inner_I"],
        "b2_over_A_I": projection["projected_energy_over_inner_I"],
        "projection_standard_error": projection[
            "projected_energy_over_inner_I_delta_standard_error"],
        "threshold": row["screen"]["sufficient_threshold"],
        "decision": projection["conditional_decision"],
        "D18_proposal_b2_over_A_I": row[
            "natural_D18_proposal_projection"][
                "projected_energy_over_inner_I"],
        "wall_seconds": row["wall_seconds"],
        "peak_rss_kib": row["peak_rss_kib"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
