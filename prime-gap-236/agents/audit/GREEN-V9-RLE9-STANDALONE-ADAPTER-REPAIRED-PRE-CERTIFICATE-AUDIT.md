# Repaired Green-v9 `R<=9` standalone-adapter audit

Verdict: **PRE-CERTIFICATE AUDIT PASS**, scoped to adapter

```text
verify/check_H1_236_Rle9_green_v9.py
ef26a71fee7ee60f1c3b9e6e0ea227649fe70c45ae5d8d47f5da8f597b4045c5
```

Its production test has SHA-256
`72f4b78be5bdc089184a460b77cd969cad98d1658136b1f38530fc83fa16f2a9`.
Independent test
`agents/audit/test_check_H1_236_Rle9_green_v9_independent.py` has SHA-256
`057f61e4c7bcdf1600d2fe8a19a26f99493613155368a9e1526d902d0926bf12`.

This is a thin-adapter/source-control verdict.  No full replay was run, no
compact certificate exists, and this report establishes no aggregate, sign,
quotient, final certificate audit, or theorem.

## Superseded failure and repairs

Adapter `dace7747...` has a permanent **AUDIT FAIL** in
`GREEN-V9-RLE9-STANDALONE-ADAPTER-AUDIT-FAIL.md`: it removed a fixed-v8
assembler that its pinned base imported during startup, and its audit-wire
adapter accepted Boolean `common_r=true` as count 1.  Repaired `ef26a71f...`
does not inherit any verdict from that snapshot.

The repaired 74-entry PINS set retains the startup-read old assembler

```text
verify/assemble_one_band_236_fixed_polygon_v8_r09.py
67c479a18b12f7e5d4df84a854dd8364f981ecdbcfd2daf2fd256edb2029b557
```

while replacing the actual mixed producer, result checker, and aggregator
with the frozen Green stack.  It also inherits repaired Green aggregator
`4762573e...`, whose flat closure includes the separately live-read fixed-v8
producer `36a8e027...`.  Every one of the 74 live pins matched.  A fresh
read trace around adapter import found no explicit repository read outside
`PINS union {adapter FILE}`; it specifically observed the retained old
assembler.

## Audit-wire translation

The frozen base replay invokes its mixed result checker without a reference
and parses the child output at the sole internal label
`b audit stdout r=<count>`.  Only that label family is routed through the
Green adapter; tuple and other strict loads remain byte-for-byte on the
original parser.

Before changing a backend name, the repair now requires the exact 16-key
Green result-audit schema and validates:

- exact integer `common_r` in `0..9`, not a Boolean or float;
- exact integer `maximum_active_shift=14-common_r`;
- active families exactly `large,small,small_total`;
- lowercase 64-hex input hash and canonical rational shard value;
- strictly positive exact-integer work counters;
- exact truth of recombination, fixed-denominator, cache, Green-denominator,
  convexity, and source-closure gates;
- both optional reference fields exactly null.

Only then does it deep-copy the record, change the status name, and rename
`green_boundary_denominator_proof_pinned` to the fixed-v8 proof field expected
by the already-audited generic base.  The independent suite deletes every
schema key in turn and attacks extra keys, Boolean/float counts, count bounds,
shift, family order, hash syntax, reduced-rational syntax, work-counter
types/signs, reference fields, and all proof flags.  Every mutant fails, and
the source object remains unchanged.

## Mathematical and certificate adapter

The adapter changes no raw-shard reconstruction.  The frozen base still
reparses the startup-bound A/b shard byte dictionary, independently selects
only `Sdelta,Stotal` at r9, forms every exact scalar, binds fresh aggregate
row hashes to those same bytes, and demands strict positivity.

For the compact-certificate comparison, the adapter first requires both the
certificate and fresh aggregate to identify the exact Green format and
engine.  It deep-copies them, changes only those two backend-name fields, and
calls the complete pinned base comparison.  An independent positive exact
synthetic reconstruction with all 13 A and 10 b byte snapshots passed this
actual base comparator.  Mutations of Green format, engine, assembler hash,
and an exact scalar all failed; input objects were not modified.  Thus no v8
mathematical assumption is substituted for Green output—the shared exact
fields are checked by the base after the two provenance-name translations.

The adapter rewires precisely `FILE`, `PINS`, the Green assembler/producer/
result-checker paths, default certificate, strict audit loader, and
certificate comparator in the isolated CLI process.  A fail-fast test uses
the real self hash and all 74 live pins, then supplies a wrong certificate
hash and proves rejection before any heavy stage can run.

## Test evidence

Production tests passed `3/3` in normal and optimized Python.  Independent
tests passed `6/6` in both modes.  Both used `-B -I` and distinct private
bytecode prefixes.  The independent suites cover flat closure and startup
reads, exact runtime rewiring, exhaustive audit-field mutations, loader
scope, a complete synthetic certificate comparison, and pre-stage fail-fast
behavior.

The remaining requirement is the actual full replay against a separately
hash-pinned compact certificate after every required Green shard exists and
has an output-specific audit.  This report must not be cited as that result.
