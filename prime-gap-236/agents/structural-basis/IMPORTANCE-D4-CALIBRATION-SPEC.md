# Frozen D4 stratified calibration specification

Status: statistical schedule frozen before any conditional chain output.  A
machine-readable gate will additionally pin the final audited source hashes
before launch.  This remains discovery validation, not a rigorous error bound.
The replacement v5 gate lists every superseded prelaunch artifact by its
complete SHA-256 value, including the v3 checkpoint and v4 final-result
ancestor-symlink counterexamples; neither an older gate nor this v5 prelaunch
gate is a production authorization.

Initial production is fresh-only.  Its separate root authorization binds the
canonical path and device/inode identity of one record directory.  Before the
first stochastic step, all 128 scheduled checkpoint names must be absent.
Each checkpoint is then created with `O_CREAT|O_EXCL`; interruption requires a
newly authorized directory and a complete rerun, never an unauthenticated
resume.  The producer holds the authorized directory itself open with
`O_DIRECTORY|O_NOFOLLOW` and performs every absence check, exclusive create,
and checkpoint reopen relative to that descriptor.  It never reconstructs a
checkpoint from the raw CLI path after validation, and rebinds both the held
inode and canonical pathname.  The root and optimized-Python production runs
use distinct fresh authorized directories and their numerical record payloads
are compared.

## Chain schedule

Both I and common-J use all 16 C10 strata.  Each `(target,stratum)` has four
independent chains, for 128 chains total.  Seeds are a fixed injective function
of target, stratum, and replicate recorded by the driver.  Every chain uses:

```text
slack-move probability       1/2
tempering powers             0, 1/4, 1/2, 3/4, 1
steps at each power          250
power-one burn-in steps      1000
retained samples             4000
proposal steps per sample    2
batches per chain            20
samples per batch            200
```

Every initial point is generated independently in the interior of its named
stratum.  Failure to initialize a positive-weight stratum, a nonfinite target,
or a state escaping its fixed stratum aborts the run.  Physical--physical and
physical--slack acceptance and support rejection are recorded separately for
each chain and stage.  Each move type must have positive acceptance in every
chain and at least 1 percent aggregate acceptance within every target-stratum.

Power zero is uniform only on the positive-density interior; a numerically
represented zero-density proposal is rejected.  This differs only on a null
set mathematically and prevents a tempering stage from handing `-inf` to the
next positive power.

## Matrix reconstruction

I samples use the six normalized tagged features
`(L/alpha)^a (Z/alpha)^b` in their fixed stratum, where `L` is the sum of
coordinates above `delta` and `Z` is the sum of the remaining coordinates.  J
samples use `g=sum m_i^2`, the unit marginal vector `m/sqrt(g)`, and
`z=m_*^2/g`; direct `m_i/m_*` ratios are forbidden.  Per common stratum the
matrix contribution is the joint ratio of means `E[y_ij]/E[z]`, then is
weighted by the byte-pinned `J_r/J_*`.  The D4 producer convention is fixed as
`j_scale_to_numerator=1`; the D12 convention will be separately fixed as 48.

The calibration must cover exactly 336 structural upper-triangle I entries
and 876 structural upper-triangle J entries.  Every nonstructural entry must be
identically zero before matrix assembly.  The sum of all constant-coordinate
entries must reconstruct one in each normalized expectation matrix within its
simultaneous band.

## Diagnostics and acceptance

The simultaneous entry multiplier is 6.  Standard errors come from the 20
within-chain batch means, with the joint numerator/denominator delta residual
on J.  Every record also retains per-batch second means; their aggregate must
reconstruct the raw second sums and satisfy the pointwise bounds and Jensen
inequalities.  This is an internal corruption check, not authentication of a
preexisting checkpoint: such checkpoints are categorically rejected in
initial production.  An exact nonzero entry with empirical zero standard error fails closed,
apart from the following exhaustive pointwise identities: the tagged I
constant diagonal is identically one within each of the 16 fixed strata, and
at common J stratum 15 the local tagged-constant ratio is identically one.
For the latter, the large distinguished branch is exactly absent because
`16*delta > beta(16)`, while the small branch is present; hence only
`m_(15,0,0)` contributes to `m0` and `y_00=z` pointwise.  Exact interior
witnesses must verify that both branches are present for common strata 0--14,
that only this large branch is absent at 15, and that every whitelisted oracle
mass is nonzero.  This is a local conditional whitelist only: the aggregate
global J entry `(90,90)` still includes the independently sampled common-r=14
contribution and is not exempt from its global zero-standard-error gate.  All
other local entries, including neighboring `(0,1)` at common r=15, retain the
fail-closed rule.  All exact D4 oracle entries must lie in their simultaneous
bands.

For every nonconstant retained conditional moment:

```text
maximum split-R-hat          1.05
minimum batch-means ESS      200
```

For every J stratum, the mean of `z` must have a positive six-standard-error
lower endpoint and relative standard error at most 2 percent.  The driver
reports the minimum `E[z]`, even when its stratum weight is tiny.

The exact oracle, not the noisy matrix, selects active coordinates: dimensions
are 16 at degree zero, 47 at affine degree, and 93 at quadratic degree.
Positive rare-stratum coordinates are diagonally equilibrated and may not be
dropped by a global rank tolerance.  The realized equilibrated denominator
must have full active rank and no materially negative eigenvalue.

For each of the three degrees, compute the estimated root and the exact-oracle
root.  Delete every chain once only from its own stratum, restoring the fixed
stratum weight from the remaining three chains.  The exact root must lie in a
six-jackknife-standard-error interval around the full estimate, and the full
relative root discrepancy must be at most 0.5 percent.  Raw matrix
antisymmetry is recorded before symmetrization; an implementation based on a
single sample outer product should give bitwise zero.

## Predeclared extension rule

There is one permitted extension, fixed before output.  If and only if all
schema, support, finiteness, exact-null, acceptance, denominator-rank, and
factor-48 gates pass, and the only failures are R-hat, ESS, `z` precision, or
statistical coverage with maximum standardized oracle discrepancy at most 12,
the same chains may append 12,000 samples each by continuing their serialized
PRNG states.  The combined schedule then has 16,000 samples per chain and 80
equal batches.  Any algebraic failure, missing stratum, standardized
discrepancy above 12, or unstable root retires this implementation instead of
authorizing post-hoc tuning.

Extension authorization binds the exact parent-result SHA and a fresh
extension-record directory identity.  Initial checkpoints may be loaded only
at the path, SHA, device, and inode listed in that parent result; every one of
the 128 extension checkpoint names must be absent and is created exclusively.
Every final result records a positive finite wall time and positive integer
peak RSS in KiB, in addition to its complete gate, authorization, parent, and
checkpoint byte/inode closure.
Final preflight, smoke, production, and extension results use the same rule as
checkpoints: the canonical output parent is held open and the leaf is created
and rechecked only with dirfd-relative operations.  A mutable ancestor alias
cannot redirect the published result after collision and provenance checks.

No D12 chain and no fresh exact scalar recurrence is authorized until this D4
gate passes in full.  A later D12 candidate must additionally retain the
previous `q>1.005` leave-one-chain and lower-endpoint `>1.002` launch gates.
