# Fixed-polygon-v8 `R<=9` assembler hostile audit

## Verdict and scope

**PRE-CERTIFICATE AUDIT PASS for the frozen aggregation wrapper.**  The
audited source is

```text
verify/assemble_one_band_236_fixed_polygon_v8_r09.py
67c479a18b12f7e5d4df84a854dd8364f981ecdbcfd2daf2fd256edb2029b557
```

with production test

```text
verify/test_assemble_one_band_236_fixed_polygon_v8_r09.py
6efe3b8a8db114e7d20834c922e514ec018c577029149598cdb5ce0b22f55a76
```

and independent hostile test

```text
agents/audit/test_assemble_one_band_236_fixed_polygon_v8_r09_independent.py
0c385ac63e285723de5fe72f5b9b601a4886c8771552a19f63ef9ca108028f06
```

This verdict establishes only the exact wrapper, immutable-byte parser,
`R<=9` branch projection, dependency closure, and aggregation handoff.  It
does not replay polygon integration, certify any future shard, establish a
positive scalar margin, or imply the prime-gap theorem.

## Mathematical projection checked independently

For the 47 shared coordinates let `r` be their count strictly above
`delta`, and let `t` be the distinguished outer coordinate.  The proposed
symmetric direction is

```text
H_9(u,t) = 1_{r + 1_{t>delta} <= 9} H_full(u,t).
```

Thus all small- and large-distinguished branches survive for common counts
`r=0,...,8`; at `r=9` only the small-distinguished branches `Sdelta` and
`Stotal` survive; all `r>=10` mixed contributions vanish.  The diagonal
outer norm retains total-large-count shards `0,...,9` and explicitly zeroes
`10,11,12`.  The endpoint `t=delta` belongs to the small side in Definition
1 and is also a null boundary.

At `r=9`, the exact selected mixed shard is therefore

```text
48 * ((high.Sdelta + high.Stotal)
      - (low.Sdelta + low.Stotal)).
```

The independent suite assigned unrelated rational values to all eight
endpoint/branch fields, repaired the full factor-48 identity, and recovered
this formula exactly.  Arbitrarily large `Ltotal`/`Lbig` changes affected the
audited full shard but not the selected `r=9` value.  Counts `0..8` continue
to use the full audited shard.  This agrees with the separate independent
audit of the pinned cached-v7 `R<=9` base assembler.

## Wrapper and byte-binding evidence

- The wrapper loads the exact `aaa3dc...` `R<=9` assembler and replaces only
  its full mixed-shard parser during the synchronous build call.
- `parse_b_v8` copies the supplied byte string to a private temporary file
  and sends that snapshot to checker `ec0162...`; it never trusts a second
  read of the supplied pathname.  A hostile test left malformed bytes at the
  live name while passing a valid snapshot and recovered exactly the value
  in the snapshot.
- The v8 checker must return the exact count and input-byte SHA, exact
  factor-48 recombination, fixed radial denominator/cache facts, pinned
  polygon denominator proof, and full source closure.  A reference comparison
  is forbidden in this aggregation path rather than silently trusted.
- The original parser is restored in a `finally` block.  Independent tests
  forced both an arithmetic exception and a dependency mutation during the
  wrapped build and verified restoration; the latter failed before output
  publication.
- `PINS` contains the complete pinned `R<=9` base closure plus the v8 runner,
  v8 checker and its transitive 29-entry source map.  All 49 unique live
  paths matched their expected SHA-256 during this audit.  They are snapshotted
  before the build and rechecked byte-for-byte afterward.
- Output rows retain hashes of the precise A and b snapshots used by the
  base algebra.  The wrapper replaces the format/engine provenance and emits
  the complete 49-entry source map.  The inherited publisher is exclusive
  and cannot overwrite an existing result.
- The wrapper has no `assert`, floating-point arithmetic, `eval`, or `exec`.
  Explicit exceptions remain active under `python -O`.

As an aggregation program used alone, the wrapper intentionally does not
claim to reintegrate shards.  In the full replay, its row hashes must be
compared with the independently audited producer bytes; that binding is a
separate standalone-checker obligation.

## Test evidence

The production suite passed `3/3` in normal and optimized modes.  The
independent suite passed `6/6` in both modes.  It covers the 49-file flat
closure, supplied-byte versus live-name behavior, exact `r=9` projection,
factor 48 and high-minus-low orientation, parser restoration on success and
failure, source mutation before publication, and optimization-safe control
flow.

```bash
cd prime-gap-236
python3 -B -I -X pycache_prefix=/tmp/v8-r09-prod-normal \
  verify/test_assemble_one_band_236_fixed_polygon_v8_r09.py
python3 -B -O -I -X pycache_prefix=/tmp/v8-r09-prod-opt \
  verify/test_assemble_one_band_236_fixed_polygon_v8_r09.py
python3 -B -I -X pycache_prefix=/tmp/v8-r09-audit-normal \
  agents/audit/test_assemble_one_band_236_fixed_polygon_v8_r09_independent.py
python3 -B -O -I -X pycache_prefix=/tmp/v8-r09-audit-opt \
  agents/audit/test_assemble_one_band_236_fixed_polygon_v8_r09_independent.py
```

## Remaining gate

No fixed-polygon-v8 target shard, aggregate, or compact certificate was
available for this audit.  Every future shard requires a fresh result-level
audit, and the complete replay must bind aggregate hashes to the independently
audited shard bytes and reconstruct the exact scalar inequality.  This report
must not be cited as evidence that those later gates passed.
