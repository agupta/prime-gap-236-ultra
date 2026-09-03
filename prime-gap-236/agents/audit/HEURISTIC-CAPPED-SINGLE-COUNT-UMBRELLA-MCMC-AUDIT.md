# Single-count umbrella MCMC formula audit

## Verdict

**SEARCH-INSTRUMENT PASS.**  This verdict concerns the frozen formulas only;
the sampler remains non-rigorous and cannot certify a quotient sign.

If the original target has density proportional to `d` and the umbrella
target has density proportional to `w*d`, the implementation uses exactly

```text
E_pi[f] = E_piw[f/w] / E_piw[1/w].
```

The pair-redistribution proposal is symmetric relative to uniform simplex
measure: a selected coordinate pair retains its sum and is redrawn uniformly
on that segment in either direction.  Metropolis acceptance with the ratio of
`d*w` therefore satisfies detailed balance.

For target total count 15, the J component is exactly `small` on common count
15 plus `large` on common count 14.  The umbrella biases precisely those two
common counts.  Group estimates are pooled with their inverse-umbrella
denominators, equivalently by pooling raw numerators and denominators.  A
synthetic unequal-denominator oracle confirms that the implemented weighted
pool agrees with the raw pooled ratio while the unweighted group mean does
not.

The checker also independently verifies the 2-by-2 off-diagonal scaling and
the Definition-5 cutoff assignment (`eta1=97/400` for `B00`,
`eta2=3031/12000` for outer-involving blocks).  Normal and `-O` outputs are
byte-identical.

## Frozen replay

- umbrella source:
  `fcef0eefc2a0503d2d1f27c568c64897dab01f8ed4c84dc33afb47a3551200a5`;
- checker:
  `e245c5da233db3d41a3a01308a7bad4cc56f072924e7215654046d2aad2a2252`;
- audit result:
  `01ee2c600058d4ad592a3c2ce0b242fb43edb39109fe521400b890a7f2d6018a`.

```bash
cd prime-gap-236
python3 agents/audit/verify_heuristic_capped_single_count_umbrella_mcmc.py
python3 -O agents/audit/verify_heuristic_capped_single_count_umbrella_mcmc.py
```

Burn-in, autocorrelation, effective sample size, floating-point error, and
all production-run stability checks remain outside this formula-level pass.
