# Exact-whitened D4 calibration v6.3

Status: unfrozen repair candidate only. No production authorization, chain,
sampled quotient, D12 screen, or theorem claim follows from this file.

Frozen v6.2 gate SHA `3642ace1...82bca` is preserved and permanently
unlaunched. Although v6.2 removed unit-scale comparison floors, it divided
serialized raw or batched totals before checking whether the positive total
survived as a positive average. A minimum positive subnormal raw z sum can
therefore become zero after division and compare equal to zero-valued batch
data.

V6.3 parses nonnegative z totals before averaging, rejects signed negative
zero, compares each raw total directly to `samples_per_batch` times the
faithfully summed batch means, rejects every zero/nonzero mismatch, and then
rejects every positive total whose required average underflows to zero. It
also rejects a positive z-second moment paired with an exact-zero z first
moment. All v6.2 local upper, aggregation, and Jensen checks still run after
this new prevalidation.

The frozen independent v6.2 `AUDIT FAIL` is pinned verbatim: report SHA
`3105d23283911725a914116ed50db36050cb34094a5874f1438f72c0c3f601f5`,
verifier SHA
`2c503f9f1b9c7e5d9ae9c3c99faf96ee4c2798a12746b3f307e4ca9564d0684b`,
and four-assertion underflow regression SHA
`bb2a1aa0689d1d351fb094e4cb2b3133ba6e5fd3e267423766cff5f8c1dc0dd8`.
The resulting gate remains disabled until a fresh independent hostile audit
and separate root authorization.
