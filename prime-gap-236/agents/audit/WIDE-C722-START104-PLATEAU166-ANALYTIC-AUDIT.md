# Wide C722 start-0.104/plateau-0.166 schedule: `AUDIT PASS`

This verdict covers the analytic Proposition-1 hypotheses only, not a sieve
quotient.  The independently reconstructed outer schedule is

\[
B_{2,m}=\min\left\{\frac{13}{125}+(m-1)\frac{361}{50000},
                         \frac{83}{500}\right\}.
\]

It has active counts 0 through 22 and count 23 is strictly empty with margin
`3/50000`.  Through that first empty count the exact schedule is

`13/125, 5561/50000, 2961/25000, 6283/50000, 1661/12500,
1401/10000, 3683/25000, 7727/50000, 1011/6250, 83/500` and then
`83/500`.

## Exact reconstruction

The verifier reruns every schedule-dependent rational branch from the frozen
source-level analytic engine.  Inner/inner moduli use BV.  Mixed orientations
use BV below the threshold and repaired direct-HB IIa/IIb/III above it; their
IIc gamma interval is empty.  Outer/outer uses BV below square root,
omega-zero IIa/IIb/III near square root, and the full continuous dynamic IIc
cell cover above square root.  These classes form the recorded disjoint range
assignment.

The weighted prime minorant is

\[
\rho(n;x)=\frac{\log n}{\log(3x)}1_{\mathbb P}(n)1_{[x,2x]}(n),
\qquad c_1=c_2=0,\quad\beta=\frac12.
\]

Schedule-dependent exact minima are:

| family | checks | least slack |
|---|---:|---:|
| mixed fixed IIa/IIb/III | 2,481 | `999997/7500000000` |
| transpose fixed | 2,481 | `999997/7500000000` |
| outer fixed | 1,584 | `4499999869/600000000000` |
| outer-near fixed | 1,584 | `45449999/2500000000` |
| outer dynamic IIc | 135,168 | `3549979/120000000000` |

All source and open-endpoint margins are strictly positive; the smallest
source margin is `1/200000000000`.

The schedule lies in an independently certified rational interior box:
the start may vary by `1/5000` and the plateau independently by `1/100000`.
The pointwise upper corner still passes all fixed cases and all 135,168
dynamic cells, with least dynamic slack `1149979/120000000000` and least
mixed fixed slack `2224973/37500000000`.  Every schedule in the box is a
pointwise subset of that corner, so the verification is for the continuum,
not merely four sampled points.

For this fixed prefix method, `417/4000 = 0.10425` passes while
`5213/50000 = 0.10426` fails mixed IIb at pair `(1,9)`.  Thus the chosen
start is at least `1/4000` below a passing point.  The earlier start
`5051/50000` target-10 schedule is retained only as superseded discovery.
The true neighboring failures at targets 8 and 9 are repaired IIb failures;
the generic mixed-IIc failures are inapplicable because that interval is
empty by `71149997/7500000000`.

This schedule pointwise dominates the earlier target-10, count-15, and volume
ramp schedules.  It does not by itself prove a quotient above one.

## Frozen verifier

```sh
python3 agents/audit/verify_wide_c722_start104_plateau166_analytic.py
python3 -O agents/audit/verify_wide_c722_start104_plateau166_analytic.py
```

Both modes emit identical bytes, equal to the frozen JSON artifact.

- checker SHA256:
  `faa23bd7370c9c4d1cc00aa3e21577884a2553bca68258f918fca992cf4d111a`
- JSON audit SHA256:
  `148852f6021119015fb1dbf0ae61d842ac16371e14ee94001d80a3e832c892e7`

An exact capped quotient above one and a final theorem audit remain required.
