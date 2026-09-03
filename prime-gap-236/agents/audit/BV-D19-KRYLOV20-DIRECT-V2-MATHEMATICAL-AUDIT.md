# BV D19 Krylov-20 direct-v2 mathematical audit

Date: 2026-09-03

Verdict: **PASS**. No mathematical or software defect was found within the
stated scope: exact cache-free evaluation of this one rational, symmetric,
full-simplex particular vector. This does not certify Krylov optimality, a
capped-support quotient, Proposition 1, or `H1 <= 236`.

## Frozen artifacts and replay

The requested hashes match:

- checker: `ff2046ce180394a6328fdec2c112d575a4c540ff964f5dede28c6db6091506c5`;
- tests: `5f03f8cdbc9235dd739c36901fab42cd44216b1213009fd019dfb1ae32fa6d27`;
- candidate: `986563579cb7fa8653f774100e9fd1cc966761261eef53052b8be8e61f96d276`;
- strict result: `8b0d47b22b09c057633022682332f0de4b7e47d4b6ab6d630690be081c58e170`.

Fresh normal and `python -O` executions both reproduced the strict result
byte-for-byte. Each reports 568 marginal terms and 13,955 terms in each
square. A separate scan-free recurrence contraction also reproduced the exact
denominator, numerator, quotient, and normalized deficit.

## Mathematical checks

- The orbit-product recurrence has the correct labeled-matching and
  automorphism factors for `P_lambda P_mu`; direct monomial expansion agreed
  in 36 small cases, including repeated parts. The full candidate contraction
  processes all `568*569/2 = 161596` input pairs.
- For `F = sum c_(a,lambda) (1-sum t)^a P_lambda`, the reconstructed `I`
  moments are the exact Dirichlet moments after expanding about `alpha`.
  The distinguished-coordinate integral uses
  `integral_0^R t^e(R-t)^c dt = e!c! R^(e+c+1)/(e+c+1)!`; its square is then
  integrated exactly over `sum u <= eta`. These formulas agree with the
  independent low-degree matrix construction.
- The numerator is `kJ`, with `k=48` applied exactly once after forming the
  marginal square. A separate constant-polynomial closed-form fixture matched
  `I = alpha^48/48!` and the returned numerator `48J` exactly.
- Independent enumeration gives 568 even-orbit basis elements of degree at
  most 19 and 707 through degree 20. The serialized basis equals the complete
  canonical D19 list; it is also exactly the first 568 entries of D20, whose
  remaining 139 entries have degree 20. The vector has exactly 568 entries.
- All coefficients, parameters, moments, and comparisons use
  `fractions.Fraction`; no floating arithmetic enters certification. Every
  serialized rational is canonical. Exactly,
  `numerator/denominator = quotient`, `denominator-numerator = deficit`, and
  `quotient + normalized_deficit = 1`; both denominator and deficit are
  positive. The quotient is approximately `0.9867930836956087557`.

## Validation and closure

The seven supplied tests pass under normal and optimized Python. Ten additional
benign full-record fixtures were rejected by `build`: fractional/boolean basis
exponents, fractional/negative partition parts, a noncanonical vector
rational, a numeric claimed rational, a boolean identity integer, a short
vector, a duplicate JSON key, and a nonfinite JSON number.

The v1 issue is reproducible: JSON `basis[0][0] = 0.5` is parsed as a float and
v1's `int(0.5)` silently maps it to the original exponent zero. V2 requires
`type(value) is int` for every mathematical integer and rejects this record
before invoking v1. Its canonical-rational checks likewise prevent lossy or
ambiguous spellings.

Source closure is complete for the replayed computation: v2 pins v1 at
`63bd2a3adc84191d212d52d3175179f583a1257d7c862f1ee07ecaa2ade3b7d3`;
v1 pins the scan helper at `96495079...` and exact integrator at `941ee82b...`;
the candidate is checked against its supplied hash before parsing; and v2,
v1, both dependencies, and the candidate are re-read after reconstruction.
The strict result records the same transitive hashes and exact candidate data.
