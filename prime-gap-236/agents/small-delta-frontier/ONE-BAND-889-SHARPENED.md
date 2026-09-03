# Sharpened one-band B889 support

Status: **analytic Proposition-1 parameter audit pass; finite quotient not yet
proved**.

## Exact support

Take

```text
k=48, epsilon=3/400, delta=7/250,
A=(-3/400,253/1000),
B_1=B_2=159999999/1000000000,
B_m=889/5000  (m>=3).
```

The schedule is extended constantly.  Counts `0,...,6` are active and count
7 is the first empty count because `6 delta=21/125<=889/5000<49/250=7
delta`.  This support strictly contains the previously audited B889 support:
only `B_1,B_2` change, from `3/20` to `159999999/10^9`.

The retreat from `4/25` is forced by the literal repaired Type-IIc inward
reserve.  At `omega=3/1000`, its first capacity is

```text
C1=1599999995521/5000000000000.
```

Thus the chosen `(1,1)` endpoint has exact reserve

```text
C1-2B1=5521/5000000000000 > 0,
```

whereas `B1=B2=4/25` fails at the explicit point `(4/25,4/25)` by
`4479/5000000000000`; neither coordinate fits any of the other three bins.

## Complete continuum cover

The checker enumerates all 27 nonempty unordered active count pairs.  It uses
exact `Fraction` boxes and a fixed bin assignment on every leaf.  Exact node
counts are

```text
IIa 27, IIb 27, repaired-IIc 1845, corrected-III 27.
```

This is not a vertex or random check.  A second source-level checker using the
independently maintained 16-by-16 `(gamma,omega_0)` cell decomposition also
passes all 27 pairs (7609 total nodes).

## Proposition 1 transfer

The support has exactly the same `A,delta,epsilon` as the audited B889 point.
Consequently every Heath--Brown classification, Type-0 estimate,
prime-power removal, and epsilon-cancellation identity is unchanged.  The
only changed analytic datum is the cap schedule, and every cap-dependent
partition case is reconstructed above.

For the direct-Heath--Brown route one may use
`rho=(log n/log(3x))*1_P(n)` on `[x,2x]`; the pinned source-level proof gives
all four Proposition-1 hypotheses with `c1=c2=0`.  Independently, the paper's
Proposition-2 prime-indicator branch has

```text
(xi1,xi2,xi3)=(19/50,2/5,2/5), beta=1-2xi2=1/5,
beta-B1=40000001/1000000000 > 0,
```

and its remaining four scalar inequalities are strict.  The direct route is
the preferred dependency because it incorporates the source-audited repairs
to the printed universal argument; this document does not silently invoke
the defective negative-`omega_0` range.

Selected exact unchanged margins are

```text
Type-0 sharp-interval saving       9400000001/100000000000
near-square-root IIc empty gap       399999907/300000000000
Type-II second scalar margin           2499999/5000000000
corrected Type-III distribution                 1/1250000000
higher-prime-power saving                           241/1500
```

The pinned analytic dependencies are listed byte-for-byte in the emitted
Proposition-1 artifact.  This closes the analytic parameter transfer, not the
finite-dimensional sign.

## Reproduction

```bash
python3 agents/small-delta-frontier/one_band_889_frontier_audit.py
python3 agents/small-delta-frontier/verify_one_band_889_prop1.py
python3 agents/small-delta-frontier/test_one_band_889.py
python3 -O agents/small-delta-frontier/test_one_band_889.py
python3 agents/independent-attack/code/verify_direct_hb_support.py \
  --delta 7/250 --A 253/1000 --epsilon 3/400 \
  --bounds 159999999/1000000000,159999999/1000000000,889/5000,889/5000,889/5000,889/5000,889/5000 \
  --gamma-cells 16 --omega-cells 16 --node-limit 4000000 \
  --min-width 1/1000000000000
```

Frozen SHA-256 values:

```text
bdc551e27f05e33d6395dd241ee116248874b17ebcb832f10c6cd6906fe580ba  one_band_889_frontier_audit.py
0bef3e4be5f4a9963f43ebdfd62f3017cd41bfa948624667619ec337733c1b63  results/one_band_889_sharpened_geometry.json
37b91d7c65dddcb2ef69c64db792e30929bd78062e980515c79e1ad106773040  verify_one_band_889_prop1.py
6189ac7a2837433a1bd760e29178dcf0e5809042c126da9d3b6d7bd1a7914dae  results/one_band_889_sharpened_prop1.json
a9c01a25c5081c8900af52e7bdf063068f051a937eebb60092ea92ed1307899e  test_one_band_889.py
```

The exact quotient is the remaining task.  No numerical or low-degree value
in this note implies a D12 sign.
