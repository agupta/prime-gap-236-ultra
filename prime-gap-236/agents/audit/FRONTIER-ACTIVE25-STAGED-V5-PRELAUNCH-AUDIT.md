# Active25 D16 staged v5 prelaunch audit

Status: **PRELAUNCH FAIL**.  The frozen v5 coordinator must not be used for
the target traversal.

## Frozen inputs

- coordinator `frontier_active25_inner_d16_staged_v5.py`:
  `8bb0d5088e419d196b4aca732ec384804bf2918554cf001f372a3127e7f1f775`
- coordinator tests: `28b5b8d182fc0836a0bf905af4d7f9b907b403e35a9e61cae779428fb7f899bf`
- conditional assembler `assemble_frontier_active25_inner_d16_v5.py`:
  `6163402f5333c73ae011acbe64191ebff7dfac043f43d8e11c2ce635019807e9`
- assembler tests: `9d6a242a7e3b76d8cada75ee23f1ba24c7c100ff7a0d73de0d637e8166c09e74`
- v5 gate: `b814507140740a821d67b6ccdec65eda3c30985075a19505d8bc485c84fa2420`
- v5 specification: `ef365ff9031b7166df50dba71d484996d075574bf668dccef207bf18238daf07`

## Smallest failure mechanism

The external ledger SHA/device/inode is checked, but a preexisting stage
prefix and a preexisting manifest need no external bindings.  Their fields
are self-consistent but reproducible by any writer of the record directory.
The resume validator also checks only that recorded times lie inside the
ledger interval; it does not require persisted times to be no later than the
current live monotonic time.

The independent checker used an ordinary fresh isolated Python process and
the frozen coordinator bytes.  It:

1. initialized a genuine temporary production ledger through the documented
   `python3 -I` entry;
2. wrote 26 canonical stage records with `inner_48J = 999`, zero cross
   vectors, and fabricated ordered resource/child intervals, without running
   one shard integral;
3. wrote the corresponding canonical manifest; and
4. resumed through a second fresh `python3 -I` invocation with the genuine
   external ledger binding.

The frozen CLI exited zero and returned `resumed_complete: true`.  All 26
record hashes were unchanged, proving that no child calculation repaired the
data.  The accepted manifest's final timestamp was still in the future at
acceptance.  No intended v5 target directory or output was created.

This is within the agreed bounded fresh-process model: no Python interpreter
or standard-library replacement is involved.

## Independent artifacts and replay

- checker `verify_frontier_active25_v5_prelaunch_fail.py`:
  `127024d7117a130b21e4a93cb5f99ddbf59273e756802270feb52f0494c881a8`
- exact result `results/frontier_active25_v5_prelaunch_fail.json`:
  `a173658fa20ada39cf2ca78e98ea92601be6e3709db9674826512c9e3a76c875`

Run:

```text
python3 agents/audit/verify_frontier_active25_v5_prelaunch_fail.py
python3 -O agents/audit/verify_frontier_active25_v5_prelaunch_fail.py
```

Both modes emitted byte-identical results with SHA-256
`a173658fa20ada39cf2ca78e98ea92601be6e3709db9674826512c9e3a76c875`.
The producer's own 13 coordinator tests and seven assembler tests pass in
both modes, so its current regression suite does not cover this failure.

## Minimum repair

On every resume, require externally supplied SHA/device/inode bindings for
each preexisting stage and for any preexisting manifest.  Reject any persisted
resource, child, or final timestamp later than the current live monotonic
time.  A conditional assembler must continue to set
`independent_arithmetic_reconstruction=false` and `theorem_ready=false`; only
the separately designed one-shot checker may upgrade the arithmetic after it
has independently recomputed every shard integral.
