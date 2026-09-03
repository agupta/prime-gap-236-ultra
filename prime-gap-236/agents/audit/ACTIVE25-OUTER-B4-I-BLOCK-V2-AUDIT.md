# Active25 outer even-B4 denominator v2 audit

Status: **AUDIT PASS**, strictly at the exact denominator-block scope.  This
artifact contains no `J` form, quotient, eigenvalue claim, or sieve result.

## Frozen package

- producer `active25_outer_b4_i_block_v2.py`:
  `ddad99bdd12710e669870fcade850eb72e1c5989ef4747b2e0658be28551b6bb`
- producer tests: `daaacda045b84eb30fbafe551300c771815f669bf5267092322854d48ba6a7e8`
- specification: `c6cb7207e1c4a4c0931d4562fffe539d6830bf8fff45aa9dd79751b6cfe64aa2`
- exact artifact `active25_outer_even_b4_shell_i_exact_v2.json`:
  `ffe98de8ee5d47da7f046f4aa91aaadc3f7981222f7b7803276556ea558e756c`
- independently reused low-level active25 support core:
  `1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a`
- analytic support identity artifact:
  `111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda`

The preserved v1 matrix is exact, but v1's work metadata was false: its
source evaluated 100 ordered entries per support while reporting 55 symmetric
pairs.  V2 genuinely evaluates only `j <= i` and copies the transpose.

## Independent reconstruction

The checker imports neither the v1 nor v2 producer.  It loads the separately
pinned active25 exact support core, hard-codes the ten `even_basis(4)` labels,
and independently performs all 55 high-support and 55 low-support
`basis_m1` calls.  It clears exact caches after each row and reconstructs

```text
I_shell[i,j] = I_high[i,j] - I_low[i,j]
```

for all 100 entries.  All three reconstructed matrices equal the artifact
entry by entry and equal the preserved v1 exact values.  An independent exact
Gaussian elimination gives rank 10.  An independent exact LDL
reconstruction has ten strictly positive pivots, so this particular 10 by 10
shell denominator block is positive definite.  The signed-vector fixture,
determinant, active-count list 0 through 25, schedule, support endpoints, and
the corrected 55+55 call metadata all agree exactly.

The producer tests pass 3/3 in normal and optimized modes, including the
low-dimensional grouped-form oracle and explicit 55-call counter.

## Audit artifacts and replay

- independent checker `verify_active25_outer_b4_i_block_v2.py`:
  `aa8b8cdb5eaaaf656c20fd44c0fe85a10d9c472dc80a747cca83daa154bc0605`
- audit result `results/active25_outer_b4_i_block_v2_audit.json`:
  `9888d3190a4f989a13a288e46d553f1f16eb780447b6e3bb1dd645130b77d23a`

Run:

```text
python3 agents/audit/verify_active25_outer_b4_i_block_v2.py
python3 -O agents/audit/verify_active25_outer_b4_i_block_v2.py
python3 -m unittest agents/structural-basis/tests/test_active25_outer_b4_i_block_v2.py
python3 -O -m unittest agents/structural-basis/tests/test_active25_outer_b4_i_block_v2.py
```

The two full independent reconstructions emit byte-identical audit results.
Acceptance of this denominator block does not establish or estimate the
target Rayleigh quotient.
