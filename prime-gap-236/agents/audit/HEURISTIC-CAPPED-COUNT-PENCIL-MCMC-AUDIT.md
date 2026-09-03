# Heuristic capped count-pencil MCMC audit

## Verdict

**SEARCH-INSTRUMENT PASS.**  The frozen program places its sampled moments in
the intended count-tagged Definition-5 pencil.  This verdict is formula-level
only: the Markov-chain convergence, floating-point error, and every reported
quotient remain non-rigorous.

For outer total-count basis functions, `I` is diagonal because the count
strata are disjoint.  If the shared `k-1` coordinates contain `r` large
coordinates, the small distinguished branch contributes to outer count `r`
and the large branch to count `r+1`.  Consequently outer `48J` has only
diagonal and adjacent entries.  The code places the small-large product once
in the symmetric `(r,r+1)` entry; the ordinary quadratic contraction supplies
the factor two.

The exact inner block `B00` uses `eta1=97/400`.  Every sampled block involving
the outer band uses `eta2=3031/12000`.  Its importance normalizer is

```text
b_inner_eta2 + b11_full = 48 integral_[U<=eta2]
                              (m_inner^2 + m_outer,full^2),
```

so factor 48 is already present and is not reapplied.

Two required hostile fixtures pass:

1. The exact inner tail from `eta1` to `eta2` is strictly positive.  Replacing
   `b_inner_eta2` in the envelope by `b00` changes the scale and is rejected.
2. A synthetic common-count point places its small and large components in
   `r` and `r+1`; injecting a fake nonadjacent `(r,r+2)` entry is rejected.

The checker additionally tests the cap helper on a constant fiber against
the exact small/large interval lengths.  Normal and `-O` outputs are
byte-identical.

## Frozen replay

- search source:
  `5accfe97f9561ce08f3fb403d9d0579847caf289a9cbd2ca8ad6229f6bc11c7b`;
- checker:
  `4f7b17a63aaa4135305270ab6a845f60724240ec5a3f2232f0c560b6f65be529`;
- audit result:
  `fe62c0865e93b9b14fab3227c4677094863b74de73c0abb84dd9d474b3846976`.

```bash
cd prime-gap-236
python3 agents/audit/verify_heuristic_capped_count_pencil_mcmc.py
python3 -O agents/audit/verify_heuristic_capped_count_pencil_mcmc.py
```

Nothing in this audit is an exact capped quotient, a Proposition-1
certificate, or an `H1<=236` proof.
