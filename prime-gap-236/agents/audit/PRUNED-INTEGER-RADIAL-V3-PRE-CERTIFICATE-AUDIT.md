# Maximum-shift-pruned integer radial v3 hostile audit

Date: 2026-09-03 (Europe/Berlin)

## Verdict

**SCOPED PRE-CERTIFICATE AUDIT PASS** for the repaired, frozen v3 source
closure listed below.  No target v3 shard existed when this verdict was issued;
every target result still requires a separate result-level audit.  This verdict
does not extend to the retired runner SHA
`9754335c47f2073128a50343d025e67aef5d4ce5292c67f7648246dd6f4c6748`.

Frozen bytes:

| role | path | SHA-256 |
|---|---|---|
| repaired v3 runner | `agents/exact-projection-engine/d14_grid38_scaled_b_shard_pruned_v3.py` | `ce5236eaed52be549a316587e8c3c543a0b02b1594c14ba32f4c1a877fd9bb26` |
| pruned backend | `agents/exact-projection-engine/pruned_integer_radial.py` | `834f624647094bf71364ad5c2b47e00371c7e7e78ed37c1d06eeca9186f73afe` |
| producer math tests | `agents/exact-projection-engine/test_pruned_integer_radial.py` | `17b5eac692f859728d502e90a52b2c9c5ce03ef45e7966ce9104d8878910adfd` |
| exclusive-publication tests | `agents/exact-projection-engine/test_pruned_v3_exclusive_publish.py` | `855b3e07ee71f75917a9ddceb2d969e10aab8c81550aa036423f7104eb5ef78d` |
| independent hostile tests | `agents/audit/test_pruned_integer_radial_independent.py` | `89a2d69f1a965f71646af429c49940616370a0d9561cf9e2a7b240722c0a7e0f` |

The runner additionally pins fast-v2 runner SHA `4613b0fb...`, fast backend
SHA `5d9d82ae...`, its tests SHA `d2898ef5...`, and, through the frozen v1
runner, the cross engine, radial reference, frontier, D19/D14 inputs and all
support/audit inputs.

## Exact pruning lemma

Let $B$ be the `total_bound` of any scheduled Definition-5 branch, and let
$h$ be the number of small-coordinate caps shifted by inclusion-exclusion.
After the shift the aggregate domain contains

\[
 X+Y\leq B-h\delta.
\]

The cross runner defines $C=\eta-r\delta$.  Direct inspection of all four
branch constructors gives $B\leq C$:

- `Sdelta`: $B=\min(C,\alpha-(r+1)\delta)$;
- `Stotal`: $B=C$;
- `Ltotal`: $B=\min(C,\alpha-(r+1)\delta)$;
- `Lbig`: $B=C$.

The reference function `_maximum_active_shift(C,delta)` returns

\[
 H=\max\{j\in\mathbb Z_{\geq0}:j\delta<C\}
   =\left\lceil C/\delta\right\rceil-1.
\]

Consequently, if $h>H$, then

\[
 B-h\delta\leq C-h\delta\leq0.                 \tag{1}
\]

For the theorem calculation there are $k-1=47$ shared variables.  The
domain in (1) is empty up to a lower-dimensional boundary and every polynomial
integral over it is exactly zero.  The same conclusion holds in all generic
positive-dimensional calls.  If the shared dimension is zero, there are no
small coordinates, hence the small-coordinate transform has only $h=0$;
the live cross path has $C>0$ and therefore $H\geq0$, so no potentially
nonzero zero-dimensional term is pruned.  This resolves the equality case
without assuming that a point has zero measure in dimension zero.

In the frozen target,

\[
 C/\delta=8960917/600000-r,
\]

which is never an integer.  Thus $H=14-r$ for every scheduled
$r=0,\ldots,12$.  The independent test enumerates every target branch at both
endpoints and verifies $B\le C$ and (1) for the first discarded shift.

## Why pruning inside the convolution preserves coefficients

For a positive small-coordinate exponent $e$, the exact boxed-coordinate
inclusion-exclusion choices are

\[
 (0,e,e!)
 \quad\hbox{or}\quad
 (1,j,-{e\choose j}\delta^{e-j}j!),\qquad0\le j\le e,
\]

where the first component is the increment in shifted-cap count.  A zero
exponent supplies the two choices `(0,0,1)` and `(1,0,-1)`.  All future shift
increments are nonnegative.  Therefore a partial convolution state with
shift $>H$ can never return to shift at most $H$; deleting it early cannot
alter any retained coefficient.  Grouping the zero exponents at the end gives
the exact factor $(-1)^z{z_0\choose z}$.  The Dirichlet angular factor
$(d+s-1)!^{-1}$ depends on total polynomial degree and the original number
of small coordinates $s$, not on how many zero exponents were grouped; the
backend uses exactly this exponent.

`partition_face_radial_pruned` then performs the unchanged exponent split
between large and small coordinates, including repeated-part binomial
multiplicities, zero-coordinate placements, full monomial-orbit size, and the
unchanged translated-large radial map.  Hence its result is coefficient by
coefficient equal to

```text
{key: value for key, value in reference_partition_face_radial.items()
 if key.shift <= H}
```

before any scalar integration.

The family backend takes its radial LCM only over these retained transforms.
Fast v2 already filters to the same key set before taking that LCM.  Therefore
both the packed integer coefficients and the radial denominator are identical,
not merely proportional.  Family denominator clearing, collected affine
integration, restoration by the product of the two denominators, and the sole
factor $k=48$ are inherited unchanged from the previously audited fast-v2
backend.

## Hostile checks

The independent test constructs its expected transform without either radial
implementation: it enumerates every distinct padded monomial in $P_\lambda$,
every choice of the $r$-large coordinate face, and every per-coordinate
inclusion-exclusion/binomial choice.  It then compares that literal exact map
both with pruned v3 and with the filtered frozen reference.

Coverage was:

- 2,080 literal coefficient-map comparisons over two rational deltas,
  dimensions 0 through 5, every face $r$, cutoffs from -1 through
  one beyond the maximum possible shift, odd/even/repeated exponents, empty
  partitions, and zero-large/zero-small faces;
- 135 arbitrary integer-family cases through dimension 6, comparing radial
  denominator and every packed integer coefficient with fast v2;
- full high/low branch values for $k=1,2,4,5$, including no shared
  variables, zero-large and zero-small aggregate faces, nonuniform schedules,
  nonintegral cutoffs, and an exact integer cutoff;
- an observable discarded boundary coefficient: for three zero-exponent small
  coordinates at $C=3\delta$, the reference $h=3$ coefficient is nonzero
  but its positive-dimensional shifted-domain integral is exactly zero;
- all four target branch-domain formulas for every $r=0,\ldots,12$ and both
  rational endpoints;
- invalid face indices, overlong partitions, negative maximum shift, and the
  genuine zero-dimensional transform.

Executions:

```text
python3 -m unittest -v agents/audit/test_pruned_integer_radial_independent.py
# 5/5 PASS; 8.019 s unittest time; 27,940 KiB peak RSS

python3 -O -m unittest -v agents/audit/test_pruned_integer_radial_independent.py
# 5/5 PASS; 8.577 s unittest time; 32,584 KiB peak RSS

python3 -m unittest -v agents/exact-projection-engine/test_pruned_integer_radial.py
# 2/2 PASS
python3 -O -m unittest -v agents/exact-projection-engine/test_pruned_integer_radial.py
# 2/2 PASS

python3 -m unittest -v agents/exact-projection-engine/test_pruned_v3_exclusive_publish.py
# 2/2 PASS
python3 -O -m unittest -v agents/exact-projection-engine/test_pruned_v3_exclusive_publish.py
# 2/2 PASS
```

All five sources/tests also passed `py_compile`; `git diff --check` passed for
the independent test.

## Publication failure found and repaired

The first frozen v3 runner (SHA `9754335c...`) checked output nonexistence only
before its long calculation and ultimately used `os.replace`.  Two simultaneous
same-path processes could both pass the check and the last would silently
overwrite the first; an intervening file could likewise be destroyed.  I
reported this exact counterexample and withheld a verdict.  That runner was
retired without a target launch.

The repaired runner SHA `ce5236ea...` writes a same-directory O_EXCL temporary,
fsyncs it, and uses atomic `link(2)` publication.  `link` fails with `EEXIST`
and never replaces an extant final path; the directory is fsynced and the
temporary is removed.  The pinned regression verifies both an intervening
sentinel and two synchronized forked publishers: exactly one publishes, one
receives `EEXIST`, the winning bytes are intact, and no temporary remains.

## Required result audit

A v3 target shard may be admitted only after checking its producer SHA against
`ce5236ea...`, the full nested source map, exact branch inventory, canonical
rationals, denominator/work metadata (including the recorded maximum shift),
exact recombination with one factor 48, and preferably exact equality with the
already frozen fast-v2 shard for the same $r$.  No such target result is
certified by this pre-certificate report.
