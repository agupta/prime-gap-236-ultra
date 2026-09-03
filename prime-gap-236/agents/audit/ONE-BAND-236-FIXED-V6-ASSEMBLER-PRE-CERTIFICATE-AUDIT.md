# Fixed-v6 one-band scalar assembler hostile audit

## Verdict

**SCOPED PRE-CERTIFICATE AUDIT PASS** for:

```text
verify/assemble_one_band_236_fixed_v6.py
SHA-256 91ab96385d32921c035bd5537a56e8254455a8033bf41e2298b7ec13be552bbc

verify/test_assemble_one_band_236_fixed_v6.py
SHA-256 593b1f4046985f4f92d8decd0f77993bddaafdb54dc2ae8317379d87cb1c767b
```

The initially supplied `6153050a...` wrapper failed hostile review because it
accepted an empty `clear_stats`, did not tie radial associations to active
family entries, and evaluated an untrusted factorial index before validating
it.  That snapshot is retired.  The defects are repaired in `91ab9638...` and
have dedicated regressions.

This is an aggregation/provenance verdict only.  Like the pinned base
assembler, the wrapper accepts a self-consistent alteration of serialized
branch values.  Every target b shard must separately pass the fixed-v6 result
checker and exact integration replay; this pass cannot certify an integral or
the theorem.

## Source and wire closure

The wrapper pins the audited base assembler `9963c942...`, fixed-v6 runner
`89c7c57a...`, backend `430d6376...`, and backend tests `a02f5137...`, in
addition to the complete base closure.  All 34 live pins matched.

An independent reconstruction of the runner's serialized source union from

```text
base.PINNED
v2.LOCAL_PINNED
v5.LOCAL_PINNED
v6.LOCAL_PINNED
```

has exactly 23 paths and equals `V6_SOURCE_HASHES` key-for-key and
hash-for-hash.  In particular, it includes the v5 runner as a dependency plus
the v6 backend and v6 tests; the v6 runner itself is separately checked as the
producer.  The snapshots passed into the base build include the strict D19
inner result and every path the base build indexes.

## Exact v6 parser checks

The wrapper derives the high/low branch sets at each count from the frozen
rational geometry, maps the union to the exact active families, and requires
the complementary inactive-family list.  It now validates the full
kernel/family schemas and identities and requires

```text
clear_stats.family_coefficients
= radial_stats.orbit_tag_associations
= sum(family_orbit_tag_entries[f] for active f).
```

It verifies the single factor-48 recombination, canonical rationals, exact
scaling/candidate/support/source metadata, and the v6 collection inventory.
For `n=47` it requires

```text
0 <= E <= 64,
factorial_ceiling = E+46,
D = 60^E (E+46)!,
radial_denominator | D,
reported gcd bits = bit_length(D/radial_denominator).
```

The `E<=64` and ceiling tests occur before exponentiation or factorial
evaluation.  A hostile `E=10^9, ceiling=10^9+46` fixture was checked while
replacing `factorial` by a function that raises on invocation; the parser
rejects without invoking it.

Synthetic r=0 data obtained from the already audited collected-v5 result
passes the v6 wire contract with `E=32`.  A separate r=12 fixture retains
exactly `small,small_total`, rejects `large`, and rejects mutations of either
the active coefficient count or radial association count.  Mutations of the
factor 48, source union, radial denominator, fixed ceiling, and pruning lists
all fail closed.

## Monkeypatch and projection path

The only runtime substitution is `B.parse_b_shard = parse_b_shard` around the
hash-pinned base `build`.  Independent success and forced-exception paths
confirm the original parser is restored by `finally`.  The fake build also
confirmed it receives the entire 34-file snapshot map, not a partial v6-only
map.

The inherited base build is byte-pinned to the separately audited exact
projection implementation.  It continues to compute

```text
margin = b^2-A D,
quotient_lower_bound-1 = margin/(A I+b^2),
```

with the exact `10^174`, `10^76`, and `10^125` form/vector scales.  The wrapper
changes only the b wire parser and result provenance; it does not change that
algebra.

## Reproduction

```bash
python3 verify/test_assemble_one_band_236_fixed_v6.py
python3 -O verify/test_assemble_one_band_236_fixed_v6.py
python3 agents/audit/test_assemble_one_band_236_fixed_v6_independent.py
python3 -O agents/audit/test_assemble_one_band_236_fixed_v6_independent.py
```

The production suite passes 2/2 under both interpreters.  The independent
suite passes 7/7 under both interpreters and has SHA-256

```text
314851c0ed2ca5dfb58d811165abb4a5479f0fa12735d760053f600c2e1c0864
```

## Remaining gate

Do not run the scalar aggregate until all thirteen fixed-v6 b shards exist and
each shard hash is bound to a `FIXED-V6 ... RESULT AUDIT PASS`.  A positive
aggregate still needs a standalone integration-reconstructing checker and the
analytic/tuple audits before it can imply `H_1<=236`.
