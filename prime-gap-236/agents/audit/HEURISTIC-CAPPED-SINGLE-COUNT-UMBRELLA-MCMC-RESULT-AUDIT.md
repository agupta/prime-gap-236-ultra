# Single-count umbrella MCMC v1: `AUDIT FAIL`

Scope: whether the frozen R15 umbrella run is reliable evidence for the sign
of the capped two-dimensional quotient.  It is not an audit of the exact
uncapped pencil and it cannot prove or disprove a capped quotient bound.

## Frozen inputs

- run `results/heuristic_capped_single_count_R15_umbrella_v1.json`:
  `bdc64a3523a4e00846caa143372b164153181386e7f0b56fb4a55b6e073bdabc`
- source `scripts/heuristic_capped_single_count_umbrella_mcmc.py`:
  `fcef0eefc2a0503d2d1f27c568c64897dab01f8ed4c84dc33afb47a3551200a5`
- prior formula-level audit:
  `01ee2c600058d4ad592a3c2ce0b242fb43edb39109fe521400b890a7f2d6018a`

The formula-level result remains `SEARCH-INSTRUMENT PASS`: the umbrella
change of measure, target-15 small/large selection, and denominator-weighted
pooling are algebraically correct.  This result-level failure concerns mixing
and uncertainty.

## Smallest decisive pathology

There are 16 chains per group and 150 retained records per chain.  Every one
of the eight reported J umbrella visit fractions is exactly a multiple of
`1/16`, with chain-equivalent totals

`[4, 3, 1, 2, 4, 4, 1, 4]`.

Thus the aggregate occupancy is quantized in whole-chain histories and gives
no evidence of within-chain travel between the rare and ordinary strata.  No
transition counts, autocorrelation estimates, or effective sample sizes were
serialized.  Aggregate visit totals cannot by themselves logically recover
each chain path, but this complete chain granularity is a direct trapping
diagnostic and makes the apparent sample size unusable.

The independent checker also finds:

- group I estimates span a factor `38.78170848488547...`;
- group J diagonal estimates span a factor `2923.174639791927...`;
- cross estimates disagree in sign (2 positive, 6 negative);
- group roots span `0.9812781318877733...` to
  `2.3294783618246846...`, a range `1.3482002299369113...`;
- the reported group-root standard error is `0.16734514851176678...`;
- raw group numerators and self-normalizing denominators were not serialized,
  so denominator-weighted pooling uncertainty cannot be reconstructed.

All eight group roots and the pooled root `0.9814546588482798605` were
independently recomputed from the serialized moments and frozen exact
normalizers.  This verifies arithmetic replay only.  It does not validate the
reported sign.  The pooled sign, every group sign, and any exact-stage go/no-go
decision based on this run are statistically unusable.

## Independent verifier

Run:

```sh
python3 agents/audit/verify_heuristic_capped_single_count_umbrella_mcmc_result.py
python3 -O agents/audit/verify_heuristic_capped_single_count_umbrella_mcmc_result.py
```

Both modes emit identical bytes.

- checker SHA256:
  `38b0ff50268734b82bfe1650effc8dad70d2d98cf9570085cf4e15c3bae20ca1`
- frozen JSON audit SHA256:
  `c9b21bbef7fed2b8cabcfa52aabdd7a7807f0ac1ce3b59a8d561c0d573b5c76a`

Decision: `AUDIT FAIL`.  The run can neither authorize nor veto an exact
capped calculation.
