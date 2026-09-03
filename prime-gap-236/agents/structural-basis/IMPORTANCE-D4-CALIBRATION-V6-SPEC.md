# Exact-whitened D4 stratified calibration v6

Status: implementation candidate only.  Production remains unauthorized until
the frozen code, gate, tests, transform, and fresh directory bindings receive
an independent hostile audit and a separate root authorization.

The gate also byte-pins the audited v5 gate it supersedes, the read-only v5
rank postmortem and its tests, every inherited v5 dependency, this v6 builder,
driver, transform, envelope, tests, and the three exact D4 data artifacts.

V6 preserves the complete v5 schedule, conditional-stratum geometry,
four-chain batching, acceptance gates, simultaneous six-standard-error bands,
R-hat/ESS/z gates, 128 leave-one-chain deletions, extension rule, O_EXCL
fresh-only checkpoints, held-directory publication, and the unchanged
relative denominator rank threshold `1/1000000000000`.

The only mathematical coordinate change is fixed before sampling.  Within
each stratum, order the exact-active normalized multiplier features by total
degree and compute the exact rational factorization

```text
A_r = L_r D_r L_r^T,
T_r = L_r^{-T} S_r,
1 <= (S_r)_ii^2 (D_r)_ii < 4,
```

where every diagonal entry of `S_r` is an exact signed-free power of two.  At
stratum zero the exact-active channels are `(1,Z,Z^2)`; at strata 1 through 15
all six channels are active.  Thus all 93 active coordinates and the nested
16/47/93 degree filtration are retained.  The full transform SHA-256 is
`f2a0e8325809956c6883191d04cde6bc67ea74c4af34f86dce7a1ac60c4ac1fb`.

Every retained I point evaluates `T^T phi(x)` directly.  Every retained common
J point evaluates `T^T m(u)` directly and samples from the new envelope
`g=sum_i (T^T m)_i^2`; transforming an already aggregated v5 matrix is
forbidden.  Exact weights `w=T^{-1}c_0`, supported on the 16 transformed tagged
constants, reconstruct the physical base multiplier and marginal.  Hence
`z=(w^T T^T m)^2/g`; its pointwise Cauchy bound is the sum of the at-most-two
active constant weights squared and remains below 2.  The exact transformed
oracle is reconstructed by rational congruence, and both normalized base forms
must equal one under `w` exactly.

Whitened I features are signed and can be large on rare strata.  Their
serialized batch means, batch second moments, raw sums, and raw second sums
are checked directly against exact transform-derived absolute bounds and
against both raw- and batch-level Jensen inequalities before the legacy v5
schema/seed/acceptance validator is applied.  The compatibility affine map
used for that legacy validator is never trusted to authenticate the original
signed moments.

No D12 screen follows from a failed or extension-eligible v6 run.  A D12
transformed-multiplier screen requires a separately authorized v6 calibration
pass, a leave-one-chain quotient strictly greater than `1.005`, and a lower
endpoint strictly greater than `1.002`.  Neither calibration nor screen is an
exact sieve certificate.
