# Local pair-MCMC cross-result withdrawal: `AUDIT FAIL`

All realized quotient signs from the fixed-amplitude, count-pencil,
binary-umbrella, and smooth-umbrella local-chain runs are withdrawn.  They
cannot support a theorem claim, authorize or veto an exact calculation, or
retire a support candidate.

## Decisive calibration failure

The frozen count-pencil run estimates the capped `R=15` frequency as

`0.0072135416666666666668`.

Multiplying by the exact rational uncapped outer normalizer gives its
serialized prediction

`1.3280806670018602944e-153`.

The independently branch-audited, complete 23-high-face/21-low-face
Decimal80 traversal instead gives

`1.867590058647541159966652284027770402944112322891498259579150487028098552988698e-156`.

Relative to the same exact rational uncapped normalizer, this is a cap
fraction

`0.000010143915982693550597719478888938625623586753201943...`.

Thus the local-chain estimate is too large by

`711.120013116594143006645267832610659...`.

The reference is a deterministic Decimal80 subtraction, not an outward-
rounded interval certificate.  That distinction cannot rescue an error of
more than a factor 700; it is fully sufficient to reject the Monte Carlo run
as calibrated evidence.

## Cross-run consequences

- The fixed-I groups differ by a factor `2.8767`; the independently run I/J
  fragments imply incompatible provisional quotients `1.02163`, `0.90068`,
  and `0.92884`.  The original source bytes for fixed I-v1 and J-v1 were also
  overwritten, so those two artifacts are no longer source-replayable.
- The count pencil reports `1.032431`, but has two `NaN` group roots, a
  `NaN` group error, and its decisive `R=15` mass is the quantity falsified
  above.
- The binary umbrella reports `0.981455`; its I group probabilities differ
  by a factor `38.78` and its prior hostile result audit already diagnosed
  whole-chain trapping.
- The smooth umbrella reports `0.981281`.  Its nominal J count-change values
  lie between 8.77% and 12.15%, but its I group probabilities still differ by
  a factor `22.92`.  A transition statistic does not establish stationarity,
  and the shared short local-chain design has failed its available exact-
  scale calibration.  The smooth negative sign is therefore not a valid
  search veto.

The prior count-pencil and binary-umbrella algebra audits remain
`SEARCH-INSTRUMENT PASS`.  Correct change-of-measure formulas do not validate
a non-equilibrated realized sample.

## Frozen replay

```sh
python3 agents/audit/verify_local_pair_mcmc_cross_withdrawal.py
python3 -O agents/audit/verify_local_pair_mcmc_cross_withdrawal.py
```

Normal and optimized modes emit identical bytes, equal to the frozen JSON.

- checker SHA256:
  `05735a7cd0d9e2122d41ae6cc95e55f626a60cb891ad8492d7d45f64bc9a76ae`
- JSON audit SHA256:
  `f48d5e30f503961e8bf4c6bd20bb4d51008e16f5dae2b829d9357300d48dfc19`

Only exact reconstruction or a genuinely calibrated sampler with an
independent reference can reinstate a capped quotient sign.
