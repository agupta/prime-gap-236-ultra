# Green-v9 `R<=9` standalone adapter audit failure

Verdict: **PRE-CERTIFICATE AUDIT FAIL** for superseded adapter

```text
verify/check_H1_236_Rle9_green_v9.py
dace7747f0573134957c2f9a14a6c4cd957789d8538d46a5e86dddd3d52856ee
```

No full replay, aggregate, compact certificate, or theorem claim is covered.

## Failure 1: removed bootstrap dependency

The adapter first imports pinned base replay `4179aeda...`.  Importing that
base replay in turn reads, hashes, and imports

```text
verify/assemble_one_band_236_fixed_polygon_v8_r09.py
67c479a18b12f7e5d4df84a854dd8364f981ecdbcfd2daf2fd256edb2029b557
```

before the adapter rewires the base module to Green.  The adapter then
explicitly removes this old assembler from its final PINS.  A fresh
`Path.read_bytes` trace around adapter import saw 14 distinct explicit
repository reads.  The sole read outside `PINS union {adapter FILE}` was the
old fixed-v8 assembler above.  Thus the advertised flat startup/end source
closure omitted a file required and imported during that same startup.

The minimal repair is to retain `_OLD_AGG.FILE` at the old assembler's frozen
SHA in PINS.  Its test need not be retained merely because it is named in the
base module: that test is not read or imported during adapter startup or
verification.

## Failure 2: Boolean common-count alias

`adapt_b_audit` checked only four Green identity flags.  It accepted a
dictionary with

```text
common_r = true
```

and translated it to the fixed-v8 audit name.  At loop count 1 the inherited
base check used `audited.get("common_r") != count`; in Python,
`True == 1`, so the wrong wire type passed that count test.  With the matching
input hash and the required truth flags, the remainder of the inherited
audit gate did not reject the alias.

More generally, the adapter accepted extra/missing audit fields and did not
require the fixed-denominator/cache truths or the no-reference values that
the actual no-reference Green checker contract promises.  Because this
adapter exists specifically to translate a child-process wire contract, it
must validate the exact Green audit schema and exact JSON types before
renaming anything.  At minimum it must require exact integer count in
`0..9`, `maximum_active_shift=14-count`, the exact active family list, all
required Boolean proofs, `reference_exact_fields_bit_equal is None`, and
`reference_sha256 is None`.

These defects concern fail-closed provenance/wire validation, not the Green
polygon formula or the already-audited r9 result.  Any repaired adapter needs
a fresh audit and must not inherit a PASS from this report.
