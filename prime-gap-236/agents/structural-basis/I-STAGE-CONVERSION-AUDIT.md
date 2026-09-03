# Audit of the legacy MP100 C10 (I)-stage conversion

## Verdict and scope

**DISCOVERY CONVERSION PROVENANCE PASS WITH EXPLICIT LIMITS.**

The converted stage is a faithful, reproducible wrapper around the completed
legacy MP100 denominator.  The denominator string, the input parameters, the
272-term degree-12 vector, and every field already present in the raw stage are
preserved byte-for-byte as JSON values.  The current driver rejects the stage
unless the caller explicitly permits the pinned legacy driver hash, and that
override is unavailable in rigorous mode.

This is only provenance for a heuristic/discovery-sign computation.  The raw
stage did not record the integrator hash, and the source bytes of the untracked
legacy driver were not retained.  Consequently no result resumed from this
stage can be promoted to an exact certificate.  A final certificate must
recompute both (I) and (J) end-to-end with the final pinned checker and with
no legacy-hash override.

## Pinned artifacts

| artifact | SHA-256 |
|---|---|
| raw MP100 (I)-stage | `f69847971d40ba0abe916a42c63533f32b0012b7441df9b7483314a5a188e38b` |
| converted MP100 (I)-stage | `9441f2b227b761fd71f61211f16308eed77f95eddfe9458957a111b504424eaa` |
| conversion script | `564ce9adb3cce12a165e42e79cbd3920877338162c5a251581eb62adcc922e58` |
| degree-12 source vector | `719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87` |
| legacy grouped driver, as recorded by the raw stage | `9ee84b1a1a05c884b37f70bd68680bf5ed8650bd5d1aa0afa63fe4a0db3ae298` |
| final grouped driver | `47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a` |
| final exact integrator | `941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52` |
| independent audit test | `a47362805b9592e90fdacd7fcc06cef4df232e903c3b091936350469a6e029b4` |

The files are, relative to `prime-gap-236/`, respectively:

* `agents/exact-integrator/results/c10_capped_fullD12_vector_grouped_mp100.json.I-stage.json`;
* `agents/exact-integrator/results/c10_capped_fullD12_vector_grouped_mp100.converted.I-stage.json`;
* `agents/exact-integrator/convert_legacy_mp_stage.py`;
* `agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json`;
* `agents/exact-integrator/grouped_fixed_vector.py`;
* `agents/exact-integrator/src/exact_integrator.py`; and
* `agents/structural-basis/tests/test_i_stage_conversion_audit.py`.

## Exact preservation checks

The raw denominator is

```text
2.787528827630692682159223062413582835678541733826585732118297248191047814521016638808619046446112162E-134
```

and the converted stage contains exactly the same string.  Structurally, the
converted object is the raw object with precisely two additional fields:
`integrator_sha256` and `legacy_nonrigorous_conversion`.  No pre-existing key
or value changes.

The source-vector file has (k=48), 272 distinct basis labels, and 272
coefficients.  Its SHA-256 is checked by both the converter and the resumed
driver.  Thus the stage cannot silently bind the preserved denominator to a
different parameter/vector input without failing a hash check.

A fresh conversion to a temporary path produced the converted artifact
byte-for-byte, including its SHA-256.  The converter rejects each of these
mutations: rigorous arithmetic, a non-decimal mode, missing completion state,
a nonpositive denominator, an already hashed stage, a wrong legacy driver
hash, and a wrong input hash.

## Evidence that the legacy and final (I) algorithms agree

The exact old driver bytes are unavailable, so a literal source diff is
impossible.  The following independent operational check is the strongest
recoverable evidence.

1. A retained legacy D4 MP80 stage produced by the same old driver was
   reevaluated from scratch by the final serial driver.
2. The two decimal denominators agree to relative error below
   (2\times10^{-79}); they differ only in the last printed Decimal unit.
3. Both agree with the independent exact-Fraction D4 denominator to relative
   error below (10^{-62}).  The weaker second tolerance accounts for severe
   cancellation in that regression case.
4. The current exact D4 path separately passes pairwise reconstruction and
   serial-versus-fork equality tests.

The final-driver changes described by the surviving code and regression
history are output self-containment, fork-by-(r) dispatch, (J)-only domain
filters and the (k=1) half-open repair, hash/RSS accounting, and CLI checks.
The D4 experiment directly tests the relevant claim that these changes did not
alter the scalar (I) computation.

There is also local timeline evidence: the pinned exact-integrator file has
mtime `2026-09-01 19:28:50.252 +02`; the raw stage's recorded duration and mtime
put the legacy (I) run at approximately `20:34:53`--`21:27:17 +02`.  Hence
the current integrator file predates the run.  This supports, but does not
cryptographically prove, the converter's inserted integrator hash.

## Resume behavior

The final driver validates:

* the complete input-file SHA-256;
* its own recorded SHA-256;
* the integrator SHA-256;
* decimal precision and arithmetic mode;
* exact parameter strings; and
* stage status.

Without the explicit legacy-driver allowance, a converted D4 fixture is
rejected before any (J) work.  With the pinned old hash in non-rigorous mode,
the same fixture resumes and preserves its quotient string.  Exact/rigorous
mode rejects both script-hash and integrator-hash override attempts.

The non-rigorous allowance deliberately does not authenticate the mathematical
truth of the denominator; a caller who edits a stage and then supplies matching
non-rigorous metadata can at most manufacture another heuristic result.  This
is why the converted MP100 run is discovery-only.

## Reproduction

From `prime-gap-236/` run:

```sh
python3 -m unittest agents.structural-basis.tests.test_i_stage_conversion_audit -v
python3 -m unittest agents.structural-basis.tests.test_grouped_evaluator_audit -v
```

At the pinned state these report respectively `Ran 5 tests ... OK` and
`Ran 12 tests ... OK`.

## Mandatory condition for any theorem certificate

Do not cite the converted stage as exact or rigorous.  The theorem path must
use an end-to-end reconstruction in which the checker itself parses the
canonical integer vector, reconstructs the support integrals, proves (I>0),
and proves (48J-I>0), with all dependency hashes pinned and no acceptance of
legacy-stage metadata.
