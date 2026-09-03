# Independent tagged-dyadic D12 driver: pre-launch hostile audit

Date: 2026-09-02 (Europe/Berlin)

## Verdict

`AUDIT PASS` in the strictly **pre-launch** scope described below.

The audited result driver is

```text
verify/check_c10_d12_affine_independent_dyadic.py
SHA256 7e2ed20a68e3c3e95a9566b32cae3d403949a79a3a81adfa61b8dab833b640b9
```

No target D12 integral was launched, no target interval or quotient was
produced, and this verdict is not a sieve certificate.  It says that the
frozen driver is a sound outward-enclosing reconstruction of its pinned
exact tagged-affine algebra, subject to the explicit limitations below.

The hostile regression is

```text
agents/small-delta-frontier/test_independent_dyadic_driver_audit.py
SHA256 1a62de64f491473275926a2e3616f1216c36e2c247fef01f911b2bfa841f8f6b
```

All seven tests pass in normal and optimized Python modes.

## Frozen arithmetic and provenance closure

The driver checks these byte hashes at preparation and again after each long
phase:

| file | SHA256 |
|---|---|
| `verify/check_c10_d12_affine_exact.py` | `5514f63159ad74e54142cf1db2d88a9c69f552cad3d253cd50ca66452cf2784e` |
| `verify/dyadic_interval.py` | `f6f1730f77ba490f04326338e7b3bfe5ab2e5c6438f10892bdf3f5bfe6fc875d` |
| `verify/exact_affine_multiplier.py` | `9c21d73af25f63ad16c62a2a1935a9cfd3a8d134d7b7ada2620eddc12e1c3d3e` |
| `verify/exact_affine_multiplier_batched.py` | `d824ab8ebb59da4cd94da7b17350c36ba5888bc2260fdeb8e976f4f825405ee8` |
| `verify/exact_capped_certificate.py` | `1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c` |

This is the complete local import closure.  The imported exact driver in turn
has exactly the last three files as its local dependency set; the independent
driver adds the exact driver's bytes and the dyadic ring.  Standard-library
modules are outside this byte-pin boundary.

The loader does not merely trust the integer-scaled vector's metadata.  It:

1. pins the original 272-term rational source and its separately frozen
   ordered label/vector payload;
2. reconstructs the 714-bit least common denominator from the source;
3. checks every integer coefficient against `source_coefficient * LCM` and
   checks primitive content;
4. pins and strict-parses the affine artifact, applies the stated cutoff 11,
   reconstructs its 206-bit effective LCM, and checks every resulting
   coefficient is integral.

Hostile temporary-copy mutations of an integer coefficient, the claimed base
LCM, and the original rational vector are rejected even when the mutated
file's expected byte hash is updated in the test harness.  The last mutation
is stopped by the independent ordered-payload commitment.

## Why coefficient intervalization is outward-safe

The target leaves supplied to the tagged recurrence are integers, hence their
initial dyadic intervals have zero width.  Exact geometric Fractions are
coerced into outward-rounded fixed-point intervals only when they interact
with a coefficient.  The ring implements addition, subtraction,
multiplication, integer powers, and division by nonzero exact geometric
constants by integer floor/ceiling formulas.  Thus each primitive operation
contains the corresponding exact rational operation; structural induction
gives containment for the finite tagged recurrence.

The potentially dangerous point was coefficient-dependent control flow.
Every coefficient cleanup in the consumed path is one of:

```text
if coefficient
if value
any(aggregate)
any(radial.values())
```

`DyadicInterval.__bool__` is false only when an exact shadow proves the value
is zero or the enclosure is exactly `[0,0]`.  A nondegenerate interval that
contains zero is true.  Consequently cancellation widening can retain extra
terms, but can never delete a possibly nonzero term.  Equality similarly
cannot identify two merely overlapping enclosures.  Geometric branch
comparisons, polygon clipping, inclusion--exclusion shift limits, and orbit
keys depend only on exact Fractions and integers, never on coefficient
intervals.

The audit directly injects a shadowless interval `[-2^-256,2^-256]` through
`poly_add_term`, `build_basis_terms`, affine-power expansion, and tagged
radial packing; every layer retains it.  It then evaluates an uncertain
three-term basis and uncertain affine tables at `k=2`.  The resulting I and
`kJ` intervals contain five independently evaluated exact specializations of
those coefficient boxes, using the expanded literal oracle, in both forward
and reverse face order.  This test uses intervals that cross zero in both the
base and multiplier coefficients; it is stronger than testing only singleton
Fraction leaves.

## Active faces and ordered branches

For the pinned C10 support,

```text
alpha = 79247/300000, eta = 76247/300000, delta = 1/100,
B1 = B2 = 3/20, Bm = 97/625 for m >= 3.
```

Both I and J visit exactly common counts `r=0,...,15`, in the requested
forward or reverse order.  The endpoint distinction is material:

```text
B15 - 15 delta =  13/2500  > 0,
B16 - 16 delta =  -3/625   < 0,
eta - 15 delta = 31247/300000 > 0,
B17 - 17 delta = -37/2500  < 0.
```

Thus J's `r=15` small distinguished-fiber branch remains active while its
`r+1=16` large branch is dead; `r=16` has neither branch.  A target-parameter
test patches only the expensive per-face arithmetic and confirms that the
public I and J traversals call precisely all 16 counts in both orders.

Within each J face the frozen batched helper allocates 16 distinct ordered
branch slots and loops over the full Cartesian square of
`(small_delta, small_total, cap, total)`.  It does not introduce a factor two
or merge left/right families.  Nominal boundary intersections are checked to
have zero exact geometric measure.  Separate frozen exact regressions already
match the literal ordered-branch oracle for signed `k=2,3` cases in both face
orders and worker counts; the uncertain-box test above independently checks
that intervalizing those algebraic coefficients preserves containment.

## Stage, serialization, and theorem gate

The I stage has an exact field set and a required lowercase 64-hex byte hash.
Interval endpoints are canonical signed decimal integers, the precision must
match, Boolean widths are rejected, `hi-lo` must equal the nonnegative width,
and the redundant exact endpoint Fractions are reconstructed and compared.
Extra/missing fields, a Boolean width, a changed endpoint Fraction, and a
noncanonical endpoint integer all fail closed.

The stage and output paths must differ and cannot resolve to the driver, any
of the three input artifacts, or any arithmetic dependency.  The driver,
dependencies, input artifacts, and I-stage bytes are checked again after the
appropriate phase.

The denominator must satisfy `I.lo > 0` before it is staged and again when it
is loaded.  The J routine returns J (not `kJ`), and the wrapper multiplies it
by the target integer 48 exactly once.  The only positive-candidate gate is

```text
I.lo > 0 and (48*J - I).lo > 0.
```

The hostile wrapper test makes staged `I=96`: `J=3` passes, `J=1` fails, and
`J in [2,3]` fails because the lower margin is exactly zero.  It also checks
that the serialized numerator is exactly `48*J`.

## Scoped limitations

- No C10 D12 I or J traversal was run during this audit.  There is no target
  sign, quotient, runtime, error width, or output artifact to audit.
- This driver is independent of the grouped Decimal/dyadic evaluator, but it
  intentionally reuses the frozen tagged exact recurrence and its batched J
  optimization.  It is therefore a second representation relative to the
  grouped engine, not a proof of the tagged recurrence without its exact
  low-k oracle tests and source review.
- A stage SHA proves the bytes loaded by J, not their computational origin.
  Final verification should run `--phase all` in a controlled invocation or
  independently reconstruct I from the published inputs.
- Start/end byte checks do not defend against a malicious process that swaps
  a file and restores it entirely between checks.  That adversarial operating
  system model is outside the checker trust boundary.
- `theorem_ready` remains hard-coded false.  A positive target output would
  still need a fresh output audit, a second reconstruction, and the complete
  analytic/support audit before it could enter `PROOF.md`.

## Reproduction

From `prime-gap-236/`:

```bash
PYTHONPATH=. python3 agents/small-delta-frontier/test_independent_dyadic_driver_audit.py -v
PYTHONPATH=. python3 -O agents/small-delta-frontier/test_independent_dyadic_driver_audit.py -v
```

Each command must report seven passing tests.  The upstream dyadic and exact
affine suites also passed (13 tests total):

```bash
PYTHONPATH=. python3 -m unittest \
  verify/test_dyadic_interval.py \
  verify/test_exact_affine_multiplier.py \
  verify/test_exact_affine_multiplier_batched.py
```
