# Exact-whitened D4 calibration v6.5

Status: repaired prelaunch candidate only. No production authorization,
chain, sampled quotient, D12 screen, or theorem claim follows from this file.

Frozen v6.4 gate SHA `6fac3831...0c8ad` is preserved and permanently
unlaunched. It inspected only the already-squared `point.z`. A nonzero tagged
base marginal of size `2^-607` therefore squared to zero before the guard and
was indistinguishable from exact cancellation.

V6.5 retains every predecessor record, raw-total, local Jensen, and exact
stratum-bound check. At every J envelope point it reconstructs the weighted
base marginal from all returned unit marginals and the exact-whitening tagged
weights before trusting z. A nonzero tagged product that underflows, or a
nonzero weighted marginal whose square is zero/subnormal, fails closed. The
returned z must have identical zero support and agree with the recomputed
square at a tolerance made only from their own ULPs, never from one or from a
stratum envelope bound.

The independent v6.4 `AUDIT FAIL` is pinned verbatim: report SHA
`aea310d56b7aa7e8f63cc14db12e474aad270f7ee9b04869b240351dc8512ceb`,
verifier SHA
`fd3370ae784a04b35f8846512de6db14c456049cb77a1ccd47f447e9eb166714`,
and pre-square regression SHA
`3e387aca92ac30f14dff5f88d5c9de67f17d645e5776fbb0aa55def64890c517`.
The gate remains production-disabled pending another independent hostile pass
and separate root authorization.
