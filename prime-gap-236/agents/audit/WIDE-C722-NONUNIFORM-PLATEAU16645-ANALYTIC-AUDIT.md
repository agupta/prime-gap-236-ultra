# Wide C722 nonuniform plateau-0.16645 analytic audit

## Verdict

`AUDIT PASS` for the analytic Proposition-1 hypotheses only.  The exact
outer schedule

```text
B_1,...,B_9 = 597/5000, 633/5000, 669/5000, 141/1000,
               737/5000, 773/5000, 1553/10000, 809/5000, 81/500
B_m          = 3329/20000 for m >= 10
```

with `k=48`, `delta=361/50000`, `epsilon=3/400`, and
`A=(-3/400,1/4,3121/12000)` satisfies the complete frozen C722 analytic
verification.  Total large counts `0,...,23` are active and count 24 is
empty.  This audit proves no finite-dimensional quotient and hence no prime
gap theorem by itself.

The checker imports no schedule-search program.  It installs the displayed
rational schedule into the frozen source-level verifier and reconstructs all
fixed and continuous cases.

## Exact inventories and least margins

The mixed and transposed families each contain 863 ordered nonzero count
pairs and 2,589 branch checks.  Their least margin is
`139967/45000000000`, at the corrected IIb branch and count pair `(1,10)`
(transposed for the reverse orientation).  The outer and outer-near families
each contain 575 pairs and 1,725 checks, with least margins respectively
`3959999869/600000000000` and `43199999/2500000000`.

The dynamic IIc continuum is covered by all 147,200 declared rational cells.
Its least prefix margin is `2649997/120000000000`, at count pair `(9,10)`
and cell `(13,7)`.  The minimum source-level strict inequality margin outside
these packing checks is `1/200000000000`.

The checker separately reconstructs the uniform-ramp schedule at the same
plateau and obtains the same complete active-count inventory.  It also checks
the independently stated grid point `166453/1000000`: its mixed least margin
is `4967/45000000000`, and its dynamic least margin is
`2289997/120000000000`.

## Strict interior and hostile mutation

There is an exact ten-parameter open box around the displayed schedule:
each of `B_1,...,B_9` may vary independently by less than `1/200000`, and
the common plateau may vary by less than `1/500000`.  All 1,024 vertices
retain Definition-1 geometry and the active set.  Every support in the box is
contained in the componentwise upper corner; a fresh full audit of that
corner has mixed least margin `49967/45000000000` and dynamic least margin
`1809997/120000000000`.

As a fail-closed sensitivity check, increasing only the plateau by
`1/100000` preserves Definition-1 geometry but fails mixed IIb at `(1,10)`.
Thus the pass is not an artifact of checking only the active count set.

The schedule pointwise dominates the frozen plateau-0.16605 support, raises
all plateau coordinates strictly, and activates the previously empty total
large count 23.

## Frozen artifacts and replay

```text
agents/audit/verify_wide_c722_nonuniform_plateau16645_analytic.py
  fa8b10aa1b95d5f3636fbf3f76f5aac2484eb8fc4aec99e305667631c5363daf
agents/audit/results/wide_c722_nonuniform_plateau16645_analytic_audit.json
  999c77ced0adca5bae2f3302a05e481a583a5a75a3d89522bd64e52e7119f8b7
```

Run from `prime-gap-236/`:

```bash
python3 agents/audit/verify_wide_c722_nonuniform_plateau16645_analytic.py
python3 -O agents/audit/verify_wide_c722_nonuniform_plateau16645_analytic.py
```

The normal and optimized outputs are byte-identical and have SHA-256
`999c77ced0adca5bae2f3302a05e481a583a5a75a3d89522bd64e52e7119f8b7`.

The analytic assignment remains the one serialized in the result: inner to
inner moduli use Bombieri--Vinogradov; mixed and outer ordered band pairs use
the explicit repaired fixed/dynamic coverage; and
`rho(n;x)=(log n/log(3x)) 1_P(n)` has `c1=c2=0`.  Any matrix worker still
pinned to plateau 0.166 or 0.16605 must be repinned and recomputed before it
can claim this stronger support.
