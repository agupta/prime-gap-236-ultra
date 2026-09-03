# Unmultiplied D12 transformed target: v6.2 identity gate

Status: identity/baseline dry-run candidate only. No D12 chain, screen,
candidate, fresh scalar traversal, quotient improvement, or theorem claim is
authorized.

The target is the unmultiplied 272-label D12 polynomial with source SHA
`719c656e...d64a87`; its exactly common-scaled integer evaluation copy has SHA
`8650e44c...f4a93`. The negative transferred quadratic endpoint SHA
`7e9f62fd...4978`, quotient `0.955596...`, is pinned only as an exclusion
regression. It is never used as a base or normalizer.

The dry run exactly constructs the rational per-stratum D4-oracle transform
and its 96 transformed constant coefficients. Multiplying by `T` gives, as
exact `Fraction`s, precisely the old multiplier vector with one on each of
the 16 tagged constants and zero on all other 80 entries. The raw D12
per-stratum masses SHA `0ac99ee5...d644d`, recovered trust chain SHA
`6411f11d...56a43`, and grouped baseline SHA `02e1a667...121d9` reproduce
the unmultiplied base quotient `0.970969847633789574...` within the frozen
`1e-98` internal and `1e-50` cross-traversal tolerances. Both normalized
stratum-weight vectors sum to one exactly as rational numbers, with factor 48
applied to J exactly once.

The target gate cannot be generated until it pins a separately frozen
independent v6.2 calibration `AUDIT PASS`. Even then it records
`screen_launch_authorized=false` and `identity_dry_run_only=true`. It keeps
all 16 I and 16 J strata, the 4-chain schedule, unchanged statistical/rank
thresholds, training replicates 0--1, disjoint validation replicates 2--3,
and continuation gates `>1.005` for the candidate and every validation-chain
deletion and `>1.002` for the simultaneous lower endpoint.

The v6.2 D4 driver does not accept a D12 base. A separate D12 screen driver
is still required and is intentionally not named as an executable command in
the gate. The current cost estimate is 12,832 CPU seconds, 6,416 wall seconds
at two workers (7,058 seconds including the fixed ten-percent guard), and
43,008 KiB per process, beneath but close to the 7,200-second predeclared
wall ceiling. This estimate is not a completed run.

Only after a separately audited screen crosses every gate may a 96-entry
exact old-coordinate multiplier be emitted for
`agents/exact-integrator/stratum_quadratic_transfer_decimal.py`, alongside
the pinned 272-term integer base. That fresh grouped Decimal traversal remains
mandatory and nonrigorous until replaced by exact/directed reconstruction.
