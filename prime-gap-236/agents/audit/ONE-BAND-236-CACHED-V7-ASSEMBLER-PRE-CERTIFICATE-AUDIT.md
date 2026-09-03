# Cached-v7 one-band scalar assembler hostile audit

## Verdict

**SCOPED PRE-CERTIFICATE AUDIT PASS** for:

```text
verify/assemble_one_band_236_cached_v7.py
08fb7e612f37050a21bc94d27e4b8ed0ad1838f64ce5e2a147d15aef9f076f05

verify/test_assemble_one_band_236_cached_v7.py
aa0fb99375561786311e20f23312e48e486e9359d24fff8b93ed49ae3acf96a0

agents/audit/test_assemble_one_band_236_cached_v7_independent.py
ab0bab5edafeccfeba4ee003cb1706f14ad5de4661eaefaf51edf5f895f27929
```

This is an aggregation/provenance verdict only.  No target cached-v7 shard or
positive aggregate certificate was available, and this assembler does not
independently integrate Definition 5.  It therefore proves no prime-gap
theorem by itself.

## Exact reduction

The wrapper imports the frozen fixed-v6 assembler
`91ab96385d32921c035bd5537a56e8254455a8033bf41e2298b7ec13be552bbc`.
It changes only the b-shard parser.  For each exact byte string read once by
the base assembler, the replacement parser:

1. copies those bytes to a private temporary regular file;
2. calls the pinned cached-v7 result checker
   `80ec3329215f66e784708039f9a1d673d7064769c48a31825961dc44f6ae7343`;
3. requires the exact count, input SHA, recombination, fixed-denominator,
   cache-semantics, and source-closure PASS fields; and
4. parses the returned `scaled_b_shard` as a canonical rational.

The v7 checker validates the complete v7 schema and cache inventories, strips
only its two diagnostic cache counters and radial timing label, and submits
the resulting exact object to the independent fixed-v6 result checker.  Thus
factor 48, `H=14-r`, branch sets, active families, scales, fixed denominator,
and all exact branch values are checked before the scalar reaches the
assembler.

The inherited base then requires exactly the 13 regular filenames
`common_r_00.json` through `common_r_12.json`, reads each once, hashes the same
bytes supplied to the parser, sums their exact values, and performs the
already-audited projection algebra.  The temporary parser monkeypatch is
restored in a `finally` block on both success and failure.

## Source and byte closure

The 42-entry pin union contains the v6/base assemblers, A producer and exact
integrators, inner form audit/result, all v7/v6/v5/v3/v2/base cross runners and
backends, their production tests, every candidate/support input inherited
through the v7 result checker, and the complete v6/v5/v3 result-checker runtime
chain (SHAs `46a8...`, `11e2...`, and `0abb...`).  Conflicting duplicate pins
are rejected at import.  Main snapshots every pinned byte string, passes that
snapshot map to the base build, and rechecks all bytes plus its own source
after assembly.  The aggregate records the complete relative-path hash map.

The independent test changes the named shard after taking its byte snapshot;
the parser still audits exactly the supplied original bytes.  It also injects
success and failure base builds to verify snapshot passage, v7 parser
installation, parser restoration, output identity, and full source-map
serialization.  Missing, extra, and noncanonical shard filenames fail.

As with the full replay audit, strict executed-code closure requires launching
under an empty redirected bytecode-cache path; the final replay driver does
this automatically.  The standalone reproduction commands below state the
equivalent explicit invocation rather than relying on ordinary unpinned
`__pycache__` contents.

## Mutation coverage

The production suite passes 3/3 in normal and optimized mode.  The independent
suite passes 3/3 in both modes and rejects wrong counts and types,
noncanonical JSON, factor-48 changes, impossible cache inventories, source-pin
changes, incomplete filename inventories, and monkeypatch leakage.

```bash
python3 -B -I -X pycache_prefix=/tmp/h1-v7-assembler-audit-normal \
  agents/audit/test_assemble_one_band_236_cached_v7_independent.py
python3 -B -O -I -X pycache_prefix=/tmp/h1-v7-assembler-audit-opt \
  agents/audit/test_assemble_one_band_236_cached_v7_independent.py
python3 verify/test_assemble_one_band_236_cached_v7.py
python3 -O verify/test_assemble_one_band_236_cached_v7.py
```

Any target result, aggregate certificate, or future replay driver needs a
fresh result-level audit; this scoped source/aggregation PASS cannot be
inherited as a theorem verdict.
