# Capped count-pencil MCMC result audit

## Verdict

**AUDIT FAIL as evidence for a positive capped quotient or an exact launch.**
The aggregate value `1.0324314258639082365` is not blessed.

Two of eight group pencils return `NaN`, and consequently the reported group
standard error is also `NaN`.  The remaining group roots range from
`0.98144868059860557175` to `3.2332204010235447988`, a spread of
`2.25177172042493922705`.  These are instability diagnostics, not a positive
signal.

Replaying the aggregate matrix gives the serialized eigenvalue, but its top
direction places approximately `0.7740501692300085` of its `I`-norm in the
single `R=15` coordinate (and nearly all the remainder in the inner
coordinate).  The run contains only 277 aggregate outer-I observations at
`R=15`.  Its decisive `B(inner,15)` and `B(15,15)` estimates have no
serialized entrywise group error bars.  The exact-zero estimate `B(6,7)` is
also sampling output, not a proved structural zero.  At least one selected I
frequency vanishes in each NaN group; the artifact does not serialize enough
groupwise data to identify or repair those pencils.

No individual entry sign is statistically certifiable from this artifact.
The only conservative qualitative ranking retained is:

1. compute the `R=15` shell-I block first;
2. compute inner--`R=15` and `R=15` self-J blocks from common counts 14 and
   15;
3. compute `R=14`--`R=15` as an adjacency/control block;
4. infer no capped quotient sign from the MCMC run.

The separate formula audit remains a `SEARCH-INSTRUMENT PASS`; this failure is
about the realized Monte Carlo sample and its use as evidence.

## Frozen replay

- production artifact:
  `e8a93753ceb5b5cf10af0cae61937ed05647aad40863da67b3385d84ef12f29c`;
- checker:
  `a0dec740443a879ebcfc4643a7f5df2dbd5e45562bf30d1da72de90d03aaf5b6`;
- audit result:
  `ae403c7f74a88197fa0cb6b3638daaedcde92fb9521d7701873e16441b41ffbe`.

```bash
cd prime-gap-236
python3 agents/audit/verify_heuristic_capped_count_pencil_mcmc_result.py
python3 -O agents/audit/verify_heuristic_capped_count_pencil_mcmc_result.py
```

Normal and `-O` audit outputs are byte-identical.
