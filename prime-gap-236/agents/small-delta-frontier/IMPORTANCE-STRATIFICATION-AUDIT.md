# Independent audit of importance stratification

Verdict: **SCOPED MATHEMATICAL PASS, WITH ONE CONCRETE ARTIFACT-CONVENTION
COUNTEREXAMPLE.**  The conditional expectation identities and the C10
fixed-stratum pair kernel are correct modulo null boundaries.  A bare field
named `j_by_common_r`, however, does not have a uniform factor-48 convention
across the existing grouped producers and must not be fed generically to the
current weight loader.

This audit is static and discovery-only.  It does not validate Monte Carlo
confidence bands or a sieve quotient.  Audited document SHA:
`31cbf95dd181f5e19bb2391ad0df728bc4d67e7b871c70e44f1866af6042e419`.

## 1. Exact conditional J normalizer

Let `C_r` be the common-coordinate region with exactly `r` coordinates
strictly above `delta`.  At a fixed common point, decompose the base marginal
as

`m_*(u)=S_r(u)+L_r(u)`,

where `S_r` integrates a small distinguished coordinate and `L_r` a large
one.  Consequently

`J_r = integral_Cr (S_r^2 + 2 S_r L_r + L_r^2)`.

The grouped recurrence realizes exactly this identity:

- `stratum_amplitude.py:114-122` classifies branch products as small-square,
  cross, and large-square; the cross product already carries its factor two;
- `stratum_amplitude.py:148-178` integrates all branch intersections and
  returns `(S2_r,twoSL_r,L2_r)`;
- hence the sum of that tuple is exactly `J_r`, before the sieve's factor
  `k=48` is inserted.

Thus `J_r` is the normalizer of the conditional `mu_J` density
`m_*^2/J_r`.  Multiplying every `J_r` by 48 leaves the mixture weight
`J_r/sum_s J_s` unchanged, but it changes which serialized total it should
match.

The envelope repair in `IMPORTANCE-STRATIFICATION.md:46-79` is also
algebraically exact.  With `g=sum_i m_i^2`, `y_ij=m_i m_j/g`, and
`z=m_*^2/g`,

`E_nu_r[y_ij]/E_nu_r[z] = J_ij,r/J_r`.

Multiplication by `w_r=J_r/J_*` gives `J_ij,r/J_*`; summing `r` proves the
display at lines 66-70.  At a fixed common point, only the two constant tagged
marginals for the small and large distinguished branches enter `m_*`, so
`m_*^2 <= 2 g` and `0<=z<=2`.  A simultaneous zero of all retained marginals
has zero envelope density.

## 2. Smallest serialized counterexample: the factor-48 convention

There are three different objects under closely related names:

1. `evaluate_all_blocks()` stores `j_by_common_r` as a tuple
   `(S2,twoSL,L2)` (`stratum_amplitude.py:229-250`), not a scalar normalizer.
2. The transfer producer stores scalar, **unscaled** `J_r` and defines
   `numerator=48*sum(j_by_r)`
   (`stratum_linear_transfer_decimal.py:270-312`).
3. The affine-space pilot explicitly multiplies every contracted stratum by
   48 before storing `baseline_j_by_common_r`
   (`stratum_linear_decimal.py:490-501,577-585`).

Concrete pinned data expose the mismatch.  In
`c10_D12_affine_transfer_decimal100_cut11.json` (SHA
`e83d3610b8130d743757a5f01aacc6ff2d2b2acd3128e5ff21b9a01cfa53d8da`),

`sum(j_by_common_r)/numerator = 0.020833333333... = 1/48`

to the recorded precision.  Passing this artifact with empty prefix to
`load_stratum_weights` fails its lines 60-71 check, which requires the J list
to sum to the already factor-48 numerator.  By contrast, the D4 Decimal160
pilot (SHA
`96e0655e0ace238cc561aa654d1facb8ac1e93257835f3ad174efef42d09d42e`)
stores `baseline_j_by_common_r=48J_r`; its sum matches
`baseline_numerator` to the advertised rounding error.

This is not a mathematical error in the weights—normalizing cancels a common
48—but it is a fail-closed schema issue.  Required repair before a new D12
importance run: bind an explicit exact convention such as
`j_values_scale_to_J=1` or `j_values_scale_to_numerator=1`, reject tuple-valued
blocks, and either multiply unscaled values by 48 or compare them to
`numerator/48`.  Merely matching the field name `j_by_common_r` is
insufficient.

## 3. Proposal symmetry

For a selected augmented pair `(i,j)`, let its invariant total be `T`.  A
uniform fraction `f` proposes `(Tf,T(1-f))`.  With respect to coordinate
length on that line, the proposal density is `1/T`; `T` is identical in the
reverse move.  Uniform pair selection is also identical.  This is exactly
what `importance_sampler.py:69-118` implements and tests via the recovered
reverse fraction.  Rejecting a candidate outside the fixed-R support simply
restricts this symmetric proposal kernel.  Therefore the Metropolis ratio at
lines 121-160 needs only the target-density ratio; no missing Hastings factor
was found.

## 4. C10 fixed-R connectivity and symmetric observables

For a fixed labeled set `S` of large coordinates, the I stratum cell is the
intersection of

- `t_i>delta` for `i in S` and `0<=t_i<=delta` otherwise,
- `sum_i t_i<alpha`, and
- `sum_{i in S}t_i<=beta(r)` when `r>0`.

Its relative interior is convex.  Physical--slack redistributions generate
the coordinate directions, so finite sequences of sufficiently small such
moves reach every open neighborhood in the same cell.

For the C10 common-J support, a large distinguished branch never adds a
separate component.  Exact inequalities are

`beta(r+1)-delta <= beta(r)` for every `r>=1`:

- `3/20-1/100 = 7/50 <= 3/20` for `r=1`;
- `97/625-1/100 = 363/2500 <= 3/20` for `r=2`;
- `363/2500 <= 97/625` for `r>=3`.

Also `alpha-eta=delta=1/100`, so every common point with
`sum u<=eta` and the common cap has a nonempty small distinguished interval.
Thus, modulo endpoints, each fixed labeled common-J cell has the same convex
form with upper total `eta`.

Different labeled cells communicate.  Select large `i` and small `j`.  The
exact swap fraction `f=t_j/(t_i+t_j)` interchanges their values, preserving
total sum and large sum.  At an interior point, an open interval of nearby
fractions still has `i` small and `j` large and stays within both caps, so the
transition has positive proposal probability.  Boundary points can first be
moved into the relative interior unless the stratum has zero target mass.
Therefore the kernel is irreducible on the positive-density relative
interior, modulo algebraic zero sets and Lebesgue-null support boundaries.

Even without using the exchange step, the polynomial, target densities, and
retained observables are permutation symmetric.  Coordinate permutation maps
any labeled-R cell measure-preservingly to any other, so every symmetric
conditional expectation is identical across cells.  This gives a weaker but
sufficient scoped lemma for the stated symmetric observables.  It does not
justify nonsymmetric diagnostics or a claim of irreducibility from every
boundary point.

## Scope and required wording

The exact decompositions in `IMPORTANCE-STRATIFICATION.md:20-44,46-79` and
the proposal-symmetry claim at lines 94-103 pass.  Any production description
should say “irreducible on positive-density relative interiors modulo null
boundaries,” not unqualified pointwise irreducibility.  It must also name the
factor-48 serialization convention rather than treating every
`j_by_common_r` field as the same scalar list.
