# Exact-whitened D4 calibration v6.4

Status: repaired prelaunch candidate only. No production authorization,
chain, sampled quotient, D12 screen, or theorem claim follows from this file.

Frozen v6.3 gate SHA `b5098156...2ce16` is preserved and permanently
unlaunched. Its raw-total checks still accepted a positive first z moment with
an exact-zero second moment when squaring the first moment landed at the
minimum subnormal and the inherited ULP allowance erased that one-ULP Jensen
gap.

V6.4 retains all predecessor raw-total, local aggregation, local Jensen, and
exact stratum-bound checks. Before them, it requires exact zero/nonzero status
agreement between each nonnegative batch first/second z pair and the raw
aggregate first/second pair. It rejects signed negative zero and every
positive subnormal serialized z moment. At observation time it also rejects a
positive z whose square is zero or subnormal, rather than silently losing its
second moment. Observed physical tail moments are many orders of magnitude
above this representation floor.

The independent v6.3 `AUDIT FAIL` is pinned verbatim: report SHA
`9b65083f553d356f2f525197623eb153dba4e1f7fdd6f3d18fa200acb08ace98`,
verifier SHA
`6302c8f8d9dbc2e557081784e359fb811ca4b1d1998aa69955169029fd1dfe6b`,
and zero-second regression SHA
`0aa8fa5c9db51d3c433e6e1ecefaa740883c4b1282e09fbff7504ffa78934b65`.
The gate remains production-disabled pending another independent hostile pass
and separate root authorization.
