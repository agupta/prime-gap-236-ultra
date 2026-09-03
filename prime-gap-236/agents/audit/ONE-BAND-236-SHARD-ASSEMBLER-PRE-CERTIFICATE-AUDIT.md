# One-band 236 shard assembler hostile audit

## Verdict

**SCOPED PRE-CERTIFICATE AUDIT PASS** for the exact aggregation algebra and
the fail-closed identity checks of the frozen assembler

```text
verify/assemble_one_band_236_shards.py
SHA-256 9963c94207ab4954ea235fe9c044fe240df2f74c8df5abe83e32467600648374
```

The earlier requested snapshots `b5231aed...` and live `92241c87...` were
rejected when their hashes disagreed.  This verdict attaches only to
`9963c942...` and its production test
`c1721c299e5346a50dd0e0384d4ce5094db6afea32636f85820396e67b726a67`.

This is emphatically **not an integration-replay pass** and not a theorem
audit.  The assembler consumes serialized exact shard values.  A standalone
certificate checker must reconstruct every A and b integral, or bind each
input to a separately passed reconstruction audit.  The independent hostile
test contains an explicit self-consistent branch-value mutation which this
aggregation layer accepts; that is a scope demonstration, not evidence for
the integral.

## Mathematical derivation checked independently

Put

```text
I = I(F),       D = I(F)-48 J(F,F),
A = I(H),       b = 48 J(F,H).
```

The inner and one-band outer supports are disjoint up to null boundaries, so
`I(F,H)=0`.  Definition 5 makes the numerator for `F+tH`

```text
48 J(F+tH,F+tH) = I-D + 2tb + t^2 48J(H,H).
```

Dropping the nonnegative last term and taking `t=b/A` gives the sufficient
inequality

```text
b^2/A > D, or equivalently b^2-A D > 0.
```

For this explicit `t`, the lower quotient minus one is exactly

```text
(b^2-A D)/(A I+b^2).
```

The assembler computes precisely these two expressions.  The frozen inner
vector is scaled by `10^87`, the outer vector by `10^38`, so `I,D`, `A`, and
`b` carry scales `10^174`, `10^76`, and `10^125`; both terms of the margin
carry `10^250`.  No favorable rounding occurs.  Independent rational examples
including a negative cross term reproduce the formula exactly.

## Definition-5 geometry and factor audit

The branch oracle in the independent test was written without importing a
shard producer.  For every `r=0,...,12` and both exact band endpoints it starts
from the remaining common-coordinate allowance

```text
eta-r delta
```

and independently applies the shared `r`-cap, distinguished-large `(r+1)`-cap,
and total-band bound.  It agrees with the assembler for all 26 cases.  Exactly
four branches (`Sdelta, Stotal, Ltotal, Lbig`) survive for `r=0,...,11`; at
`r=12` the large-coordinate cap is empty and exactly the two small branches
survive.  Null endpoints do not affect these polynomial integrals.

Each b shard is recombined as exactly

```text
48 * (sum(high branches)-sum(low branches)).
```

There is one and only one factor 48.  The high/low orientation agrees with the
band identity.  Removing a branch, changing the schedule, changing the source
closure, or changing only the serialized total is rejected.

## Source and result evidence

The assembler checks a 30-file transitive live source closure.  Every live hash
matched.  Its parsers also enforce exact top-level schemas, canonical rational
strings for all values used in arithmetic, exact candidate/scaling/support
geometry, all 13 counts, and exact branch/stat inventories.

The all-13 A parse sum equals both:

```text
agents/structural-basis/results/d14_one_band_a_aggregate_exact_v2_strict.json
agents/audit/results/d14_one_band_a_aggregate_v2_strict_audit.json
```

and the latter records exact equality of all 13 independent radial replays.
The real collected-v5 `r=0` b shard parses to the same exact rational as the
independent v5-versus-fast-v2 result audit, whose reference fields are
bit-identical.

The assembler's direct-`O_EXCL` publication prevents overwrite but is not an
atomic temp-file publication: a crash can leave a truncated final file.  This
is an availability/restart weakness, not a false-certificate path, because a
strict reader rejects truncated JSON.  The final standalone checker should
still use atomic publication or verify only a completed, externally hashed
artifact.

## Reproduction

```bash
python3 verify/test_assemble_one_band_236_shards.py
python3 -O verify/test_assemble_one_band_236_shards.py
python3 agents/audit/test_assemble_one_band_236_shards_independent.py
python3 -O agents/audit/test_assemble_one_band_236_shards_independent.py
```

All four commands pass.  The independent audit has eight tests.  Its frozen
SHA-256 is

```text
170d4b448e78de2e2c3d267b66266d128ff1d5bb911703c7bc6a8517ef938930
```

## Scope gate for later use

A future positive aggregate may use this pass only if all thirteen A shard
hashes agree with the already frozen all-count radial audit and every one of
the thirteen b shard hashes has an independent result-level/reconstruction
pass.  Merely obtaining `theorem_ready_scalar=true` from this assembler is not
an exact integration certificate and cannot close `H_1<=236`.
