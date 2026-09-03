# `R<=9` standalone replay hostile pre-certificate audit

## Verdict and exact scope

**PRE-CERTIFICATE AUDIT PASS** for the frozen standalone replay source

```text
verify/check_H1_236_Rle9.py
4179aeda84fef4d6712e62e7b02c0738bd277e69cb0e8d71f81de77863e324cb
```

after repair of the retired `81a121...` snapshot's audited-shard TOCTOU
defect.  The independent repair regression is

```text
agents/audit/test_check_H1_236_Rle9_bound_bytes_independent.py
a6193f4462642ab45c421252cbe178e604af734567b4bd8a23d5be6e0bb9c90d
```

and passes `3/3` in normal and optimized modes.

No compact certificate and no complete set of v8 target shards existed at
this audit.  Consequently this is a source/control-flow verdict only.  It
does not certify a numerical sign, quotient, or theorem.

## Repaired byte binding

The retired source independently audited each A and b pathname, but later
reread those live names for scalar reconstruction.  A race could substitute
internally consistent shards for aggregation and reconstruction, then
restore the audited names for the final pathname check.  The compact
certificate intentionally does not bind nondeterministic whole-shard hashes,
so that was a real false-pass route.

The frozen repair instead records the exact bytes accepted by each
independent result audit in one `bound_shards` dictionary.  The exact scalar
reconstructor now:

1. requires its dictionary keys to equal exactly all 13 A and 10 b paths;
2. parses canonical JSON only from the dictionary values;
3. computes all row hashes directly from those values; and
4. never reads a shard pathname.

The fresh aggregate's 23 row hashes are then compared to those independently
audited byte hashes.  Live names are still checked before and after the
assembler as defense in depth, but correctness no longer depends on winning
a pathname race.

The independent regression snapshots synthetic exact shards, replaces a live
A name and a live b name with different valid canonical records, and proves
that every reconstructed value and hash remains the audited original.  It
then checks that changing either a fresh aggregate A hash or its `r=9` b hash
is rejected.  An extra audited-byte dictionary entry is rejected as well.

## Replay and proof-control audit

- The source is externally self-pinned, the compact certificate is externally
  hash-pinned, and 66 replay/runtime dependencies are snapshotted and checked
  before work and again after all comparisons.
- Every child is invoked with `-B -I` and an absent private
  `pycache_prefix`; optimized parent mode is propagated explicitly.  There is
  no repository bytecode input path.
- Fresh analytic support is compared in every deterministic mathematical and
  source field with the frozen exact support result.  The only stripped
  fields are already type- and value-validated host device/inode identities.
- The tuple checker must report exactly size 48, minimum 0, maximum 236,
  diameter 236, the pinned tuple-data hash, and a successful admissibility
  verification.
- The D19 inner forms are regenerated and required to equal the frozen
  canonical result byte-for-byte.  Their exact `I`, `48J`, and positive
  deficit relation is independently reparsed.
- All 13 A shards are regenerated, passed together through the independent
  radial replay, and individually hash-bound to that replay.  Its full A sum
  is independently compared with the exact sum parsed from audited bytes.
- Mixed shards are generated only for common counts `0..9`.  Every v8 result
  is passed through the externally pinned structural/result checker and
  bound through its `input_sha256`.  Progress stderr must consist of exactly
  the three anchored producer lines; warnings or extra output fail.
- The standalone reconstruction independently applies the total-large-count
  rule: A counts `0..9`, full b branches for common `r=0..8`, and exactly
  `48*((high.Sdelta+high.Stotal)-(low.Sdelta+low.Stotal))` at `r=9`.
- It recomputes `A`, `b`, scaled inner `I,D`, `b^2-A D`, the mixing
  coefficient, normalized energies, and the exact quotient.  Both the fresh
  aggregate and compact certificate must match every exact canonical
  rational; only the fresh aggregate hashes are required to match the fresh
  nondeterministic shard bytes.
- Aggregate and compact schemas are exact, counts use exact `int` types (not
  booleans or floats), all hashes use lowercase 64-hex syntax, and the fixed
  format, engine, assembler chain, `k=48`, scales, direction, source map, and
  theorem-ready status must agree.
- A pass requires both `b^2-A D>0` and the reconstructed quotient strictly
  above one.  No positive-definiteness or matrix-invertibility assumption is
  used.

The source contains no Python `assert`, floating-point arithmetic, pickle,
`eval`, `exec`, shell command, or mutable serialized matrix input.  Normal
and optimized imports yield the same 66-pin and count inventories.

## Reproduction

```bash
cd prime-gap-236
python3 -B -I -X pycache_prefix=/tmp/rle9-driver-audit-normal \
  agents/audit/test_check_H1_236_Rle9_bound_bytes_independent.py
python3 -B -O -I -X pycache_prefix=/tmp/rle9-driver-audit-opt \
  agents/audit/test_check_H1_236_Rle9_bound_bytes_independent.py
```

The full replay command cannot be stated until an externally hash-pinned
compact certificate exists.  Its eventual result requires a fresh audit of
every generated v8 shard and of the complete final output; this source PASS
cannot be inherited as a result-level or theorem verdict.
