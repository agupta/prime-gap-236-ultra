# Globally collected integer scalar v5 hostile audit

Date: 2026-09-03 (Europe/Berlin)

## Verdict

**SCOPED PRE-CERTIFICATE AUDIT PASS** for the repaired, frozen, unlaunched v5
closure below.  An earlier documentation inventory failure was found and
repaired as described below; the runner which pinned the faulty test snapshot
was retired.  No target v5 result existed at this point, so this source verdict
is not a result or theorem verdict.

| role | path | SHA-256 |
|---|---|---|
| v5 backend | `agents/exact-projection-engine/collected_integer_scalar.py` | `aef0a183d71b9c41b5373806d03481b94cb4e61a1ff3561888b8c31f94e8c890` |
| v5 runner | `agents/exact-projection-engine/d14_grid38_scaled_b_shard_collected_v5.py` | `eaa22454347d17201c60c30e1ed5ac01e34ba39368bc4711c1ea2c7f6d03ba82` |
| pinned producer tests | `agents/exact-projection-engine/test_collected_integer_scalar.py` | `281ff70246041cc0d2ed948c41187b406a26b9d7ba9b94a1f4b502dab63d31d4` |
| independent hostile tests | `agents/audit/test_collected_integer_scalar_independent.py` | `baea74decb6d7e079f9548b55b77c6c393d037ae66ef660f21e60a66bfb29e9f` |
| corrected derivation note | `agents/exact-projection-engine/COLLECTED-INTEGER-SCALAR-V5.md` | `10405e9837fb4a48fede9f6d4f099508d1c42f7ec58ca44457f4d15886f752dc` |

## Exact collection identity

Fix an endpoint, branch, and surviving inclusion--exclusion shift (h).  The
audited v3 stage supplies packed integers (c_{\tau,x,y}), with tag
(	au=(p,q)).  Write the exact shifted product of the two tagged affine
powers as

\[
 A_{\tau,h}(X,Y)=\sum_{a,b}u_{\tau,h,a,b}X^aY^b.
\]

Let (U_h) be the LCM of all denominators in every such affine product for
this shift.  V5 collects globally, across every radial row and every tag,

\[
 C_{i,j}=\sum_{x+a=i,\,y+b=j}
 c_{\tau,x,y}(U_hu_{\tau,h,a,b})\in\mathbb Z.       \tag{1}
\]

Thus all paths to the same final named monomial collide with their signs
intact, and exact zero coefficients are discarded only after the sum (1).
Because the branch domain and its measure depend on (h,r,s), not on the tag
or the path to ((i,j)), this collection commutes with integration.

For the remaining exact moments

\[
 m_{i,j,h}=\int_{D_h}X^iY^j\,d\mu,
\]

let (M_h) be their denominator LCM.  The code evaluates

\[
 \frac{\sum_{i,j}C_{i,j}
       (M_hm_{i,j,h})}{U_hM_h},                     \tag{2}
\]

which expands exactly to the original tagged contraction.  Both LCMs are
local to the branch and shift and are restored in (2).  The already cleared
family/radial denominator is different and is restored exactly once after
the endpoint sums.  This proves that neither collision, cancellation, nor
branch-local denominator variation changes the value.

The literal substitution is also preserved: both affine constants receive
`+ y_slope*h*delta`, corresponding to (Y_{old}=Y+h\delta), and requested
moments use final exponents `(radial_x+affine_x,
radial_y+affine_y)`.  Empty affine products give an empty final polynomial and
LCMs equal to one.  Empty positive-dimensional boundaries are skipped, while
the genuine zero-dimensional point is evaluated with the inherited strict
lower-bound branch convention.  A radial power in an absent aggregate fails
closed.

## Independent hostile tests

Expected packed values were obtained by repeated multiplication of ordinary
named affine polynomials followed by independent exact rational
Green-theorem polygon integration, interval antiderivatives, or point
evaluation.  This route does not use fast-v2's affine collector or moment
batcher.  Coverage includes:

- two distinct pairs of cross-tag paths producing the same final monomial and
  cancelling exactly, while an unrelated constant survives;
- 100 seeded random signed packed problems spanning total upper/lower, X cap,
  Y lower/upper, combined domains, (r,s>0), (r=0), (s=0), and the
  zero-dimensional point;
- zero affine products, exact and empty boundaries, noninteger packed input,
  and forbidden absent-aggregate radial powers;
- full (k=2) high/low values for every scheduled branch against the separate
  literal original-coordinate polygon oracle, including the one external
  factor (k=2);
- exact v5 = v4 = pruned-v3 = unpruned Fraction-reference values and branch
  maps for every common count at (k=1,\ldots,5), with nonuniform schedules;
- a larger 720-row, 72-tag collision inventory: 33,360 radial--affine integer
  products collected into 538 final nonzero monomials/moment multiplications,
  with 170-bit affine and 236-bit moment denominator LCMs, and exact equality
  with v4.

Executions:

```text
python3 -m unittest -v agents/audit/test_collected_integer_scalar_independent.py
# 5/5 PASS; 18.717 s unittest time; 25,680 KiB peak RSS

python3 -O -m unittest -v agents/audit/test_collected_integer_scalar_independent.py
# 5/5 PASS; 19.630 s unittest time; 30,216 KiB peak RSS

python3 -m unittest -v agents/exact-projection-engine/test_collected_integer_scalar.py
# 5/5 PASS
python3 -O -m unittest -v agents/exact-projection-engine/test_collected_integer_scalar.py
# 5/5 PASS
```

The runner pins v3 pruning/publication sources and tests, fast-v2 and all
inherited v1 inputs.  It snapshots and checks that closure before import,
rechecks it before writing, requires an external self hash, and uses the
audited non-overwriting atomic-link publication routine.  All sources passed
`py_compile`; independent additions passed `git diff --check`.

## Failure found and repaired: mislabeled target inventory

The first supplementary-note snapshot, SHA `d364519e6ad7...`, stated that the
older target `r=0` shard performed 22,244,880
"affine-coefficient/moment scalar products."  That was false.  In the frozen
fast-v2 `r=0` result SHA `6594f8a5...`, 22,244,880 is exactly the radial-stage
`distributed_terms` count.  Summing `scalar_products` over high and low and
all four branches gives

```text
2 * (1,019,711 + 15,568,807 + 15,568,807 + 12,798,335)
= 89,911,320.
```

The same result records 78,810 requested moments over those endpoint/branch
calls.  The producer confirmed the counterexample, corrected the note to SHA
`10405e98...`, and added a regression that pins the frozen `r=0` artifact and
requires the two distinct counts 89,911,320 and 22,244,880.  The repaired test
is SHA `281ff702...` and passed 5/5 in normal and optimized modes.  The old
runner SHA `e5a6d10e...` was retired unlaunched; the repaired runner SHA
`eaa22454...` pins the new test.  I rechecked its seven local pins, import,
publication closure, and byte snapshots.

A target v5 shard must still record its actual surviving final-monomial count;
it is expected to be at most the old requested-moment inventory, but this is a
cost expectation, not a proof premise.  The repair fully resolves the scoped
documentation finding without changing the already audited backend algebra.

## Frozen target `r=0` result audit

After the source verdict, the first theorem-size v5 shard landed:

| object | SHA-256 |
|---|---|
| `agents/exact-projection-engine/results/d14_grid38_scaled_b_collected_v5/common_r_00.json` | `d097b5cdcd8e6fca25144e82a9bc2760d17441b62f74bef996d4a211f8feece1` |
| `agents/audit/verify_collected_v5_cross_shard.py` | `11e2930bce62f13faf8c4874a439ab02220e155a384ea1f0e0587a871cb4abb9` |
| `agents/audit/results/d14_grid38_scaled_b_collected_v5/common_r_00.audit.json` | `bb14f4bac2372cecae0c06a44e29759b67d219e18ccf261b1ab83bb69c2bd2c3` |

The strict checker verified canonical JSON, repaired runner SHA `eaa22454...`,
the complete live and serialized source closure, exact frozen geometry,
(H=14), all four branch inventories, every reduced rational, upstream
family/radial denominator metadata, v5 collection invariants, and exact

\[
 b_0=48\left(\sum \mathrm{high}-\sum \mathrm{low}\right).
\]

It additionally required exact bit-for-bit equality of the high and low
branch maps, final scaled value, common work inventories, and upstream
denominators with frozen fast-v2 `r=0` SHA `6594f8a5...`.  Both normal and
optimized checker executions produced the same audit bytes, SHA
`bb14f4ba...`.  Therefore this individual shard has a **RESULT AUDIT PASS**.

The measured v5 inventory was 89,911,320 integer radial--affine collection
products and 78,810 final moment multiplications; no final target monomial
cancelled completely in this shard.  Total producer time was 361.960 seconds
and peak RSS 327,240 KiB, versus 543.726 seconds and 537,396 KiB for fast-v2.
This performance comparison is observational only.  Counts `r=1,...,12`,
their exact sum, and the final quotient remain outside the individual `r=0`
result verdict.
