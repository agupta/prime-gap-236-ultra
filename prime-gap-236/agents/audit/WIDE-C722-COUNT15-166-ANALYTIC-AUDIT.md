# Wide C722 count-15/0.166 schedule: `AUDIT PASS`

This verdict covers every analytic Proposition-1 hypothesis, not a sieve
quotient.  The independently verified schedule is

\[
B_{2,m}=\min\left\{\frac{1623}{25000}+(m-1)\frac{361}{50000},
                         \frac{83}{500}\right\}.
\]

It reaches the plateau at count 15, has active counts 0 through 22, and count
23 is strictly empty with margin `3/50000`.

## Exact reconstruction

The checker reuses only the frozen source-level analytic engine, then reruns
all schedule-dependent cases from rational inputs.  The four ordered band
exponents and disjoint distribution-range assignment are unchanged.  Mixed
IIc and outer-near IIc are empty; outer-above-square IIc receives its full
continuous 16-by-16 cell cover.  The weighted prime minorant is

\[
\rho(n;x)=\frac{\log n}{\log(3x)}1_{\mathbb P}(n)1_{[x,2x]}(n),
\qquad c_1=c_2=0,\quad\beta=\frac12.
\]

Schedule-dependent exact minima are:

| family | checks | least slack |
|---|---:|---:|
| mixed fixed IIa/IIb/III | 2,481 | `23349997/7500000000` |
| transpose fixed | 2,481 | `23349997/7500000000` |
| outer fixed | 1,584 | `4499999869/600000000000` |
| outer-near fixed | 1,584 | `45449999/2500000000` |
| outer dynamic IIc | 135,168 | `3549979/120000000000` |

All source/open-endpoint margins remain strictly positive.  The smallest
source margin is `1/200000000000`.

This point is not an active-boundary accident.  Independently varying both
the start and plateau by every amount of absolute value at most `1/100000`
preserves Definition 1 and the active inventory.  The pointwise upper corner
passes every fixed check and all 135,168 dynamic cells; its least dynamic
slack is still `1149979/120000000000`.  Monotonicity of the support in the two
schedule parameters covers the entire rational box, not just its corners.

## Correction to the claimed neighboring frontier

The generic discovery checker reports failures for maximal-slope targets 8
through 14 in a fixed “mixed IIc” branch.  That gamma interval is empty by
the exact margin

`71149997/7500000000`.

Those failures are therefore not analytic obstructions and cannot establish
that count 15 is the first feasible target.  Checking only nonempty source
branches gives:

- targets 8 and 9: this sufficient prefix method first fails repaired IIb,
  at pairs `(1,7)` and `(1,9)` respectively;
- target 10: all fixed branches and all dynamic cells pass;
- targets 11 through 15 are pointwise subsets of target 10 and also pass.

The stronger target-10 schedule starts at `5051/50000` and has the same
plateau `83/500`.  It pointwise dominates both the count-15 schedule and the
previous volume ramp (`49/625`, plateau `1599/10000`).  Hence count 15 is
analytically valid but is not the true frontier of this family.

## Frozen verifier

```sh
python3 agents/audit/verify_wide_c722_count15_166_analytic.py
python3 -O agents/audit/verify_wide_c722_count15_166_analytic.py
```

Both modes emit identical bytes.

- checker SHA256:
  `3d6c3c2a1887d0bce11303b62ad37f5427fbfce425d3aa8888e67f6ac9eb2cdf`
- JSON audit SHA256:
  `f3cb62c4c53e3eb28480710675409805173be52a51e9ca6ffdfac4f0c104c8f9`

An exact capped quotient above one and a final theorem audit remain required.
