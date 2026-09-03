# Repaired Green-v9 `R<=9` assembler hostile audit

Verdict: **PRE-CERTIFICATE AUDIT PASS**, scoped to repaired wrapper

```text
verify/assemble_one_band_236_green_v9_r09.py
4762573e5f699f2641bb0081f571a3c34f23b47d70386f49626f9af1eef2de29
```

Production test SHA-256 is
`3dfc7afc7bafd20daa94e8a43d0d8e27e1a06ebce86a6777a8a8bd57c12c1300`.
Independent test
`agents/audit/test_assemble_one_band_236_green_v9_r09_independent.py`
has SHA-256
`a657358dfa1d1703c2f03ca5c916347c134715b44db40cc164f9d365dc465423`.

This pass supersedes and does not inherit the retracted SHA `614d2212...`
verdict.  It is an aggregation-wrapper audit only—not an integration replay,
target aggregate, sign, compact certificate, final certificate audit, or
theorem claim.

## Repaired closure

The nested Green checker converts a shard to the fixed-polygon-v8 contract
and invokes `V8.audit`.  In addition to the v8 source map, that audit
live-hashes its producer separately.  SHA `614d2212...` omitted that producer
from the wrapper's flat PINS, so its PASS was retracted.  Repaired SHA
`4762573e...` explicitly adds

```text
agents/exact-projection-engine/d14_grid38_scaled_b_shard_fixed_polygon_v8.py
36a8e027c83cabb272aa28a5d542dc571793cbcf90c5ca48787bc20092a55b72
```

The resulting flat set has 54 distinct paths.  It contains the entire base
`R<=9` closure, Green runner and checker, normalized-v8 checker, both the
30-entry Green and 29-entry normalized-v8 source maps, and the separately
live-read v8 producer.  Overlapping entries must agree in SHA.  Every live
path matched.

An independent read-recorder wrapped `Path.read_bytes` around an actual
synthetic Green shard audit through the complete Green-to-v8-to-v7-to-v6
checker cascade.  Every repository path read by that recursive audit was a
member of the repaired flat pin set.  A dependency mutation during the build
still fails before publication, and every pinned byte snapshot is compared
again after the synchronous build.

## Exact projection and byte binding

For shared-coordinate large count `r`, the symmetric direction is

```text
H_9(u,t)=1_{r+1_{t>delta}<=9} H_full(u,t).
```

Counts `r=0..8` therefore retain the full exact audited mixed shard.  At
`r=9`, only the small-distinguished branches survive, giving exactly

```text
48*(high.Sdelta + high.Stotal - low.Sdelta - low.Stotal).
```

Common counts `r>=10` vanish.  The A side selects total counts `0..9` only
after validating all 13 base A shards.  The independent suite verifies this
formula with unrelated rational branch values, including the single factor
48 and high-minus-low orientation, and checks full pass-through at r0 and
r8.

The mixed directory must contain exactly `common_r_00.json` through
`common_r_09.json`; missing, extra, and symlinked expected files fail.  The
Green parser audits the supplied byte string in a private temporary snapshot,
binds the returned input SHA and exact count, and never rereads the caller's
pathname.  The original base parser is restored on success and on forced
failure.  Exclusive publication preserves an existing sentinel byte for
byte.

## Test evidence

The final production tests passed `3/3` in normal and optimized Python.  The
independent suite passed `7/7` in both modes, covering closure, recursive live
reads, byte-versus-path binding, count projection, directory inventory,
parser restoration, dependency TOCTOU, exclusive publication, and
optimization-safe explicit checks.  The production synthetic aggregate
digest was identical in both modes:

```text
c7e30685cf2fc39e9d7717efac4d0d65b4fe1f4fc57c47ccf5a2f974cb4ab688
```

No target aggregate or certificate was consumed or created by this audit.
