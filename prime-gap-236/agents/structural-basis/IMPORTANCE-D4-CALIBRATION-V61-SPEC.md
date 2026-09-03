# Exact-whitened D4 calibration v6.1

Status: repaired prelaunch candidate only.  No production authorization,
chain, sampled quotient, D12 screen, or theorem claim follows from this file.

V6 gate SHA `d7ab62d0...9521b` is preserved but invalid: its legacy J record
validator checked only the global envelope inequalities `z<=2` and
`z^2<=4`.  A self-consistent common-stratum-zero record with every z first
and second moment equal to one passed that validator even though the exact
pointwise bound is `17/16384`.

The predecessor failure is itself an input, not a narrative assumption.
V6.1 pins verbatim the independent audit report SHA
`2c2b3ec5887b982185624216d041ecf44531bb0da279271e05a1a77a11d06ff4`,
independent verifier SHA
`b643bd7458e1ecdf3909d33a753fcabe83abbf9305d811d086a5d24030837ce7`,
and minimal failing regression SHA
`b278c5a78513e2e5ed017cdff873a519cef44c40a49ed1e076b32dfae41edc3d`.
The regression mutates only one batch z-second moment and the matching raw
z-second sum to `2*Z_0^2`; frozen v6 accepts it, whereas v6.1 rejects it.

V6.1 reuses every frozen v6/v5 formula, chain schedule, statistical gate,
fresh-only checkpoint rule, held-directory race defense, exact whitening,
and the unchanged relative rank tolerance `1e-12`.  It additionally derives
from the exact transformed tagged-constant weights, and enforces both at
every generated J envelope point and on every batch and raw first/second
moment,

```text
z <= Z_r = sum_{s in {r,r+1}, s<16} w_s^2,
z^2 <= Z_r^2.
```

The 16 exact bounds are gate-pinned; they range from `1/8` down to
`1/288230376151711744`, with `Z_0=17/16384`.  Tolerances scale with the ULP
of each local bound rather than with one, so tail-stratum checks are not
silently weakened.  The v6.1 gate remains production-disabled until a fresh
independent hostile audit and root authorization.
