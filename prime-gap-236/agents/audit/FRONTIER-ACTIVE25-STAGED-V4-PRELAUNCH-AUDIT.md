# Frontier active25 staged v4 hostile prelaunch audit

Verdict: **PRELAUNCH AUDIT FAIL.  Do not launch.**

The ordinary frozen suites pass 19/19 in normal and optimized mode, and the
honest-path v3 repairs (boot-bound cumulative deadline, subprocess timeout,
exact leaf-set checks, disjoint synthetic formats, held-directory assembly,
and one-time factor 48) are present.  A smaller production-authenticity
counterexample nevertheless bypasses the new runtime guard and produces a
complete production-format manifest accepted by the frozen assembler without
performing any exact shard computation.

## Frozen tuple attacked

- wrapper `agents/small-delta-frontier/frontier_active25_inner_d16_staged_v4.py`,
  SHA-256 `7d5188ec18ef99ae22aeada193471a69c11cf15363aa26496ef8b3217387beef`
- wrapper test, SHA-256
  `4082c32c1358d564f6ed17743c3ccdc471813c67df5a5a3013acd9aa1e227ac0`
- assembler `agents/small-delta-frontier/assemble_frontier_active25_inner_d16_v4.py`,
  SHA-256 `0b60c03e3743fe8003c9571423e79922a3ded08594d30894bee2461e980d0d85`
- assembler test, SHA-256
  `bb2a751b0459365641e188afc0f67fea27781e7a17a04538b5f35b3bae1140db`
- gate, SHA-256
  `2dcfb44e4c9fbc5ec5f9b030f6565a35b06af478dff60c0805f96b44078c35fe`
- spec, SHA-256
  `66b4b7de36aecd3a2b4ecbf2ea1cb5e6192c2590d24d8a61bb7bc76a327f2edb`

Neither intended target path was created or used.

## Smallest executable counterexample

`production_runtime_intact` binds the singleton runtime object and the five
class-method objects, but those methods dispatch through mutable module
globals `_REAL_MONOTONIC_NS`, `_REAL_SLEEP`, `_REAL_MEM_AVAILABLE_KIB`, and
`_REAL_SUPERVISE_COMMAND`.  The purported CLI-only test likewise reads the
mutable module globals `__name__`, `__spec__`, and `sys.argv`.

The independent checker imports the frozen wrapper, leaves the singleton and
all class methods unchanged, substitutes those private call targets, restores
the three mutable identity fields to their expected CLI values, and invokes
the public `run_all` closure.  The frozen integrity predicate remains true.
The call then emits:

- a production-format ledger using the real gate SHA;
- all 26 production-format stages and the exact allowed leaf set;
- a production-format manifest accepted by
  `assemble_frontier_active25_inner_d16_v4.load_completed_manifest`.

No `/proc/meminfo` read, real sleep, child subprocess, or target exact
arithmetic occurs.  Every fake shard contains the deliberately false
`inner_48J = 999`, yet the production assembler accepts all 26 because it
reconstructs the child-stdout hash from the same self-declared data rather
than independently recomputing the shard.  No pencil or quotient was built or
inspected in the attack.

This simultaneously falsifies the claims that imported production is
unreachable, that the live resource/subprocess evidence is authenticated,
and that assembler acceptance establishes exact-shard provenance.

## Related remaining holes

The same underlying issue survives across process resumes: the ledger has no
external immutable anchor, so a consistently replaced ledger/stage prefix can
become the new trusted state.  `read_leaf` also does not require link count
one; a record with an out-of-directory hardlink is not caught by the internal
inode-distinctness test.  Resource observations from different stages are not
required to be temporally ordered, so consistently forged observations can
all reuse one five-second interval.  These do not need separate attacks to
establish the FAIL, but a successor should test them explicitly.

The honest-path cumulative deadline is no longer reset on resume, a child is
actually killed/reaped by the ordinary supervisor timeout fixture, and exact
leaf sets are checked repeatedly.  Those repairs do not authenticate how an
accepted production record was created.

## Minimum repair

1. Make the only production entry a fresh isolated process that checks an
   externally supplied expected hash of its own driver before touching the
   record directory.  Do not dispatch production evidence through replaceable
   module-global call targets or mutable in-process identity tests.
2. Give the first ledger an external, durable trust-root binding that survives
   resume; reject full ledger/prefix replacement, stage injection, deletion,
   symlinks, and any link count other than one.
3. Enforce chronological non-overlap/order of all memory observations and
   supervised child intervals under the original boot-bound deadline.
4. Most importantly, the final certificate checker must independently
   reconstruct every shard from the frozen mathematical inputs.  Self-declared
   source fields and a manifest hash cannot authenticate arithmetic values.

## Frozen counterexample

- checker `agents/audit/verify_frontier_active25_v4_prelaunch_fail.py`,
  SHA-256 `b1da2c8bc980154751da868d67c543bf281d2892113e259c6bf67a9ed8217588`
- result `agents/audit/results/frontier_active25_v4_prelaunch_fail.json`,
  SHA-256 `f020711a107dd36f724561e00f7d2c3fb9e7eb801a4e4f24e6e547cba6d782f5`

Replay from `prime-gap-236/`:

```sh
python3 agents/audit/verify_frontier_active25_v4_prelaunch_fail.py
python3 -O agents/audit/verify_frontier_active25_v4_prelaunch_fail.py
```

Normal and optimized outputs are byte-identical at SHA-256
`f020711a107dd36f724561e00f7d2c3fb9e7eb801a4e4f24e6e547cba6d782f5`.
