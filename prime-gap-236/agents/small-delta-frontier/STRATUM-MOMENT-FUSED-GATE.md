# Fused fixed-base moment table: frozen benchmark gate

Status: D4 exact calibration passed; the D12 representative-face gate below
was frozen before observing any D12 face timing.  This route is an
implementation experiment, not a sieve certificate.

## Exact fusion

For a fixed branch domain, let
`M[j][lambda](x,y)` be the shifted distinguished-fiber marginal polynomial.
The unfused implementation separately forms

`sum_nu c(lambda,mu;nu) density_nu M[j,lambda] M[k,mu]`

for each `(j,k)`.  The fused implementation instead loops once over each
orbit-key pair `(lambda,mu)`, obtains its orbit-product expansion once, and
carries every allowed `(j,k)` polynomial product in a structure-of-arrays
map indexed by `nu`.  It then visits each nonzero density once and contracts
all resident tags.  Scalar integrations are still separate exact outputs.

For multiplier degree three, the canonical tag inventory has 10 channels,
28 I moments, 10 same-branch distinguished pairs, 16 cross-branch pairs,
115 same-branch scalar tags, and 180 cross-branch scalar tags.  Its canonical
JSON SHA is
`320272a9dfb08ab6d12396127de3ff35ffe35c47b4715e4035bc985e67981aad`.

## Frozen calibration

The source-bound fused D4 run reconstructed all entries rather than reading a
matrix.  Artifact
`results/c10_D4_stratum_moment_table_fused_oracle.json` (SHA
`72ece5aa4a15536153d7634ee630ebf5e1090dc2ce0a7104cf00190bf310f6eb`)
matches all 96 by 96 I and 48J entries and the exact particular-vector
contraction in the frozen independent D4 oracle.  Counts are 312 I faces,
4,680 I scalar moments, 1,200 J branch domains/fused traversals, 8,556
logical products, and 57,788 J scalar moments.  Runtime was 449.480 seconds
and peak RSS 50,108 KiB.  The unfused D4 run took 460.515 seconds, so D2 by
itself shows only a 1.025x end-to-end speedup.

Low-k signed degree-two/three equality and a literal k=1 degree-three oracle
pass under normal Python and `python -O`.

## D12 benchmark and predeclared gate

The worker SHA is
`54d0ade581d4d63636b77daade93f5b2799e87f5c8ba0f98fe251b26107469f1`;
its tests have SHA
`2d846ee34719082633fa120d0515575a40a631fa526bf8818a58a183afa1014d`.
It reconstructs the pinned 714-bit primitive integer scaling and evaluates,
in fresh single-worker processes, I and J faces `(0,0)`, `(7,9)`, and
`(15,0)` in fused and unfused modes.  It serializes every nonzero exact
tag/value pair, the canonical tag inventory, all logical counts, dependency
hashes, phase times, and peak RSS.

The machine-readable frozen gate is
`d12_fused_face_benchmark_gate.json`.  Every following condition is required:

- full D4 exact equality and exact equality of all sampled D12 tables/counts;
- unfused/fused time ratio at central J face `(7,9)` at least 1.25;
- conservative wall projection
  `setup_I + setup_J + 312 max(t_I) + 296 max(t_J)` at most 10,800 seconds;
- measured and projected RSS each below 819,200 KiB.

The memory projection adds storage for at most 16,668 exact values: 448 I
moments, 11,520 J moments, and 4,700 entries in the block-diagonal I and
block-tridiagonal J representation.  Each is charged
`1024 + 2*C` bytes, where `C` is the maximum sampled rational-token length.
This is an engineering projection, not a formal Python allocator bound.

Before either fresh worker starts, shared available memory must be at least
1,844 MiB: the 0.8-GiB benchmark cap plus 1.0 GiB host headroom.  Each worker
reads and enforces this gate from `/proc/meminfo` before taking its dependency
snapshot and records the observed value.  The worker is serial.  A `GO`
verdict would only recommend a later root decision; this
task never launches the full D12 degree-three matrix.
