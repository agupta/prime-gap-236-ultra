# Hostile reaudit: conditional importance statistics

Verdict: **SCOPED AUDIT PASS** for the byte-pinned discovery helpers below.
This is not a pass for a stochastic D4 calibration, an error bar, a D12
candidate, or a sieve certificate.

## Frozen bytes

| artifact | SHA-256 |
|---|---|
| `importance_statistics.py` | `dd7a919b23f1eedc7cbb1093612c0dabfbcce2a5f7d30407503e2cc963686d26` |
| `importance_conditional.py` | `6e502c09354eb0fedf82c90d9d5ba12d7313609dc4392c0c947ca1166bad0258` |
| producer statistics tests | `604c7d5b0ed89d2792732912e80db97a23530e288ed5659942ac15e7bca3ecb1` |
| producer conditional tests | `b379fe6c2f2a29173dfae0ea8986b70eab79e9206c56a37b1c62445fe10f8adb` |
| `importance_sampler.py` | `54c936221fff3c2f981b98fee4110abfc384cf9b3e65d759b3997ff27c9812e4` |
| `importance_envelope.py` | `7c28633e89987c6d2d3493d4f05e699914b5fb7a023d31ccb458878587bc7110` |
| `importance_point_eval.py` | `ea88f6d29b744f59ad146bdebf9b2003a2d57e40eea5b7a03fb48f2309cdfc01` |
| `importance_density.py` | `d656c788b3cbedf6029a95e74ac5a1cc9e8b6e3794ea9ca3d624af460ced9380` |
| exact D4 parameter artifact | `fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86` |
| D4 fixed-vector input | `2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b` |

The independent executable audit is
`agents/small-delta-frontier/audit_importance_conditional_statistics.py`, SHA
`db4162a1f14803b18eacda24b0504b04de252c37b763ed6a543d2ce43c464b6e`.
It prints `AUDIT PASS` under both ordinary Python and `python -O`.

## Formula checks

1. `split_rhat` uses axes `(chain,batch,feature...)`, splits every chain into
   its first and second half, and concatenates halves along the chain axis
   (`importance_statistics.py:22-44`).  A hand-computed two-chain shifted
   fixture reproduces the exact within/between factors.  It requires two
   chains and an even four-or-more batch count.  An overflowed finite fixture
   produces `inf`, never a false finite or `NaN` convergence value.
2. The ESS formula is
   `N*raw_variance/(batch_size*variance(batch_mean))`
   (`importance_statistics.py:47-92`).  A literal size-two-batch example gives
   exactly `12.6`.  The current code requires at least `2 x 4` batch means,
   checks raw and batched means, checks both `E[X^2]>=E[X]^2` and the stronger
   batch Jensen lower bound
   `E[X^2]>=mean_b(E[X|batch=b]^2)`, rejects nonfinite/underflowed variances,
   and grants full ESS only to the represented constant case.
3. The J ratio uses the joint residual
   `Y_b-ratio*Z_b`, so numerator/denominator covariance is retained.  Its
   sample deviation divided by `mean(Z)*sqrt(number_of_batches)` exactly
   matches an independent array calculation (`importance_statistics.py:95-138`).
   Every batch is checked against the envelope identities: `Z in [0,2]`,
   exact matrix symmetry, diagonal in `[0,1]`, and off-diagonal magnitude at
   most `1/2`.  Nonpositive mean denominator and every nonfinite output fail.
4. Diagonal equilibration of the generalized pencil is algebraically correct:
   for `D=diag(A_ii^-1/2)` the code whitens `DAD`, solves against `DBD`, and
   maps the vector back by `D` (`importance_statistics.py:141-231`).  A
   positive `1e-30` rare-stratum coordinate survives and yields its root 2.
   A supplied inactive coordinate is accepted only when its complete raw A
   and B rows and columns are exactly zero, before symmetrization; omitting a
   nonzero `B`-only direction now raises.

## Fixed-stratum geometry and power zero

For the pinned C10 support all active strata are exactly `0,...,15`.  The
initializer (`importance_conditional.py:51-109`) was checked for both the
48-dimensional I target and 47-dimensional J-envelope target in every
stratum.  Every generated point had:

- the named number of coordinates strictly above `delta`;
- every remaining coordinate strictly below `delta`;
- strict total-simplex and large-sum cap reserve; and
- finite positive target log density.

The construction is sound for C10.  If there are `s` small coordinates,
their total is below `0.28*s*delta` and their weights have ratio at most
`5/3`, hence every one is below `(7/15)delta`.  Large coordinates equal
`delta` plus a positive share of an interior large-total excess.

The fixed-stratum support is checked before and after every proposal.  The
physical--physical and physical--slack selection probabilities are state
independent, and uniform redistribution of the unchanged pair total has the
same density in both directions.  Restricting it to one stratum therefore
preserves symmetry.

The repaired power-zero wrapper (`importance_conditional.py:124-155`) agrees
with the frozen schedule at `IMPORTANCE-D4-CALIBRATION-SPEC.md:31-34`:
the current state must have finite target density, every geometrically valid
finite-density proposal is accepted, and a represented `-inf` candidate is
rejected.  The independent audit forces both finite-to-finite acceptance and
finite-to-`-inf` rejection, then runs actual C10 I and J power-zero chains in
strata 0, 7, and 15.  They retain finite density and fixed R while exercising
both move types.

## Repaired hostile counterexamples

This report supersedes the earlier no-pass snapshot for statistics SHA
`79d670...` and conditional SHA `9862307...`.  The following smallest failures
are now permanent producer and independent regressions:

1. `active_indices=[0]` on `A=diag(1,1), B=diag(1,100)` formerly hid the true
   second direction.  The nonzero inactive row now rejects.
2. One batch formerly returned ESS `NaN`; a materially negative raw variance
   could be clipped into false full ESS.  Minimum batch counts and consistency
   gates now reject both.
3. Alternating batch means `+/- 1e-3` with serialized raw second moment zero
   formerly passed the weaker moment test.  The batch Jensen gate now rejects.
4. Negative `z`, impossible/non-symmetric envelope numerator batches, and a
   tiny denominator producing `inf/NaN` formerly escaped.  Pointwise bounds,
   symmetry, and finite-output gates now reject.
5. Conditional power zero formerly accepted a supported candidate whose log
   target was `-inf`, contradicting the frozen positive-density-interior
   schedule.  The wrapper now treats it as a rejected proposal.

## Exact limitations of this pass

- These are floating-point, batch-CLT discovery diagnostics.  Their bands are
  not rigorous confidence intervals and never enter a theorem checker.
- The helper does not know the byte-pinned exact-null manifest.  Its caller
  must bind the exact degree-specific active lists (16, 47, and 93 in D4), and
  the helper then checks the omitted realized rows.  A solver return by itself
  is not an active-space provenance proof.
- The solver records raw antisymmetry but intentionally symmetrizes afterward.
  The calibration consumer must apply the predeclared antisymmetry gate.
- `simultaneous_coverage` accepts a caller-supplied Boolean mask.  The
  calibration consumer must bind the 336 I and 876 J structural entries and
  reject an empty or incomplete mask.
- `ratio_matrix_delta` is an algebraic batch helper and accepts any two or
  more batches.  The frozen calibration consumer, not this function, must
  enforce four chains, 20 batches per chain, the positive six-SE `z` lower
  endpoint, and the 2% relative-SE limit.
- The initializer proof above is C10-specific.  It is not a generic theorem
  for a schedule with a discontinuously larger `beta(r+1)` branch.

No stochastic chain was launched by this audit, and no quotient or theorem is
claimed.

## Reproduction

```bash
python3 agents/small-delta-frontier/audit_importance_conditional_statistics.py
python3 -O agents/small-delta-frontier/audit_importance_conditional_statistics.py
PYTHONPATH=agents/structural-basis/code \
  python3 agents/structural-basis/tests/test_importance_statistics.py
PYTHONPATH=agents/structural-basis/code \
  python3 agents/structural-basis/tests/test_importance_conditional.py
```
