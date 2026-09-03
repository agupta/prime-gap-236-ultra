# Runtime choices for rigorous scalar D12 certification

Status: design and operation-count analysis only; no D12 certification run was
launched for this note.

The finite decision is only

\[
I(F)>0,\qquad M(F):=48J(F)-I(F)>0.
\]

No matrix, eigenvalue, or positive-definiteness assertion is needed.  The three
reasonable arithmetic routes are exact rational arithmetic, outward-rounded
dyadic intervals, and denominator-cleared integer/modular arithmetic.

## 1. Normalize the vector before every rigorous route

The 272 stored coefficients have 43 distinct denominators.  Their least common
multiple `L` has 714 bits (215 decimal digits).  After replacing

```text
F by F_tilde = L*F,
```

all 272 coefficients are integers of at most 714 bits and have gcd one.  Since

```text
I(F_tilde) = L^2 I(F),
48 J(F_tilde) = L^2 48 J(F),
M(F_tilde) = L^2 M(F),
```

the quotient and both required signs are unchanged.  The checker should print
`L`, its bit length, and the SHA-256 of the unscaled ordered vector.  It should
keep the scaled forms rather than divide by `L^2` at the end.

This normalization removes the 210-digit coefficient denominators from every
subsequent product and gcd.  It is safe for the existing exact evaluator: add
an `--integer-scale-vector` option which computes `L` with `math.lcm`, replaces
the parsed coefficients by integer `Fraction`s, and records
`forms_scaled_by=L^2` in both the I-stage and final output.  Resume validates
`L` and the unscaled vector hash.

The exact C10 support constants have common denominator

```text
Q = lcm(denominators(alpha,eta,delta,beta1,beta2,beta3plus))
  = 300000.
```

This small `Q` is useful for both interval and integer clearing below.

## 2. Route A: exact `Fraction`

### Construction

Run the audited face-grouped scalar evaluator with the integer-scaled vector,
`fractions.Fraction`, exact positive-domain prefilters, and two fork-by-r
workers.  It reconstructs every coefficient, orbit factor, polygon moment,
`I`, and `J`; there is no error term.  Retain the I-stage checkpoint and require
both the grouped-script and imported-integrator hashes to match on resume.

The final proof is simply

```text
scaled_I.numerator > 0
scaled_margin.numerator > 0
```

after normal Fraction reduction.  The independent checker described in
`FINAL-CHECKER-SPEC.md` then reconstructs the same signs by a different
geometry formula.

### Runtime expectation

On the final implementation, capped C20 D4 took 2.22 seconds at MP80 and 12.42
seconds exactly, a 5.6-times ratio.  D12 has much larger intermediate integers,
so an unscaled exact run could plausibly cost 5--20 times the completed D12
MP wall time.  Integer-scaling should remove many large gcds; a provisional
range is 2--8 times MP, but it must be calibrated on four complete r-strata
before extrapolation.  These are estimates, not bounds.

### Assessment

This is the safest primary route.  Its code path is already audited, its output
is an exact equality, and it requires no numerical error proof.  Start here if
the MP candidate has a positive margin and the calibrated runtime fits.  Do not
replace it merely because interval arithmetic looks faster.

## 3. Route B: rigorous dyadic intervals

This is the preferred independently checkable runtime fallback.  It uses
Python integers for directed rounding and therefore does not depend on the
host floating-point rounding mode, Decimal context behavior, MPFR, or an
external interval package.

### 3.1 Fixed-point interval type

At precision `P`, store an interval as two integers `(lo,hi)` representing

\[
[lo/2^P,hi/2^P].
\]

For an exact rational `n/d`, `d>0`, construct

```text
lo = (n << P) // d
hi = -((-(n << P)) // d)
```

using Python's floor division.  The operations are:

```text
[a,b]+[c,d] = [a+c,b+d] / 2^P
-[a,b]      = [-b,-a] / 2^P
```

For multiplication, compute the four integer products, let `u` and `v` be
their minimum and maximum, and set

```text
new_lo = u // 2^P
new_hi = -((-v) // 2^P).
```

Multiplication or division by an exact signed integer/rational gets a dedicated
outward-rounded operation.  Exponentiation uses repeated squaring.  Every
operation has a one-line integer proof that its result contains the exact real
operation; negative operands are covered by the four-product rule and floor
division.

### 3.2 Keep all branching and geometry exact

Support feasibility, branch selection, polygon clipping, and zero-area tests
must use exact `Fraction`s.  Thus no interval comparison decides which domain
is integrated.  Construct each rational polygon exactly.  Compute a monomial
moment either by the independent affine-triangle formula from
`FINAL-CHECKER-SPEC.md` and round its final rational outward once, or propagate
dyadic intervals through that formula.  The first choice gives tighter bounds
and a smaller audit surface.

Use the integer-scaled coefficient vector.  Combinatorial and orbit
coefficients remain exact integers.  Convert only support powers, marginal
antiderivative factors, and exact monomial moments to outward dyadic intervals.
Accumulate the complete face polynomial and its integral with interval
addition.  Enumerate ordered J branch pairs in the independent checker so no
producer factor-two convention is trusted.

### 3.3 Explicit final error bound

The enclosure proof is structural induction on the arithmetic expression:

1. every rational leaf is enclosed by its floor/ceiling construction;
2. every addition, negation, product, and rational scale preserves enclosure;
3. exact face selection covers precisely the mathematical integration domains;
4. finite summation therefore gives
   `[I_lo,I_hi]/2^P` containing `I(F_tilde)` and
   `[M_lo,M_hi]/2^P` containing `M(F_tilde)`.

The certificate prints the four endpoint integers and

```text
I_absolute_width = (I_hi-I_lo)/2^P
M_absolute_width = (M_hi-M_lo)/2^P.
```

The rigorous decision is exactly

```text
I_lo > 0 and M_lo > 0.
```

For an additional audit margin require `M_lo > 4*(M_hi-M_lo)` when practical;
this is not logically necessary.  Run at `P`, then at `P+256` or `2P`, and in
reverse face order.  All runs may give different enclosures, but each must
contain the intersection and have a positive lower endpoint.  Start at 512
bits and double until the sign separates.  Because the expected quotient gap
is macroscopic relative to 512-bit rounding, 512--2048 bits is the anticipated
range, not an assumption.

### 3.4 Runtime and memory

An interval scalar carries two fixed-size integers and a general multiply uses
four integer products.  Orbit enumeration, exact geometry, and monomial
moments are shared.  At 512--1024 bits, expect roughly 3--10 times the MP scalar
wall time and 2--4 times its live scalar memory.  At 2048 bits, budget 5--20
times MP.  Unlike Fraction, bit sizes are capped by `P` and there is no gcd
normalization.  Two fork workers remain reasonable if a four-r-stratum trial
keeps combined RSS below 6 GiB.

### Assessment

This is the safest *independent error-bounded* route.  It reconstructs the
whole scalar expression, makes every rounding direction executable and
reviewable, and exposes the total error as final integer widths.  If exact
Fraction runtime is unacceptable, a positive dyadic lower bound is itself a
rigorous certificate under the task's outward-interval allowance.

## 4. Route C: denominator-cleared integer evaluation

Exact integer accumulation can be faster than both Fraction and intervals, but
the denominator-clearing proof is an additional place to make a fatal mistake.
It is a useful second exact implementation, not the first certificate route.

### 4.1 Stream rational contributions into one integer

With `F_tilde`, every vector coefficient is integral.  Enumerate each final
face/monomial contribution as a pair `(n,d)`, `d>0`, without adding it to a
global Fraction.  Choose a positive common denominator `D`, require explicitly

```text
D % d == 0
```

for every streamed term, and accumulate

```text
S += n*(D//d).
```

Then `S/D` is exactly the desired form.  Use separate `S_I` and `S_M`, or one
common `D` for both.  The sign is the sign of `S`.

For C10 all polygon vertices have denominators dividing `Q=300000`: the
halfplane normals are `0,+/-1`, so clipping introduces no arbitrary determinant
denominator.  Total polynomial degree is bounded by the 48-dimensional volume
degree plus twice the basis degree.  A deliberately conservative candidate is

```text
D0 = Q^100 * (100!)^8,
```

about 6100 bits.  It is not trusted merely from this display: the code must
prove coverage by checking `D0 % d == 0` for every generated contribution and
abort at the first failure.  A sharper lcm can be built in a denominator-only
first pass, but two full enumerations may cost more than the extra 6100-bit
arithmetic.  Cache `D0//d` by denominator in memory.

Also accumulate the exact triangle-inequality bound

```text
B = sum(abs(n)*(D//d)).
```

This gives `abs(S)<=B` and is useful for a modular cross-check.

### 4.2 Modular variant

One may compute `S mod p` for deterministic primes and combine by CRT.  To infer
the signed integer, the accumulated modulus `Pcrt` must satisfy

```text
Pcrt > 2*B.
```

Then the symmetric CRT representative is the unique `S` in `[-B,B]`.  Every
prime must have a reproducible primality proof, and any denominator-inverse
formulation must reject primes dividing a denominator.

For the expected several-thousand-bit bound, 61-bit primes require on the order
of 100 full modular evaluations.  Pure Python is therefore unlikely to beat
one direct 6000--10000-bit integer accumulation, even though the prime runs are
parallel.  CRT is best retained as a residue cross-check of the direct integer
answer, not as the primary sign proof.  Rational reconstruction with unknown
denominator is less attractive still: it needs simultaneous numerator and
denominator bounds and adds ambiguity that the fixed common denominator avoids.

### Runtime assessment

Direct denominator-cleared accumulation should cost about 2--6 MP scalar
times if the term stream reuses face densities and monomial moments; this is an
unmeasured estimate.  Its memory is small: one several-thousand-bit accumulator,
the denominator-factor table, and the ordinary face workspace.  The proof
burden is higher than the interval route because every denominator source and
the stream-to-integral correspondence must be audited.

## 5. Recommended certification sequence

1. Finish MP discovery and record the actual relative margin and scalar wall
   time.
2. Run the integer-scaled exact Fraction evaluator.  It is the primary result
   if its calibrated runtime fits.
3. Independently run the cache-free directed-dyadic checker, first at 512 bits
   and then at a higher precision/reversed face order.  Record exact endpoint
   integers and widths.
4. Implement denominator-cleared direct integer accumulation only if Fraction
   runtime threatens the wall or as an additional exact cross-check.  Require
   per-term divisibility; do not rely on an informal global denominator claim.
5. Use modular residues only to audit an exact integer result unless CRT has
   crossed the explicit `2B` uniqueness threshold.

The strongest and safest package is therefore **exact scaled Fraction plus an
independent directed-dyadic lower bound**.  If only one route completes, exact
Fraction is preferred; if it cannot finish, the dyadic interval construction
is the safest independently checkable rigorous fallback.  Neither route reads
a serialized matrix or persistent moment cache.

## 6. Mandatory implementation tests

- Exhaustive small signed rational tests for interval conversion, addition,
  subtraction, multiplication, rational scaling, and powers; compare every
  result with exact Fraction containment.
- Negative-endpoint tests proving floor/ceiling directions are correct.
- Exact polygon moments must lie in their dyadic enclosures for random small
  rational triangles.
- Capped C20 D4: the interval contains the independently known exact `I`, `J`,
  and negative margin; increasing precision narrows it.
- Small `k=1,2,3,4` full forms, including both zero-dimensional branch ties,
  agree with exact pairwise reconstruction.
- Integer scaling leaves exact quotients unchanged and multiplies both forms by
  precisely `L^2`.
- Every integer-stream denominator divides `D`; deliberately deleting one
  factorial or support factor must trigger a failure.
- CRT reconstruction is accepted only after `Pcrt>2B`; one-prime and truncated
  residue files fail closed.
- Normal/reverse face order and serial/fork execution produce compatible
  positive intervals or identical exact integers.
- A partial face limit, missing hash, stale dependency, malformed endpoint, or
  nonpositive lower margin can never print `PASS`.
