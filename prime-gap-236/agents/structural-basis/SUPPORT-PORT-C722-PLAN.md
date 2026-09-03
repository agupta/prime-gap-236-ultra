# Support-port pivot: C722 with a reusable fixed-vector kernel

Status: predeclared discovery plan only.  No target traversal is authorized by
this document.

## Claim under test

The selected C10 six-core cross space gains only `4.6206068e-6`, while a
separate analytically audited small-delta support is substantially better in
low-degree reoptimized spaces.  The materially different question is whether
the exact 272-term full-simplex D12 vector, without changing its coefficients,
retains enough mass on that support to make a support-specific reoptimization
worth its much larger cost.

The first target is the count-scheduled C722 point

```text
k       = 48
delta   = 361/50000
A       = 3121/12000
epsilon = 1/250
alpha   = A+epsilon = 3169/12000
eta     = A-epsilon = 3073/12000
```

with the 28-entry, then constant, cap schedule in
`agents/exact-integrator/results/c722_prefix_beta_schedule.json`, file SHA-256
`33baffcd08b5262cf75a2767bf49da198a29cd31ee8bc7c49dafae65a1e59e2a` and
canonical schedule SHA-256
`8c67d65544a8f6036bae6f868eb937cabe963eaec12ec59e3a9fb537a9695f17`.
The fixed vector is
`agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json`, SHA-256
`719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87`.

The combined exact analytic/schedule preflight
`agents/small-delta-frontier/verify_c722_all.py`, SHA-256
`4fef5565cb3e0755169801646099e568b2c35896db749139b636980ecb60d701`,
was rerun successfully on 2026-09-02 and must rerun successfully again before
any numerical target job.  Its present audit has active counts `0..24`, first-empty
margin `1/100000`, 625 ordered cap pairs in each of seven branches, and worst
strict IIc reserve `56499669613/285000000000000`.

## Reusable kernel rather than repeated product reconstruction

Before a target evaluation, compile a strict, source-bound fixed-vector kernel
whose entries do not contain any support parameter:

1. the monomial-orbit products needed by the 272 labels;
2. the exact I square kernel before translating slack from `1-sum(t)` to
   `alpha-sum(t)`, indexed by `(remaining orbit,total slack degree)`;
3. the exact distinguished-coordinate marginal components indexed by
   `(remaining orbit,distinguished exponent,slack degree)`;
4. the integer selected-exponent splits and orbit sizes used by every face.

At replay, `alpha`, `delta`, `eta`, and the relevant cap entries are inserted
only into the residual translation, density shifts, marginal endpoint
polynomials, and polygon/interval moments.  Thus one cache can drive C10,
constant-C722, scheduled-C722, or nearby audited rational points.  Geometry
moments remain point-specific and bounded face caches are still cleared after
each face; no serialized numerical moment is trusted.  The cache loader must
rebuild and hash-check the source vector and all integer orbit products rather
than trusting a matrix dump.

Required prelaunch tests are:

- exact equality with the existing direct evaluator on signed `k=1,2,3`
  examples, including the zero-dimensional marginal convention;
- exact C10 and C722 D4 equality in both face orders;
- Decimal serial/two-worker equality and a support mutation that changes the
  answer while leaving the kernel bytes fixed;
- strict duplicate-key/schema/path-alias/dependency-hash rejection;
- normal and `python -O` runs with identical verdicts.

A first in-memory prototype now implements exactly this algebra split at
`agents/structural-basis/code/fixed_vector_support_kernel.py`, SHA-256
`774b8f3a09d77d79d6e4abe56cce4ed1eb82fc5f71ca08cb033bd383091073a3`.
Its test file SHA-256
`7662e0e8cb96998a7a9bd9552e63e4f2422c4b47fe56c76b96e9b788bcd87e59`
passes 5/5 in normal and optimized mode, including signed `k=1` zero-dimensional
J, two distinct constant supports, an explicit nonconstant schedule, and
serial/two-worker equality.  This is a feasibility prototype only: it has not
compiled the D12 target, serialized a production kernel, or passed an
independent target-output audit.  The exact-integrator report
`agents/exact-integrator/FIXED-VECTOR-SUPPORT-KERNEL-AUDIT.md`, SHA-256
`94105250a76d6ed5f3144d2d0299aa6794f66321ab32ffb3473e46be6179938c`,
gives `SCOPED AUDIT PASS` for the formulas and all ten test invocations.  It also
confirms the important cost limitation: the cache saves fixed coefficient
contractions and retains orbit tables, but support-dependent marginal
polynomials, branch products, face densities, domains, and integrations still
dominate and are rebuilt.  Treat it as reusable in-process scan plumbing, not
as evidence for a large target speedup or as certificate infrastructure.

This cache is feasible because all orbit multiplication and coefficient
contraction are support-independent.  It will not eliminate the dominant
support-specific polygon integrations, so the cost gate below remains based on
measured face/domain work rather than claiming an unmeasured speedup.

## Cost model and resource gate

The comparable 272-label C10 scalar run used 312 I faces and 1,200 J branch
domains, with measured times 1,773.913s and 4,918.617s.  C722 schedule geometry
has 625 I faces and 2,468 J domains.  Linear count scaling predicts

```text
I: 1773.913 * 625/312  = 3553.512 s
J: 4918.617 * 2468/1200 = 10115.956 s
total                    = 13669.467 s = 3.80 h
```

This is an estimate, not a benchmark.  The previous bounded-cache 272-label
run used about 319 MiB per largest child; require two stable
`MemAvailable >= 2.2 GiB` readings, no rising swap, no other new heavy job, two
workers at most, fresh absent output/stage paths, and a progress log.  Add a
resume-safe I stage to the scheduled evaluator before launch.

## Predeclared falsification and continuation gates

Let `q_722` be the fresh Decimal100 scalar quotient.  It is discovery data.

- If `q_722 <= 0.975`, retire direct fixed-vector support transfer.  Do not run
  a C722 coefficient-action traversal.
- If `0.975 < q_722 < 0.985`, retain the support family but require a new cheap
  residual/cost argument before any multi-hour coefficient action; do not infer
  the C10 residual transports to C722.
- If `q_722 >= 0.985`, a support-specific sparse coefficient action may be
  proposed under a separate resource gate.  Its own candidate still requires
  a fresh scalar evaluation.
- If the scalar display exceeds one, do not claim a theorem: rationalize only
  after a second-precision replay, then reconstruct the forms exactly or with
  outward intervals and redo the analytic audit against the frozen support.

The thresholds are cost-control heuristics, not upper bounds.  A failed
fixed-vector transfer does not rule out reoptimized C722 bases.
