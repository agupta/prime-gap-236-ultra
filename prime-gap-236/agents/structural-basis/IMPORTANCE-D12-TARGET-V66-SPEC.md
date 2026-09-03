# Unmultiplied D12 transformed target: v6.6 identity draft

Status: identity/baseline dry-run only. No D12 chain, screen, candidate,
fresh scalar traversal, quotient improvement, or theorem claim is authorized.
The target-gate builder deliberately fails while the independent v6.6 audit
artifact map is empty.

The target is the unmultiplied 272-label D12 polynomial with source SHA
`719c656e...d64a87`; its common-scaled integer evaluation copy has SHA
`8650e44c...f4a93`. The negative transferred-quadratic endpoint SHA
`7e9f62fd...4978`, quotient `0.955596...`, is an exclusion regression only.

The dry run constructs the exact rational D4-oracle transform and its 96
transformed constant coefficients. Exact multiplication by `T` returns the
old multiplier vector containing one on each of the 16 tagged constants and
zero on the other 80 entries. Raw D12 stratum masses SHA
`0ac99ee5...d644d`, recovered trust-chain SHA `6411f11d...56a43`, and
grouped baseline SHA `02e1a667...121d9` reconstruct the unmultiplied base
quotient `0.970969847633789574...` within the frozen internal and
cross-traversal tolerances. Factor 48 is applied to J exactly once.

Even after a separately frozen independent v6.6 calibration `AUDIT PASS` is
pinned, the target gate records `screen_launch_authorized=false` and
`identity_dry_run_only=true`. A separate D12 screen driver and separate root
authorization remain mandatory. It must retain all 16 I and 16 J strata,
the four-chain split, unchanged statistical/rank gates, training replicates
0--1, disjoint validation replicates 2--3, and continuation thresholds
`>1.005` for every selected/deleted-chain quotient and `>1.002` for the
simultaneous lower endpoint.

The existing resource estimate is 12,832 CPU seconds and 6,416 wall seconds
with two workers (7,058 seconds with the fixed ten-percent guard), at roughly
43,008 KiB per process. This is only an estimate, not a completed screen.
Any eventual 96-entry transformed candidate must be mapped back exactly to
old coordinates and freshly evaluated with
`agents/exact-integrator/stratum_quadratic_transfer_decimal.py` against the
pinned 272-term integer base.
