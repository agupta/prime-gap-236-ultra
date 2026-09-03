# Active25 staged v3 delta audit: PRELAUNCH FAIL

Date: 2026-09-03 (Europe/Berlin).

## Verdict

`PRELAUNCH AUDIT FAIL`.  Do not launch the v3 target traversal.

The exact arithmetic inherited from the scoped v2 pass is not challenged.
The new live-execution contract fails its advertised 14,400-second hard total
wall gate.

## Smallest counterexample

`run_all` sets `started = time.monotonic_ns()` anew on every invocation.  It
checks elapsed time only after a complete shard returns.  When an invocation
exceeds the gate, every shard already published by that invocation remains a
valid resumable leaf.  A later invocation obtains a fresh `started`, accepts
those leaves, and may publish a complete manifest.  Its
`wall_nanoseconds` records only the last invocation.

The independent pin-bound regression uses no target integration.  With a
deterministic clock it performs:

1. invocation one: elapsed `14,400,000,000,001 ns`; v3 rejects after writing
   `common_r_00.json`;
2. invocation two: resumes that shard and writes the other 25; v3 accepts a
   complete manifest recording only `27 ns`.

Thus a successful manifest can follow arbitrarily more than four hours of
aggregate traversal.  Separately, one individual shard has no enforceable
mid-shard deadline because elapsed time is examined only after its builder
returns.

Two additional live-contract weaknesses were reproduced:

- directory membership is scanned only before traversal.  A synthetic stage
  adds an unauthorized leaf after that scan; v3 still publishes a complete
  manifest, and `strict_manifest` accepts it because neither it nor the
  assembler requires the exact final leaf set;
- `run_all` publicly accepts replacement memory readers and sleepers.  A
  manifest made with invented high readings and zero delay is
  indistinguishable from one made by the CLI defaults.  The intended CLI does
  call `time.sleep(5)`, but neither actual read timestamps nor their separation
  are bound into the manifest.

The O_EXCL writes and inode rebindings themselves failed closed in the cases
inspected; the defects are the temporal/directory contracts around them.

## Required repair

Use a new versioned gate/driver.  At minimum, the authorization must account
durably for elapsed work across every resume and must reject/retire a record
directory once the cumulative limit is exceeded.  Each validated existing
stage's recorded duration must enter that cumulative accounting, including a
strict manifest identity.  If “hard stop” is retained literally, enforce the
remaining deadline around each shard (for example in a supervised subprocess
with a timeout); a post-return comparison is not a hard stop.

Also require the exact allowed leaf set immediately before and during
assembly, and bind measured monotonic timestamps for the two real memory
reads.  Production entry points must not expose unrecorded reader/sleeper
substitution.

Re-audit memory timing, immutable dirfd publication, manifest completeness,
and the assembler after this material change.  Preserve v3 bytes and do not
reinterpret this as an arithmetic failure.

## Reproduction

From `prime-gap-236/`:

```bash
python3 agents/audit/test_frontier_active25_v3_resume_wall_bypass.py
python3 -O agents/audit/test_frontier_active25_v3_resume_wall_bypass.py
```

Both commands print the same `PRELAUNCH AUDIT FAIL` counterexample and run no
real target integration.
