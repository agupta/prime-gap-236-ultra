# Active-25 outer even-B4 denominator block

Status: exact I-only structural computation.  This package contains no
distinguished-variable integral, no J matrix, no quotient, and no sieve
claim.

The support is the independently audited active-25 outer schedule with
`delta=361/50000`, high total endpoint `3211/12000`, low total endpoint
`103/400`, and the same 26 rational caps on both sides.  For the ten labels in
`even_basis(4)`, the shell Gram block is reconstructed entrywise as

```
A_shell[i,j] = I_high(G_i,G_j) - I_low(G_i,G_j).
```

The source computes all 55 upper-triangle contractions exactly as Python
`Fraction`s, emits the full high, low, and difference matrices, clears all
support/radial caches after every completed row, and certifies the shell
matrix's exact rank and LDL pivots.  A signed-vector fixture separately binds
the difference identity.  Low-k tests compare each quadratic form against the
independent grouped face traversal at `k=3` and test exclusive publication.

This block is useful only for detecting dependence and scaling of a future
outer polynomial residual.  It gives no numerator information and therefore
cannot establish even a heuristic Rayleigh sign.

Reproduction commands after the source/test tuple is frozen:

```
python3 -m unittest agents/structural-basis/tests/test_active25_outer_b4_i_block_v1.py
python3 -O -m unittest agents/structural-basis/tests/test_active25_outer_b4_i_block_v1.py
python3 agents/structural-basis/code/active25_outer_b4_i_block_v1.py --preflight-only
python3 agents/structural-basis/code/active25_outer_b4_i_block_v1.py \
  --progress \
  --output agents/structural-basis/results/active25_outer_even_b4_shell_i_exact_v1.json
```
