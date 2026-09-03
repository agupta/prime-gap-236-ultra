# One-outer-band width portfolio v4

Status: `EXACT ONE-OUTER-BAND WIDTH PORTFOLIO PASS`.

This is an analytic-support certificate only.  It does not certify an energy
lower bound, a quotient, or a bounded-gap conclusion.  Its exact acceptance
closure does not read the ancillary H2 diagnostics or proxy below.

## Exact artifacts

- `verify_one_band_width_portfolio_v4.py`
  SHA-256 `67cadda54da344c0760bec204d9656d09e8e1fa8ff70adb0e8648423c982a923`.
- `one_band_width_portfolio_v4_exact.json`
  SHA-256 `4d8053a4ef6160ea30bab5b4573379d1903bb235c4dc513d9985d6bc6297b7e5`.
- `test_one_band_width_portfolio_v4.py`
  SHA-256 `06c06b63c3da28685d7185fdcb4f3f42968b8c4ed6160109be4f37c68c8b97fb`;
  four lightweight integrity/hostile tests pass.

The checker hash-pins the frozen v3 kernel at
`fff280573fa1bf539fe8fcba72270aa088c6d35255f39da24d7fb77fce5a75d5`.
Each candidate reruns the complete v3 Definition-1, Proposition-2/1,
direct-HB source, fixed IIa/III, continuum-gamma IIb, and 16-by-16 IIc
inventories at its own endpoint.  It also reruns packing after adding
`1/10000000` to every outer cap and checks the corresponding negative shift's
active inventory.

## Rational candidates

The common values are `delta=1/60`, `epsilon=3/400`, and old outer width
`x=6241/900000`.  Every schedule below is its 12-entry head in millionths;
the twelfth cap is extended as a plateau, so counts 0 through 12 are active
and count 13 is empty.

| lambda | A2 | alpha2 | eta | 12-entry cap head (millionths) |
|---|---|---|---|---|
| `19/20` | `4618579/18000000` | `4753579/18000000` | `4483579/18000000` | `141072,157274,167751,173648,184820,190315,191873,197631,201942,206705,211467,215216` |
| `39/40` | `3081133/12000000` | `3171133/12000000` | `2991133/12000000` | `141766,157158,167088,172955,184749,189621,191266,197779,201335,206088,210932,214740` |
| `1` | `231241/900000` | `237991/900000` | `224491/900000` | `142459,157043,166329,172261,185389,188928,190659,196720,202462,206792,210255,214263` |

Relative to the frozen `lambda=37/40` schedule, the exact cap changes for
counts 2,3,4,5 are respectively:

- `lambda=19/20`: `+233,-793,-690,-668` millionths;
- `lambda=39/40`: `+117,-1456,-1383,-739` millionths;
- `lambda=1`: `+2,-2215,-2077,-99` millionths.

Thus widening necessarily moved the discovered face in the wrong direction
at the empirically dominant counts 3 and 4.  Repeating the float discovery
from a minimally active schedule, and reversing count-3/count-4 priority,
returned the same `lambda=19/20` face to below one millionth.  This is a local
search observation, not a proof of global cap optimality.

## Exact margins and inventories

| lambda | direct-HB face reserve | base minimum packing reserve/case | `+1e-7` minimum packing reserve/case |
|---|---|---|---|
| `19/20` | `6421/6000000` | `1/6000000` / IIc | `17/120000000` / IIc |
| `39/40` | `6601/12000000` | `3497/30000000000` / IIc | `2897/30000000000` / IIc |
| `1` | `3/100000` | `94998119/180000000000000` / IIb | `81498119/180000000000000` / IIb |

For every row the ordered inventories are identical: 582 main pairs, 168
near-root pairs, 1,500 fixed IIa/III checks, 168 dynamic pairs, and 43,008
adverse IIc cells.  Both zero-left and zero-right inventories are 39.  The
minimum source margin is `1/200000000000` in the outer/outer IIc-width check.
The candidate-specific IIb breakpoint record counts and exact worst witnesses
are serialized in the result rather than abbreviated here.

The main face requires `3w+delta<3/80`, equivalently `w<1/144`.  Consequently
there is no maximal rational interior width: for rational `w<1/144`, the
rational midpoint `(w+1/144)/2` is larger and remains strict.  The exact
supremum ratio to the old width is `6250/6241`.  The `lambda=1` row is the full
old endpoint, not a falsely labelled maximum.

## Ancillary H2 cap-CDF comparison

- `compare_one_band_width_h2_proxy_v4.py`
  SHA-256 `20b0c02d5fc1a5236eaec895f7baccd55baba000b266727a152cb1de3cc9be5b`.
- `one_band_width_h2_proxy_v4.json`
  SHA-256 `63368f08c54d0ca898fc2acaf7bbc41cc647aea3368fd42a19384ad2b6483943`.

This ancillary proxy linearly shifts the five local cap-CDF samples in each
of seeds 2361817 and 2361818.  It omits all newly added shell mass and does not
recompute `A`, `b`, or `b^2/A`.  The mean cap-side proxy ratios relative to
`lambda=37/40` are `0.99158645`, `0.98218522`, and `0.972210998` for
`lambda=19/20`, `39/40`, and `1` respectively.  Therefore none of the wider
supports currently qualifies as an energy-retention improvement.  All three
also retain exactly the same active-count and pair inventories, so no material
exact-`A,b` combinatorial cost reduction is established.

Recommendation: keep `lambda=37/40` as the exact `A,b` priority.  Reconsider
a wider exact support only if a direct energy evaluation demonstrates that
its added shell outweighs the measured high-share count-3/count-4 cap loss.
