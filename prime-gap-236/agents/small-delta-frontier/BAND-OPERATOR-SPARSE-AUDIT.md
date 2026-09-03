# Hostile audit of the 20-band sparse gradient route

Date: 2026-09-02 (Europe/Berlin)

## Verdict

**SCOPED ALGEBRA AUDIT PASS; PRODUCER PROVENANCE COUNTEREXAMPLE; NO
QUOTIENT CLAIM.**

At the frozen arithmetic SHAs below, the sparse channel algebra agrees exactly
with independently rebuilt low-dimensional `Fraction` matrices, including
signed coefficients, repeated and distinct channel owners, the factor `k`,
and serial/fork aggregation.  A target-parameter constant-polynomial oracle
also gives exactly `N=48J`, 312 `I` faces, 1,200 `J` branch intersections, and
16 `r` buckets.

This is not an unqualified pass for the producer executable.  The smallest
explicit failure is a path/provenance counterexample: the program computes all
end hashes at lines 451--455 of `band_operator_sparse.py`, but writes
`args.output` only at line 568 and never rejects an output path equal to the
operator, a dependency, the source, the bands, or the baseline.  Thus, for
example,

```text
--output agents/structural-basis/code/band_operator_sparse.py
```

can leave every serialized gate true and then overwrite the very producer
whose pre-write hash was checked.  The same construction works with the
source, bands, or baseline.  The producer also does not snapshot the source or
bands at the end of the run.  No destructive counterexample was executed; the
ordering and missing collision gate are fixed as a permanent static
regression.

The actual active invocation does **not** trigger this defect.  Its five paths

```text
agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json
agents/structural-basis/results/c10_D12_degree_bands.json
agents/exact-integrator/results/c10_capped_fullD12_vector_grouped_mp100.json
agents/structural-basis/code/band_operator_sparse.py
agents/structural-basis/results/c10_D12_band_sparse_gradient_mp100.json
```

resolve pairwise distinctly.  At this audit checkpoint the output did not yet
exist.  This only clears the alias counterexample for this invocation; the
eventual output still requires the consumer below.

## Frozen identity

| object | SHA-256 |
|---|---|
| sparse producer | `e1545435f0c7ad22a17115ac46c291436c1ead5101fd3de6d2a80ab65bc9c257` |
| dense jet / `BandMap` dependency | `e4fbf7a97d061d362c32b54bf0d49a89c4195b965e96d7ab89a2581bc907c073` |
| grouped scalar evaluator | `47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a` |
| exact integrator | `941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52` |
| 272-term source | `719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87` |
| 20-band map | `29d38a9e7ca7a352560c0a01813f2dfd2f477ec8cb829c433cce18d8229d31e9` |
| scalar capped baseline | `02e1a6676a68380592fd272845f7714d583574bd74f73b9a96727171751281d9` |
| fail-closed postprocessor | `dbd0d47f4c3796f6f09cbfed649d86fc884a21db1c6c6c8aec287bc894176bc7` |
| hostile tests | `bbe1b56dbe4931fd15e046aae3144d7ee6143d851c68f44d20edd22d3de578a4` |

The source is exactly the complete ordered no-ones basis

```text
(a,lambda),  a+|lambda| <= 12, all positive parts of lambda >= 2,
```

with 272 distinct labels and no zero source coefficient.  The band file
reconstructs all 272 coefficients over `Fraction`, in the same order.  Owners
0--11 are the individual degree-at-most-four labels.  Owners 12--19 contain
exactly

```text
7, 11, 15, 22, 30, 42, 56, 77
```

labels of total degrees 5 through 12.  The source/band validation in
`band_gradient_postprocess.py` lines 176--267 reconstructs these facts rather
than trusting serialized dimensions.

## Algebra checked from definitions

Write `o(p)` and `w_p` for the stored owner and rational weight, and

```text
c_p(theta) = w_p theta[o(p)].
```

The producer constructs this map at lines 57--70.

### `I` channels

For an unordered expanded-label pair `(p,q)`, the coefficient of its orbit
product is

```text
p=q:  c_p^2,
p!=q: 2 c_p c_q.
```

Its nonzero derivatives are therefore

```text
p=q:                 2 c_p w_p                         in owner o(p),
p!=q, same owner:    2(w_p c_q + c_p w_q),
p!=q, distinct:      2 w_p c_q in o(p), 2 c_p w_q in o(q).
```

These are exactly lines 86--96.  Lines 97--117 multiply them by the same
integer orbit multiplicities and residual expansion

```text
binom(a+b,c) (1-alpha)^(a+b-c)
```

as the scalar evaluator.  Lines 120--130 compute each geometry moment once and
contract every channel against it.  Fresh exact matrices verify

```text
I(theta)          = theta^T A theta,
gradient I(theta) = 2 A theta
```

coordinate by coordinate for a six-label signed example in which three labels
share one owner and two share a second owner.

### `J` channels and branch ownership

Distinguished-variable splitting is linear, so the owner derivative of a
marginal is obtained by replacing `c_p` by `w_p`.  Lines 196--208 do exactly
this.  On the actual 272-label input the scalar dictionary has 695 components,
and the hostile test verifies coefficientwise

```text
M(theta) = sum_o theta_o M_o
```

over every one of them.

Let `B(L,R)` denote the symmetric orbit contraction of two branch marginals.
The scalar evaluator uses `B(M,M)` for one branch and `2B(L,R)` for two
different unordered branches.  Hence

```text
d B(M,M)   = 2 B(M,dM),
d 2B(L,R) = 2B(dL,R) + 2B(L,dR).
```

Lines 244--264 implement precisely these formulas.  The branch list, the two
zero-measure complementary-pair exclusions, domain intersections, densities,
and integration are unchanged at lines 266--347.  Exact comparison with the
separate canonical-moment matrix recurrence detects either a missing or extra
branch factor two.

### Factor 48

The `J` traversal returns one distinguished-coordinate value.  Lines 381--390
multiply both its value and every derivative by `support.k`.  A fresh
target-support test with `k=48` and a nonunit coefficient proves exactly

```text
numerator = coefficient^2 * M2[0,0]
          = 48 * sum_r J_r,
```

where the independently constructed `M2` is defined as `k*basis_j`.  This is
an exact `Fraction` equality, not a Decimal tolerance check.

### Counts and fork aggregation

For C10, `max_large()` is 15 because `r/100 < 97/625` exactly through
`r=15`.  Thus both traversals have buckets `r=0,...,15`.  Since
`floor(alpha/delta)=26`, the `I` face count is

```text
sum_(r=0)^15 (26-r+1) = 312.
```

An independent constant-polynomial geometry traversal gives 1,200 active
unordered branch intersections for `J`.  The complete D12 no-ones product
orbit list is the set of no-ones partitions of degrees 0 through 24, whose
independently enumerated cardinality is 1,575.  These explain all target count
fingerprints without copying them from the active process.

Lines 175--194 and 349--373 use `fork`, `Pool.map`, and ordered parent-side
summation.  The hostile signed test compares all value and derivative channels,
all per-`r` channel dictionaries, and all counts between one and two workers
exactly.  The actual invocation uses two workers.  Concurrent threaded calls
inside one Python process were not audited and are outside the CLI's use.

## What one completed gradient can and cannot imply

Even an *exact* output at a single nonzero `theta` would supply only

```text
D=theta^T A theta,  N=theta^T B theta,
A theta,            B theta.
```

It does not determine either quadratic form away from `theta`.  Explicitly,
choose nonzero `v` with `v^T theta=0`.  Replacing

```text
A by A+s vv^T,   B by B+t vv^T
```

leaves all four displayed quantities and both Euler identities unchanged but
changes the quotient at every `theta+lambda v`, `lambda != 0`.  The exact
two-dimensional counterexample is a permanent unit test.

Consequently one gradient output cannot establish any of the following:

- the quotient of a finite perturbation;
- the maximum quotient in the 20-dimensional band space;
- positive or negative definiteness of either form;
- optimality from a small residual;
- a certified ascent direction, because the present channels are unbounded
  Decimal approximations rather than outward intervals.

It may rank *discovery* directions.  To evaluate even a one-dimensional line,
the missing self-forms `d^T A d` and `d^T B d` must be reconstructed.  A final
polynomial must then undergo an independent exact or outward-interval scalar
evaluation.

Matching the scalar baseline and Euler identities is useful but not a gradient
certificate: any error vector orthogonal to `theta` preserves the Euler test,
and traversal counts do not check the values assigned to those channels.

## Fail-closed postprocessor

`agents/small-delta-frontier/band_gradient_postprocess.py` is separate from the
running producer.  It:

1. requires a caller-supplied byte SHA for the completed gradient;
2. strictly rejects duplicate JSON keys, nonfinite tokens, missing or extra
   fields, wrong dimensions, hashes, parameters, counts, factor-48 bucket sum,
   gradient halves, Euler reconstruction, or baseline forms;
3. reconstructs the complete ordered source and every band owner/weight;
4. rejects output collision with any input, dependency, or itself (lines
   464--489), refuses overwrite, and rechecks all bytes immediately before
   writing (lines 552--556);
5. forms only the Decimal discovery residual `r=B theta-q A theta`;
6. when its relative signal passes the stated nonrigorous gate, emits the exact
   rational relative-sign direction

   ```text
   d_i = sign(r_i) |theta_i|
   ```

   and the explicit trial `theta+(1/4096)d`, expanded to all 272 exact rational
   coefficients;
7. otherwise emits `no-claim-band-gradient-postprocess`;
8. always writes `rigorous=false`, `theorem_ready=false`,
   `proves_improvement=false`, and states that a fresh scalar reevaluation is
   mandatory.

Thus the consumer cannot promote the active output into a numerical quotient.
The step `1/4096` is a deterministic discovery proposal, not a line-search
result and not asserted to improve the quotient.

After the real output completes, invoke it as follows, substituting the
independently printed SHA literally:

```bash
sha256sum \
  prime-gap-236/agents/structural-basis/results/c10_D12_band_sparse_gradient_mp100.json

python3 prime-gap-236/agents/small-delta-frontier/band_gradient_postprocess.py \
  --gradient prime-gap-236/agents/structural-basis/results/c10_D12_band_sparse_gradient_mp100.json \
  --gradient-sha256 '<64 lowercase hex characters from sha256sum>' \
  --source prime-gap-236/agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json \
  --bands prime-gap-236/agents/structural-basis/results/c10_D12_degree_bands.json \
  --output prime-gap-236/agents/structural-basis/results/c10_D12_band_rational_trial.json
```

The output path must not already exist.

## Test commands and scope

```bash
python3 -m unittest \
  prime-gap-236/agents/small-delta-frontier/test_band_gradient_audit.py -v
python3 -O -m unittest \
  prime-gap-236/agents/small-delta-frontier/test_band_gradient_audit.py -v
```

Both modes pass 8/8 tests.  Peak test runtime is about four seconds and no D12
integration is launched.  The target constant-oracle path peaks near 21 MiB in
a standalone timing; the remaining tests are similarly light.

This report audits the frozen code and input identity before completion of the
active target run.  It is **not** an audit of an as-yet-absent gradient artifact
and supplies no evidence that the 20-band space crosses one.
