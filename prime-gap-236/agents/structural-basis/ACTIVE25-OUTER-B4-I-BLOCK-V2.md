# Active-25 outer even-B4 exact I block, v2

Status: exact denominator-only structural artifact.  No J form, Rayleigh
quotient, numerical eigensolve, or sieve implication is present.

The v1 artifact (SHA `368c5305...`) contains the correct exact matrix but a
false cost statement: its source evaluated all 100 ordered entries for each
support while reporting 55 upper-triangle contractions.  Both the v1 source
and artifact are preserved.  V2 computes exactly the 55 pairs `j<=i` for the
high support and the same 55 for the low support, fills the transpose, and
clears exact moment caches after each row.

The ten coordinates are `even_basis(4)` on the shell between the high and low
total endpoints of the independently audited active-25 schedule.  Every entry
is

```
I_shell(G_i,G_j) = I_high(G_i,G_j) - I_low(G_i,G_j).
```

The result stores all three exact Fraction matrices, an exact signed-vector
difference fixture, exact rank, determinant, and all LDL pivots.  The low-k
test independently evaluates quadratic forms through the grouped face
integrator at `k=3`.  A call-counting regression proves that v2 performs 55,
not 100, basis-moment calls per support and reproduces every preserved v1
matrix entry.

Reproduce with:

```
python3 -m unittest agents/structural-basis/tests/test_active25_outer_b4_i_block_v2.py
python3 -O -m unittest agents/structural-basis/tests/test_active25_outer_b4_i_block_v2.py
python3 agents/structural-basis/code/active25_outer_b4_i_block_v2.py --preflight-only
python3 agents/structural-basis/code/active25_outer_b4_i_block_v2.py \
  --progress \
  --output agents/structural-basis/results/active25_outer_even_b4_shell_i_exact_v2.json
```
