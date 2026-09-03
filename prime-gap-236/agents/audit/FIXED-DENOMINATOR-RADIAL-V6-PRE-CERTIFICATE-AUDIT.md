# Fixed-denominator radial v6 hostile pre-certificate audit

## Verdict

**SCOPED PRE-CERTIFICATE AUDIT PASS** for the frozen, previously unlaunched
v6 bundle:

```text
backend  agents/exact-projection-engine/fixed_denominator_radial.py
         430d6376d803abaad40c3bf9fb88d5f4db75ad144649e8c9446d47f1e771b228
tests    agents/exact-projection-engine/test_fixed_denominator_radial.py
         a02f51377800e4906e711da2cd62bd4f406999b73d8bb58dfa2e6d0eb1ed2f45
runner   agents/exact-projection-engine/d14_grid38_scaled_b_shard_fixed_v6.py
         89c7c57aa439b0535bd17b85683dd1fd4ece2d1439e1b5d8bd9562c44eb57e17
```

No target result existed when this source verdict was issued.  Every v6
target shard still requires a fresh result-level audit and, where a same-r v5
shard exists, exact equality of the mathematical fields.

## Independent denominator proof

Let `delta=a/q` be reduced, let `T` be the degree of an orbit monomial, let
`E>=T` be the maximum orbit degree in the active families, and write `d_L`
and `d_S` for the degrees selected after expanding the large and small
coordinates.  A combined radial coefficient has possible denominator

```text
q^(T-d_L-d_S)
* (d_L+r-1)!
* (d_S+s-1)!,                       r+s=n,
```

where the factorial for a zero-dimensional aggregate is instead `0!=1`.
Thus its product-radial powers have total at most

```text
E+n-2       if r,s>0,
E+n-1       if r=0 or s=0.
```

For nonnegative `u,v`, `u!v!` divides `(u+v)!`; every smaller factorial then
divides `(E+n-1)!`.  Also

```text
q^E * (a/q)^(T-d_L-d_S)
 = a^(T-d_L-d_S) q^(E-T+d_L+d_S)
```

is integral.  Consequently

```text
D = q^E (E+n-1)!
```

clears every coefficient, including `r=0`, `s=0`, the empty partition, and
top-degree terms.  This is the exact integer `delta_scale` and factorial
division implemented by v6.

If the integer numerators under `D` are `N_i`, their reduced denominators have
LCM

```text
D / gcd(D,N_1,N_2,...).
```

The global gcd reduction therefore recovers exactly the same transform-level
common denominator as the audited Fraction/v3 implementation.  It is not an
unproved heuristic denominator bound.

## Independent coefficient and branch tests

The hostile oracle enumerates every distinct monomial in a symmetric orbit,
all `binomial(n,r)` choices of the labelled large face, and the Cartesian
large/small coordinate expansions.  It does not call the v3 transform or the
v6 falling-factorial helpers.  It agrees coefficient-by-coefficient with v6
for:

- `n=0,...,5`, every face `r`, all surviving shifts through three;
- empty, odd, repeated, and mixed partitions;
- `delta=1/6,2/5,7/11`, exercising nonunit delta numerators;
- zero-large, zero-small, empty-partition, and top-shift cases.

Forty deterministic random packed-family cases independently recover the LCM
of the literal coefficients and agree exactly with both v6's denominator and
the audited v3 integer maps.  Target-dimension tests at `n=47` cover
`r=0,1,11,12,46,47`, shifts including the frozen `14-r` boundary, and orbit
degrees through 44.  They agree exactly with v3.

An exact target-geometry band test uses `k=48`, the frozen rational endpoints,
`eta`, `delta`, and nonuniform schedule.  For `r=0,11,12`, v6 equals collected
v5 in the total and every high/low branch under normal and optimized Python.
The recorded maximum shift is exactly `14-r`.  At `r=12`, the endpoint job
lists contain no distinguished-large branch, so and only so the entire
`large` family is removed before radialization; `small` and `small_total`
remain.  At `r=0,11`, all three families remain.  This proves that pruning is
by actual endpoint use rather than a guessed count cutoff.

## Cache, inventory, and runner closure

The two cached falling-factorial convolutions depend only on the exponent
tuple (and, for the small side, zero count and maximum shift).  Delta, face
multiplicity, denominator, and family coefficients are applied outside the
caches, so omitted cache keys cannot contaminate a later exact call.

The work fields have the following checked meanings:

```text
orbit_tag_associations       nonzero active family/tag/partition incidences
orbit_transforms             distinct active partitions
transform_terms              nonzero terms after shift pruning, before distribution
distributed_terms            transform-term/incidence products attempted
packed_nonzero_terms         nonzero rows after family/tag cancellation
maximum_orbit_degree         E over active partitions only
factorial_ceiling            E+n-1
fixed_*_bits                 bit lengths, not operation counts
```

Family pruning can change these fields and the transform denominator relative
to an unpruned v3 job while leaving every branch value identical.  Therefore a
later checker must not demand v5/v3 equality of performance metadata.

The runner recursively pins and snapshots the complete v5, v2, base, fixed
backend, and test closure; all live hashes matched.  It rechecks every byte
after computation and publishes through the already audited same-directory
temporary file plus `link(O_EXCL)`/file-fsync/directory-fsync implementation.
The concurrent-publication regression is pinned at
`855b3e07ee71f75917a9ddceb2d969e10aab8c81550aa036423f7104eb5ef78d`.

## Commands and independent artifact

```bash
python3 agents/exact-projection-engine/test_fixed_denominator_radial.py
python3 -O agents/exact-projection-engine/test_fixed_denominator_radial.py
python3 agents/audit/test_fixed_denominator_radial_v6_independent.py
python3 -O agents/audit/test_fixed_denominator_radial_v6_independent.py
```

The production suites pass 3/3 under each interpreter.  The independent suite
passes 7/7 under each interpreter.  Its SHA-256 is recorded after its final
normal/-O run alongside this report.

## Remaining gate

This audit authorizes a target run; it does not certify one.  A shard is usable
only after a separate checker verifies its canonical schema, exact source
closure and producer hash, `H=14-r`, active/inactive family sets, denominator
and gcd inventory, all four/two expected branches, exact single-factor-48
recombination, and exact mathematical-field equality with any available v5
reference.
