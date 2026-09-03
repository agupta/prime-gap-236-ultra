# Hostile audit of the C10 affine-transfer probe

Status: **ARITHMETIC AUDIT PASS; PROVENANCE FAILURE FOUND AND REPAIRED;
NOT THEOREM-READY**.

## Exact meaning checked

On the stratum

```text
R(t)=#{i:t_i>delta}=r,
L(t)=sum_{t_i>delta} t_i,
Z(t)=sum_{t_i<=delta} t_i,
```

the transferred function is

```text
F(t)=F0(t)*(a_r+b_r L(t)+c_r Z(t)).
```

For an I face with `r` large and `h` inclusion--exclusion-shifted small
coordinates, the channel polynomials are exactly

```text
1,
L = r*delta + X,
Z = h*delta + Y.
```

For J, `r` counts large *shared* coordinates.  If the distinguished fiber is
small (`Sdelta` or `Stotal`), the total count is `r`, `L` has no fiber term,
and `Z` receives `integral t F0 dt`.  If it is large (`Ltotal` or `Lbig`), the
total count is `r+1`, `Z` has no fiber term, and `L` receives that first fiber
moment.  `evaluate_j_r_transfer` combines these channels before branch
squaring.  The unordered four-branch loop is correct because the inherited
orbit product supplies factor two for distinct branches.  The final factor
`k=48` is applied exactly once.

The cutoff has the literal semantics

```text
a_r retained for all r=0,...,15;
b_r=c_r=0 only when r>linear_cutoff.
```

The staged I dictionary stores one triangle of each same-r 3-by-3 block;
off-diagonal entries are doubled exactly once during contraction.

## Independent D4 calibration

Contracting the exact 48-coordinate D4 forms after the `R<=10` cutoff gives

```text
I  = .999993563670784443250817792431637141212912777168565934094971214738062525332978...
48J= .934806639883815948929113407936071585792616960732673294757436390518844031520215...
q  = .934812656645828990698336238450542021055045412038003251437022453825592273199528...
```

The Decimal transfer agrees in all four forms through at least 74 significant
digits.  This checks the staged-I contraction, `r/r+1` branch insertion,
factor-two convention, `k` factor, cutoff, and 1,200-domain traversal against
the exact D4 matrix/direct artifact rather than the producer narrative.

## Smallest provenance counterexample and repair

Old transfer driver SHA
`f8e642c5fcccbd64f1cce3c515b7c2eec30b569776136c448c1ed0fc6ea50732`
authenticated only staged-I metadata.  Changing the single value

```text
((0,0),(0,0)):
  1.4799707088744639833...E-19  ->  1
```

and changing nothing else produced altered stage SHA
`4c37b9e8c7cf7c7e73aea31985206a01990aafb417681de3b7e603cecfe979df`,
process exit status zero, `gates_passed=true`, and quotient
`8.0756679931430627e-19`.  Thus the old gate was concretely fail-open.

The repaired transfer driver SHA
`91d1b4ad0c675ccfe36100166bee20bb4007af49e1d0cfe618c8c82c8857f354`
now requires the stage byte SHA before parsing, reads it once, checks it again
after J, requires the exact stage dependency dictionary, and pins the full
local transfer arithmetic closure:

```text
stratum_linear_transfer_decimal.py
stratum_linear.py
stratum_amplitude.py
grouped_fixed_vector.py
src/exact_integrator.py
```

It also pins the stage driver and imported robust solver.  Its four producer
tests (SHA
`5399df38abc2e5dac58a4f4514d1e5324d3479ca4d7517e0f45f1fe9fc48508f`)
pass.  Because the already-computed I stage did not itself record the
transitive `stratum_amplitude.py` hash, the repaired output deliberately says
`theorem_ready=false`.  A positive result would require a fresh end-to-end
stage or independent exact I reconstruction.

## Independent low-k oracle and D12 scope

`verify/affine_multiplier_oracle.py` (frozen SHA-256
`1d4cb452c376878fe4fa136008d3b5aeae237159e965c2c5ac56eb4642bc4a26`)
independently expands `F0`, evaluates I
with the square of the aggregate affine multiplier, derives both zeroth and
first distinguished-fiber moments, and sums all 16 *ordered* branch pairs.
It therefore shares neither the producer's channel assembly nor its implicit
factor-two convention.  Exact signed tests at k=2 and k=3 exercise both
small/large distinguished branches and cutoff semantics.  The companion test
(frozen SHA-256
`078fa3a508c5fa6181b816b9b9bf81d2c19d8450d1dbfd7266c9928ca5ff9bdf`)
also checks a signed degree-two multiplier at k=3 against both the monolithic
quadratic evaluator and its per-r direct-transfer implementation.  All three
tests pass in normal and optimized modes.  These are the intentionally
generalized post-affine-audit hashes; the earlier affine-only hashes
`3a105a06...` and `a4d57118...` are retracted and must not be used as pins.

This literal expanded-polynomial oracle is intentionally restricted to
`k<=4`.  A cache-free D12 checker should reuse the existing tagged-residual
backend as follows:

1. For I, keep `_tagged_i_square` and integrate every face with the extra
   affine factor `(a_r+b_r(r delta+X)+c_rY)^2`.
2. For J, derive tagged zeroth and first fiber-moment families.  On a small
   branch combine `A_r M_0+c_r M_1`; on a large branch combine
   `A_(r+1) M_0+b_(r+1) M_1`.
3. Extend the packed radial integrator from two to four independent affine
   tags (fiber slack, residual slack, left multiplier, right multiplier), or
   expand only the two degree-one multiplier affines after radialization.
4. Sum ordered branches and multiply by 48.  Run forward/reverse and one/two
   worker modes, with the k=2/k=3 literal oracle as the required regression.

No heavy D12 exact run is authorized by this audit unless discovery is
positive.

## Commands

```bash
python3 prime-gap-236/agents/small-delta-frontier/audit_affine_transfer.py
python3 -m unittest prime-gap-236/verify/test_affine_multiplier_oracle.py
python3 -O -m unittest prime-gap-236/verify/test_affine_multiplier_oracle.py
python3 -m unittest prime-gap-236/agents/exact-integrator/tests/test_stratum_linear_transfer_decimal.py
```
