# Green-v9 `R<=9` assembler hostile audit

> **SUPERSEDED AND RETRACTED.**  The reviewed SHA `614d2212...` omitted
> `GREEN.V8.PRODUCER` from its flat runtime pin set even though the nested v8
> audit live-read that producer.  The former PASS is withdrawn.  This file is
> retained only as the historical audit record; repaired SHA `4762573e...`
> is reviewed separately in
> `GREEN-V9-RLE9-ASSEMBLER-REPAIRED-PRE-CERTIFICATE-AUDIT.md`.

## Verdict and scope

**RETRACTED — NO VERDICT** for the superseded aggregation wrapper

```text
verify/assemble_one_band_236_green_v9_r09.py
614d2212d057954a8aa226f0025f2e71e352ee5b0ede098aae400a66af33efa4
```

with production test

```text
verify/test_assemble_one_band_236_green_v9_r09.py
3dfc7afc7bafd20daa94e8a43d0d8e27e1a06ebce86a6777a8a8bd57c12c1300
```

and independent hostile test

```text
agents/audit/test_assemble_one_band_236_green_v9_r09_independent.py
422fec6edd5c2d1f320071be050c67f23c75ed4e7f14142fe1ef5d1418326931
```

The two earlier snapshots `a1ae50a9...` and `e668174e...` are superseded
and receive no verdict.  The final snapshot adds the normalized-v8 checker
and both the Green and normalized-v8 source maps to its flat byte-rechecked
closure.

This verdict covers only wrapper identity, exact `R<=9` projection,
audited-byte parsing, count inventory, parser restoration, source closure,
and aggregation handoff.  It is not an integration replay, target aggregate,
positive scalar certificate, final certificate audit, or theorem claim.

## Independent mathematical check

Let `r` count the 47 shared coordinates strictly above `delta`, and let `t`
be the distinguished coordinate.  For

```text
H_9(u,t) = 1_{r + 1_{t>delta} <= 9} H_full(u,t),
```

all distinguished-coordinate branches survive for `r=0,...,8`.  At `r=9`
the large-distinguished branches have total count 10 and vanish, while the
small-distinguished branches have total count 9 and survive.  Consequently
the exact selected r9 contribution is

```text
48 * (high.Sdelta + high.Stotal
      - low.Sdelta - low.Stotal).
```

All mixed common counts `r>=10` vanish.  The diagonal outer norm selects
total-count A shards `0,...,9` and records `10,11,12` as zeroed.  The
independent suite assigns unrelated exact rationals to all eight r9 branch
values, repairs the full-shard identity, and recovers this selected formula
exactly.  It separately checks that counts 0 and 8 pass through the complete
audited Green shard.  Thus neither the factor 48, high-minus-low orientation,
nor the large/small distinguished-coordinate distinction is inherited merely
from a serialized selected value.

## Byte binding and checker cascade

- `parse_b_green(path,data,count)` writes the supplied `data` bytes to a
  private temporary snapshot and audits that snapshot with Green checker
  `7dbb3520...`; it never rereads `path`.  A hostile test leaves malformed
  data at the live path while supplying a valid snapshot and obtains exactly
  the supplied snapshot's rational value.
- The Green checker must bind its `input_sha256` to those bytes, check the
  exact count and factor-48 branch recombination, validate fixed radial/cache
  metadata and Green denominator/convexity contracts, and return a complete
  source-closure pass.  The wrapper forbids an optional reference comparison
  in this path rather than trusting an external reference bit.
- The Green checker normalizes into fixed-polygon v8 and invokes the v8
  checker live.  The wrapper's 53-entry flat `PINS` set now includes the
  Green checker, its v8 checker dependency, all 30 Green source-map entries,
  all 29 normalized-v8 source-map entries, and the complete 43-entry base
  `R<=9` closure, with overlaps required to carry identical hashes.  All 53
  distinct live paths matched during both independent modes.
- Every dependency byte string is snapshotted before the synchronous build
  and compared byte for byte afterward.  A test mutates a pinned dependency
  inside the build and proves failure before publication.  The exact A and b
  rows themselves retain hashes of the same byte strings used for parsing and
  arithmetic.
- The base directory gate requires precisely `common_r_00.json` through
  `common_r_09.json`; missing, extra, and symlinked expected entries all fail.
  The base assembler separately requires and audits all 13 A shards before
  selecting the ten nonzero counts.
- The temporary replacement of the base mixed-shard parser is enclosed in
  `try/finally`.  Forced source mutation and arithmetic failure both restore
  the original parser.  External processes have separate module state.
- The inherited publisher uses exclusive creation.  An independent sentinel
  test confirms that a preexisting output remains byte-identical.

No Python `assert`, `eval`, `exec`, floating-point branch decision, or
serialized matrix occurs in the wrapper.  Its explicit checks remain active
under optimized Python.

## Executed tests

The final production suite passed `3/3` normally and under `-O`.  The
independent suite passed `6/6` in both modes:

```text
python3 -B -I -X pycache_prefix=/tmp/green-r09-prod-final-normal verify/test_assemble_one_band_236_green_v9_r09.py
python3 -O -B -I -X pycache_prefix=/tmp/green-r09-prod-final-opt verify/test_assemble_one_band_236_green_v9_r09.py
python3 -B -I -X pycache_prefix=/tmp/green-r09-independent-normal agents/audit/test_assemble_one_band_236_green_v9_r09_independent.py
python3 -O -B -I -X pycache_prefix=/tmp/green-r09-independent-opt agents/audit/test_assemble_one_band_236_green_v9_r09_independent.py
```

The two production modes produced the same synthetic aggregate digest
`a0cf4ec52c5005516098b2ba442a4840170ccf9f7a71af20cd5ba407f98c93c5`.

## Remaining gate

The wrapper cannot run to a theorem-facing result until every required Green
mixed shard exists and passes a fresh result-level audit.  A future aggregate
must then be independently reconstructed from startup-bound shard bytes and
compared with the compact certificate.  This report supplies none of those
later facts.
