# Integer-weight scalar v4 hostile audit

Date: 2026-09-03 (Europe/Berlin)

## Verdict

**SCOPED PRE-CERTIFICATE AUDIT PASS** for the frozen, unlaunched v4 source
closure below.  No target-size v4 result existed at the time of this verdict;
no future result inherits a pass without a separate source-closed result
audit and exact branch recombination.

| role | path | SHA-256 |
|---|---|---|
| v4 backend | `agents/exact-projection-engine/integer_weight_scalar.py` | `316ef7ab97f22c7163ec2687cc21db8351c47ff7697122d5d58476cfacbc5b32` |
| v4 runner | `agents/exact-projection-engine/d14_grid38_scaled_b_shard_integer_weights_v4.py` | `e861cca5e67793f1e2ee5bc5e864024bdf38971879ec5b26c9c898dd9053949f` |
| pinned producer tests | `agents/exact-projection-engine/test_integer_weight_scalar.py` | `5f073c808d7f73b07ab92c31117b76fe1f5c05c1201640e7072736a0b1fa64d8` |
| independent hostile tests | `agents/audit/test_integer_weight_scalar_independent.py` | `b47d4152a55391813ae2ed4839c283767be46bf79247004468da8d7d242bbda8` |

The runner also pins the repaired v3 radial backend and publication routine,
their tests, the fast-v2 runner/backend/tests, and the complete inherited v1
candidate/support/integrator closure.  Those nested hashes were checked
against the live bytes.  The runner snapshots every one before computation,
rechecks every byte before publication, requires an externally supplied hash
of itself, and publishes using the previously audited same-directory
O_EXCL/write/fsync/atomic-link/directory-fsync routine.  The initial
non-overwriting output check is therefore backed by an atomic final publish.

## Exact denominator-restoration derivation

Fix a branch and an inclusion--exclusion shift (h).  After the already
audited family/radial clearing, let (c_{	au,x,y}\in\mathbb Z) be a packed
coefficient, where (	au=(p,q)) is the pair of affine powers.  Independently
expand the shifted affine product as

\[
 A_{\tau,h}(X,Y)=\sum_{a,b}u_{\tau,h,a,b}X^aY^b,
 \qquad u_{\tau,h,a,b}\in\mathbb Q,
\]

and let (m_{i,j,h}\in\mathbb Q) be the exact requested polygon, interval, or
point moment.  The desired contribution of this shift is

\[
 S_h=\sum_{\tau,x,y,a,b}
 c_{\tau,x,y}u_{\tau,h,a,b}m_{x+a,y+b,h}.       \tag{1}
\]

The backend takes one LCM (U_h) of every nonzero affine-coefficient
denominator for the shift and one LCM (M_h) of every requested moment
denominator.  It computes

\[
 N_h=\sum c_{\tau,x,y}
       (U_hu_{\tau,h,a,b})(M_hm_{x+a,y+b,h})\in\mathbb Z
\]

and adds (N_h/(U_hM_h)).  This is exactly (1), including arbitrary signs and
cancellation.  The LCMs are local to the shift and branch, so differing
denominators cannot leak between domains.  The sum over shifts remains a sum
of exact `Fraction` values.  The older family/radial common denominator is
then divided out once at the endpoint level, exactly as in audited v3; the new
two LCMs have already been restored and are not divided out again.

The requested-moment index is exactly `(radial_x + affine_x,
radial_y + affine_y)`.  Each affine constant is changed from (q_0) to
(q_0+q_yh\delta), the literal substitution (Y_{\rm old}=Y+h\delta).
Slopes and radial exponents are unchanged.  Thus negative slopes and the
target ((-1,-1)) factors retain the correct signs.

If an affine product vanishes identically, its map and requested set are
empty, both LCMs default to one, and the contribution is zero.  Empty domains
likewise return zero moments.  At a positive-dimensional equality
`total_bound-shift == 0` the shift is null and skipped.  For a genuine
zero-dimensional face it is instead evaluated as the point ((0,0)), with
strict lower-bound branch conventions preserved.  A nonzero radial power on
an absent aggregate is rejected before contraction; an affine power of that
aggregate correctly evaluates to zero through its requested moment.

## Independent hostile execution

The independent oracle does not call fast-v2's affine collector or its domain
moment batcher for expected packed values.  It repeatedly multiplies named
affine polynomials, forms the full signed polynomial, and integrates it by a
separate exact rational Green-theorem polygon routine, a direct interval
antiderivative, or point evaluation.  Coverage includes:

- dense mixed-sign packed rows, affine powers through four, and two unrelated
  rational slope pairs;
- every domain shape used by the four scheduled branches: total upper/lower,
  X cap, Y lower/upper, and combined clipping;
- 80 seeded random packed problems with branch-local rational domains and
  denominators, plus exact cancellation of equal and opposite rows;
- (r=0), (s=0), and (r=s=0), equality and empty boundaries, an
  identically zero affine, nonintegral packed-coefficient rejection, and
  forbidden zero-dimensional radial powers;
- full (k=2) endpoint values against literal original-coordinate polygons,
  with all four branch names and the sole external factor (k=2);
- exact v4 = pruned-v3 = unpruned Fraction-reference values and high/low
  branch maps for varied (k=1,\ldots,5), every common count, nonuniform
  schedules, active and empty cutoffs, and zero-dimensional faces.

Executions:

```text
python3 -m unittest -v agents/audit/test_integer_weight_scalar_independent.py
# 5/5 PASS; 15.237 s unittest time; 24,960 KiB peak RSS

python3 -O -m unittest -v agents/audit/test_integer_weight_scalar_independent.py
# 5/5 PASS; 15.431 s unittest time; 29,648 KiB peak RSS

python3 -m unittest -v agents/exact-projection-engine/test_integer_weight_scalar.py
# 3/3 PASS
python3 -O -m unittest -v agents/exact-projection-engine/test_integer_weight_scalar.py
# 3/3 PASS
```

All audited Python sources passed `py_compile`, and the independent additions
passed `git diff --check`.  I found no exact mathematical or publication
counterexample.  The verdict remains source-scoped until a target shard is
produced and checked.
