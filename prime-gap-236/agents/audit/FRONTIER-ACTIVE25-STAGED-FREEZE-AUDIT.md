# Active25 staged package: PRELAUNCH AUDIT FAIL

Date: 2026-09-03 (Europe/Berlin).

## Verdict

`PRELAUNCH AUDIT FAIL` for the announced full staged tuple.  This is a
provenance/immutability failure, not a refutation of the separately frozen
arithmetic core.

The producer announced the ordinary staged-wrapper paths as frozen at

- wrapper `d1b2d5c15fefdd3351088a6eab1885fdbbe4a12295aacb3b38bb4ad0a5ddbe64`;
- tests `e252b0c45cffc35e91418395c760ac42cf5cb978cf5f32d2dad8b4a3a56133d8`.

At hostile audit time those same paths instead contained

- wrapper `bb00675f722a843c0d87ef36e382aea812d6622c79da517e238b0146af9592dd`;
- tests `77ab338b79a30e653ba8b52cb468c3b5bd1db43f057da4d0799e390df360bf64`.

Thus the announced tuple cannot be replayed or audited from the named paths.
No production launch is authorized.  A repair must use new versioned paths,
explain the byte changes, freeze new hashes, and receive a fresh independent
audit.  Merely re-announcing hashes on the same moving paths is insufficient.

## Preserved positive scope

The distinct arithmetic-core package remains independently consistent: the
true ungrouped `r=10,h=10` oracle equals the grouped direct result exactly;
low-dimensional literal/grouped identities pass; and the reconstructed shell
matrix uses `48*(HH-HL-HL^T+LL)`.  The gate itself is frozen with
`launch_authorized=false`.  Those facts do not cure the full-tuple provenance
failure and do not authorize computation.

## Reproduction

Run in `prime-gap-236/`:

```bash
python3 agents/audit/verify_frontier_active25_staged_freeze.py
python3 -O agents/audit/verify_frontier_active25_staged_freeze.py
```

Both invocations must exit nonzero and name exactly the two mismatched files.
