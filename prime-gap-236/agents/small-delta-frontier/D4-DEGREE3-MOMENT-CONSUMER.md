# D4 degree-three moment consumer prelaunch

Status: **PREPARED AND TESTED; NO DEGREE-THREE RESULT OPENED; NO
INTEGRATION LAUNCHED**.

`consume_stratum_moment_d4_degree3.py` is a read-only future-result checker.
It has no production mode and no output-file option.  Its only result input is
required explicitly together with the caller's lowercase SHA-256.  The caller
must also pin the consumer's own bytes.  Self is verified before any result
access; both self and result must remain stable regular files through final
closure.

## Frozen acceptance policy

The machine-readable policy is
`results/c10_D4_degree3_moment_consumer_gate.json`, SHA-256
`a1ab82c3f5f4805c3f3c2506baa00295caf884f94200da290bb906f74e4b0ed3`.
It was refrozen without opening a degree-three result.

| frozen artifact | SHA-256 |
|---|---|
| `consume_stratum_moment_d4_degree3.py` | `fedf1970b197af825675fa62644aa227875487453d125ad454d213ebcdedfb7c` |
| `test_consume_stratum_moment_d4_degree3.py` | `421f5630ade4077282c96646542a058202d0659962b065ec74093e56e6c6c749` |
| consumer policy gate | `a1ab82c3f5f4805c3f3c2506baa00295caf884f94200da290bb906f74e4b0ed3` |
| fixed authorization | `8bf587b2ee0c0ff27c99d18446802b7be3007c17651cf4aa6c573b1745445c89` |

- Producer status, provenance, the byte-pinned authorization `8bf587b2...`,
  exact traversal/work counts, and the original
  1,800 s fused / 3,600 s total / 262,144 KiB resource limits must pass.
  The consumer cannot change or relax those limits after seeing timing.
- Canonically ordered exact I rows must contain all 448 `(R,u,v)` moments.
  Producer `expected_counts` contains the matrix dimension plus six
  integration/traversal work counters, not serialized-row cardinalities.
- The complete J matrix-query inventory is independently enumerated over all
  160 labels/classes: 10,980 tags, canonical-inventory SHA
  `746de1d75e0deee16c7e15380e1b912dbe36c6de215e1e45844cec1ceea7fa92`.
  Every serialized J row must be a valid, canonically ordered member, with no
  duplicates and exact mirror symmetry.  The serialization is sparse: an
  omitted queried tag is interpreted as zero when reconstructing the matrix.
- Both 160 by 160 matrices are rebuilt from the dense I and sparse J rows.
  The serialized matrix hashes are checked only afterward as secondary
  equality checks.
- Every entry of the embedded 96 by 96 degree-two principal pencil and its
  frozen rational-vector contraction must equal the byte-pinned exact D2
  reference.
- Per-R exact incremental LDL selection, in canonical channel order, must
  have rank 154.  Exactly the six `R=0` channels containing `L` are discarded:
  `L,L^2,LZ,L^3,L^2Z,LZ^2`.  A zero Schur complement is accepted only after
  its complete A and B columns satisfy the same exact dependence; a negative
  complement is rejected.
- The reduced pencil is solved at exactly 120 and 200 decimal digits.  The
  relative quotient disagreement must be at most `1e-85`; relative residuals
  must be at most `1e-105` and `1e-185`, respectively.
- Rationalization is skipped unless **both** accepted numerical quotients are
  strictly greater than one.  If enabled, the 200-digit vector is normalized
  with the first maximum-magnitude coordinate positive, rounded half-even to
  the `10^-80` grid, expanded with exact zeros on discarded coordinates, and
  contracted against the exact reconstructed matrices.  Only exact
  `N > D > 0` opens the continuation gate.

The numerical eigenvalue is a discovery aid, not a rigorous spectral bound.
Only reconstruction, rank/dependence identities, the D2 replay, and a
conditional rational-vector contraction are exact claims.

As a non-D3 calibration, the independently checked D2 pencil completed its
120-digit solve in 41.93 s / 32.7 MiB with 25,935 rotations and relative
residual `3.68256e-111`; this confirms that the frozen `1e-105` low-precision
gate is attainable.  It does not predict or relax the D3 gate.

## Trust boundary

The consumer imports only Python standard-library arithmetic.  It imports no
producer, moment-table, integrator, or existing solver module.  The channel
order and I/J assembly formulas are independently implemented from the
published canonical-row semantics.  Its external arithmetic trust boundary
is therefore limited to byte-pinned data:

- producer gate `964ab9cd...` and producer driver identity `e48d46f4...`;
- authorization `8bf587b2...`;
- exact D2 reference `fbc8c38d...`; and
- consumer policy gate `a1ab82c3...`.

Sparse row omission alone does **not** prove that an omitted source integral
is zero.  That source-integral trust boundary remains the caller-pinned result
bytes plus the pinned producer's exact fused/unfused equality gate.  The
consumer independently checks tag admissibility and reconstruction, but does
not re-run integration.  Exact matrix hashes inside the future result are not
trusted as matrix inputs.  Timing fields only re-apply the frozen producer
resource ceilings.

## Use and tests

Only after the producer has closed and published a complete artifact should a
caller pin those final bytes and run:

```sh
python3 agents/small-delta-frontier/consume_stratum_moment_d4_degree3.py \
  --result COMPLETED_RESULT.json \
  --expected-result-sha256 CALLER_PINNED_FINAL_SHA256 \
  --expected-consumer-sha256 CALLER_PINNED_CONSUMER_SHA256
```

The report is emitted to stdout.  The prelaunch tests are synthetic/schema
tests and never open a degree-three result:

```sh
python3 agents/small-delta-frontier/test_consume_stratum_moment_d4_degree3.py -v
python3 -O agents/small-delta-frontier/test_consume_stratum_moment_d4_degree3.py -v
```

Both modes pass 7/7 tests, including wrong-self-SHA, post-read self mutation,
authorization mismatch, unused `R=15` class-1 tags, and malformed J
coordinates.  No degree-three quotient or candidate is reported
at this checkpoint because no degree-three output was read.
