# Importance D4 calibration v5 hostile reaudit

## Verdict

**SCOPED AUDIT PASS (prelaunch discovery only).**  At the frozen bytes below, I
found no remaining false-accept in the D4 calibration gate, checkpoint protocol,
or final-result publication protocol.  This is not a sieve certificate, a
stochastic quotient, or permission to launch a production chain.  The gate
itself has `production_launch_authorized=false`.

## Frozen objects

| Object | SHA-256 |
|---|---|
| `agents/structural-basis/code/importance_d4_calibration.py` | `b0b4350ff1804530724c87b8693aa4dd0059904f3eb9d72696497fb3c90c1b41` |
| `agents/structural-basis/tests/test_importance_d4_calibration.py` | `f3439db90a057b94d8df031e07ab648020f5d76430b85b097973e80b7fe0399c` |
| `agents/structural-basis/IMPORTANCE-D4-CALIBRATION-SPEC.md` | `2de6acd05a8cb4b969368887efec8c721a939e9c33b84a1ed67e88581b7a7b48` |
| `agents/structural-basis/results/importance_d4_calibration_gate_v5.json` | `860a9a51284187388e2384b7ca19615dc7d17eb523a7a4fa4d5617e2e6f29196` |
| independent hostile suite (historical filename) | `8357fa78939819ee2a777ab963b5fc9234b02d8f83a32110df63488416de7773` |
| canonical v5 audit wrapper | `b5e4bc30479f9196367dcfaa9b0b7fff363d0dddd391cbdd31df74efca7e7ad5` |

The v5 gate rejects, in this exact order, all four invalid predecessors:

1. v1 `fcce4e339c9b7d23eb39bf74fe88f82592ea101fd0be1fea3c9691f760ed237c`;
2. v2 `0d52e2d0c730f01d459c20a3091f312edfec3ea86a253775b452de26fa5dcb03`;
3. v3 `2e2417e30ded2520a16a5778cb9d56833b17524fe92b51add5418bf1ae27e282`;
4. v4 `a2ca98514d0aa31463aaeca2d46baec400e8d4d54f9fc54e068b8684d235f8f6`.

## What was checked

### Mathematical and statistical conventions

- `k=48` and the exact C10 support parameters are bound by the gate.
- Features are exactly `(L/alpha)^a (Z/alpha)^b`, in the declared six-channel
  order.  The active dimensions are exactly 16, 47, and 93 in degrees 0, 1,
  and 2.
- The exact branch witness calculation gives a small J branch in all 16 common
  strata and a large branch only for strata 0 through 14.  It reconstructs 336
  I structural entries, 876 J structural entries, and exact active local-pair
  counts 321 and 1158.
- The only permitted analytic zero-standard-error entries are the 16
  per-stratum I constant diagonals and the *local* J entry `(r=15,0,0)`.
  Neighboring `(r=15,0,1)` and the aggregate global constant entry remain
  subject to the statistical gate.
- The D4 J stratum artifacts already use the `48J` numerator convention, so
  `j_scale_to_numerator=1`.  Exact base-form comparisons and a wrong-factor
  mutation test exclude both omitting and duplicating the factor 48.
- Raw and batch means/second moments, Jensen lower bounds, split-R-hat, ESS,
  bounded J-envelope observations, active-mask zero-SE failures, and finite
  resource/timing fields are checked before a result can pass.  Zero SE on an
  active non-whitelisted entry becomes a predeclared statistical failure.

### Provenance and publication

- Initial and extension record directories are fresh-only.  Authorization binds
  their canonical path and device/inode identity, performs the complete absence
  scan, and creates every checkpoint by `openat(..., O_EXCL)` through a held
  canonical directory descriptor.
- Extension input checkpoints must match the parent manifest and are reopened
  through the held initial-directory descriptor.
- Production and extension ancestor-symlink swaps cannot redirect checkpoint
  creation.  The hostile regression changes the raw alias after authorization;
  bytes are written under the already-held authorized directory, never the new
  alias target.
- Generic/final output publication independently resolves and holds its canonical
  parent directory, then uses only descriptor-relative creation and reopening.
  The invalid-v4 alias-swap witness now writes the intended A path, not B.
- Final publication rehashes the output through both the held output descriptor
  and a fresh `openat` through the held directory descriptor.  Dynamic input
  replacement, output-inode replacement, and a create-after-scan race all fail
  closed; a concurrently installed foreign inode is preserved.
- All held descriptors are registered for unconditional cleanup.

## Permanent counterexamples that motivated v5

- v1 could never pass its blanket positive-SE rule: at J common stratum 15 only
  the small branch exists, so the local constant observable equals the
  normalizer pointwise and has exactly zero variance despite nonzero mass.
- v3 validated a resolved record directory but created checkpoints using the
  raw CLI spelling.  Swapping an ancestor symlink after validation redirected
  an otherwise accepted write to a different directory.
- v4 repaired checkpoint paths but left the generic/final result writer with
  the same resolved-versus-raw ancestor race.  The explicit witness completed
  successfully with A absent and B populated.  V5 keeps and passes both races
  as regressions.

## Reproduction

```sh
cd /home/anish/code/prime-gap-236-ultra/prime-gap-236
python3 agents/small-delta-frontier/audit_importance_d4_calibration_v5.py
python3 -O agents/small-delta-frontier/audit_importance_d4_calibration_v5.py
```

Both modes pass 11/11 independent hostile tests.  The producer's calibration
suite passes 20/20 in each mode, and the complete importance suite passes 76/76
in each mode.  Normal and optimized tiny-smoke outputs agree after excluding
the deliberately nondeterministic wall-time and RSS fields.

## Scope and remaining trust boundary

- No 128-chain calibration, extension, stochastic matrix, generalized
  eigenvalue, or quotient was produced or accepted here.
- Moment consistency is not cryptographic authentication of a chain.  The
  fresh-only authorized directory, held-directory descriptors, O_EXCL creation,
  and closure rehashes are essential parts of the trust boundary.
- The audit checks the exact total/base forms and simultaneous D4 oracle
  coverage, but does not perform a new exact integration of every individual
  per-common-stratum J normalizer.  Those serialized Decimal decompositions
  remain byte-pinned discovery inputs.
- Any future calibration output requires an independent output audit.  Any
  resulting D12 candidate remains discovery-only until it is reevaluated by the
  exact or outward-rounded dyadic recurrence with a strict positive margin.

