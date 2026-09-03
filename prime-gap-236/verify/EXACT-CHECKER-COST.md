# Static cost estimate for the independent exact checker

Date: 2026-09-01.  This estimate was produced without running either the
same-geometry C10 D4 regression or the C10 D12 integration.  The reproducible
count-only program is `verify/checker_cost_model.py`; it reads no certificate
data and performs no `Fraction` integration.

## Structural counts

The table contrasts the retained expanded/literal oracles with the production
tagged backend.  The oracles can contain every ordinary symmetric orbit
through degree `2D`; production retains residual powers, so its base orbits
have no part equal to one.

| count | C10 D4 | C10 D12 |
|---|---:|---:|
| expanded `F` orbit ceiling | 12 | 272 |
| expanded `F^2` orbit ceiling | 67 | 7,338 |
| nonempty `I` faces | 16 | 16 |
| `I` orbit/face slots | 1,072 | 117,408 |
| exponent-to-face assignment calls in `I` | 6,077 | 3,702,827 |
| `J` `S*S` orbit components | 67 | 7,338 |
| `J` `S*L_h` components, one order summed over `h` | 173 | 31,477 |
| `J` `L_h*L_l` components, grouped by `h+l` | 187 | 32,095 |
| ordered `J` component/face traversals | 17,062 | 2,968,878 |
| exponent-to-face assignment calls in literal `J` oracle | 80,925 | 73,085,161 |
| expanded-streaming `J` orbit/face slots | 1,072 | 117,408 |
| expanded-streaming `J` face-split calls | 6,077 | 3,702,827 |
| tagged no-ones base-orbit ceiling | 22 | 1,575 |
| tagged orbit/face slots | 352 | 25,200 |
| tagged face-split calls | 1,117 | 344,018 |
| tagged `SS`/`SL`/`LL` target maps per face | 9 / 35 / 45 | 25 / 247 / 325 |
| tagged ordered branch jobs over all faces | 106 | 106 |
| tagged ordered jobs after active IE shifts | 2,006 | 2,006 |
| boundary-measure jobs over all faces | 138 | 138 |
| boundary jobs after enumerating active IE shifts | 2,598 | 2,598 |
| hostile dense tagged radial-key ceiling, one face | 26,026 | 712,530 |
| transient moment-pair ceiling per polygon | 66 | 378 |

These are dense structural ceilings.  Exact coefficient cancellation can
lower them, but a dense D4 vector reaches these ceilings, so they are the
appropriate hostile planning numbers.
The assignment counts include multiplicity-class splitting but not the inner
large/small radial-degree products or polygon moment expansion.  Thus they
understate arithmetic operations, especially at D12.

The first streaming engine reduced the hostile dense `J` face-split count to
6,077 at D4 and 3,702,827 at D12.  Retaining residual powers reduces it again
to 1,117 and 344,018 respectively: about 72.4x and 212.4x below the literal
oracle ceilings.  This is not the whole runtime:
D12 still has larger rational numerators/denominators, radial degrees through
24, affine fiber powers through 26, and much more expensive initial orbit
products.  A simple split-count extrapolation remains optimistic.

## Runtime and memory estimate for the streaming code

Light, pre-pause microcases on the historical C20 geometry (not a full
regression and not the target specialization) took about 0.06 seconds for the
constant D4 orbit and about 1.5 seconds for the hard `1^8` orbit.  These are
only scale markers.

- **C10 D4:** static planning range is about 10 seconds to 2 minutes on one
  process.  The wide range covers exact-integer growth and the initial orbit
  products, neither represented by the split count.  Two workers affect only
  the face phase, so a plausible speedup is 1.3--1.8x rather than 2x.
- **C10 D12:** static planning range is roughly 30 minutes--8 hours on one
  process.  Two face workers may reduce this to roughly 20 minutes--5 hours if
  memory bandwidth and copy-on-write behavior remain favorable.  The range is
  still broad because 597 possible `(family,fiber,residual)` maps can fan out
  into large exact radial dictionaries even though only 344,018 face splits
  and 2,006 active ordered geometry batches remain.

The tagged radial maps are face-local and are discarded before the next `r`.
A deliberately loose dense ceiling is 712,530 tagged radial entries on one
D12 face and 26,026 on D4 after impossible IE shifts are pruned.  Actual degree
correlations and cancellation should lower both.  Each polygon's moment map is transient and has at most 378 distinct
degree pairs at D12 (66 at D4), although their absolute exponents include the
Dirichlet dimension offsets.  Pure-expression LRU caches are explicitly
bounded: 16,384 orbit products and 8,192 entries for each radial/literal
moment helper.  Two workers duplicate face-local maps and some cache pages, so
the two-worker D12 run still needs a memory check after C10 D4.

This is why the D12 guard must remain in place.  The estimate is not evidence
about the sign of the capped margin.

## Bottlenecks

1. **The literal and expanded oracles rebuild or enlarge face structure.**
   The translation/inclusion-exclusion/Dirichlet transform of an orbit
   `P_nu` depends on `(nu,r,delta)`, not on the branch domain or marginal
   affine power.  Rebuilding it accounts for most of the 73,085,161 D12 calls.
2. **Tagged radial fanout is now the main face-memory risk.**  Many orbit
   splits land on the same `(upper-face count,X power,V power)` key, but the
   additional fiber/residual tag pairs must coexist until a complete ordered
   branch batch is assembled.
3. **Ordered reverse pairs need separate accounting.**  The streaming engine
   retains a separate result slot and geometry evaluation for each direction,
   while sharing only the immutable radial polynomial derived from their
   common product.  There is no hidden factor two.
4. **Two exact affine tags enlarge the coefficient state.**  Avoiding exponent
   ones saves face splits, but `(fiber_power,residual_power)` creates as many as
   597 target maps at D12.  They must be combined into one moment polynomial
   per ordered branch/shift before triangulation.
5. **Initial orbit algebra is still serial.**  Building `F^2` and the three
   marginal-product families occurs before the face split and can dominate
   once face transforms are cheaper.
6. **Exact big-integer triangle batches remain a risk.**  Clipping is now once
   per active IE shift and requested moments are batched, but the factorial
   affine expansions can still grow expensive at D12.

## Independent streaming redesign

The implemented changes preserve the trust boundary: all tables start empty,
are derived from the checked labels/coefficients, and are discarded without
serialization.

1. Stream one large-coordinate face `r` at a time.
2. Retain the checked residual power and use
   `(1-S)^b=sum_c binom(b,c)(1-alpha)^(b-c)(alpha-S)^c` for `I`.
   For `J`, derive the finite Definition-5 antiderivative directly and retain
   `(fiber_slack_power,(1-U)_power)`.  No exponent-one residual partitions are
   constructed in production.
3. For every no-ones orbit occurring anywhere in `I` or a marginal product,
   construct
   its exact radial face transform once:

   ```text
   (nu,r) -> {(h,x_power,v_power): rational coefficient}
   ```

   Distribute that transform to every `(family,fiber,residual)` coefficient
   that uses it, then drop the transform immediately and discard all radial
   maps at the end of the face.  This reduces the D12 face-transform ceiling
   from about 73 million assignment calls to about 344 thousand.
4. Before geometry, linearly combine all tagged radial terms for one ordered
   branch and IE shift into a single `(X_power,V_power)` moment polynomial.
   Clip and triangulate once for that complete batch.
5. Preserve all four ordered branch labels and all 16 ordered pair slots.
   Reverse pairs share a radial input but are evaluated into distinct slots;
   complementary intersections still reach geometry and must have zero area.
6. For each clipped polygon, expand each distinct affine x/y power once per
   triangle and return all requested moments as one batch.  The old scalar
   factorial formula remains unchanged as a test oracle.
7. Bound every persistent pure-expression cache, prune IE shifts that cannot
   satisfy the total bound, and retain no cross-face radial state.
8. Offer exactly two deterministic contiguous `r` blocks under `fork`.
   Immutable polynomials are inherited copy-on-write, workers return only
   exact per-face Fractions, coverage is validated, and the parent sums in the
   requested canonical face order.

The expanded streaming and literal term-by-term engines both refuse `k>4`.
The tagged production engine agrees with both on constant, signed, capped,
interior cap/total-switch, and mixed degree-4 cases at `k=2,3,4`, in both face
orders and in serial versus two-worker mode.  The estimates above are not
evidence about the sign of either certificate; the same-geometry C10 D4
reconstruction is still the required first full regression.

## Why historical C20 is not the specialization regression

The existing C20 artifacts encode
`alpha=163/625`, `eta=627/2500`, and `delta=1/50`.  Exactly,
`alpha-eta=1/100`, not `1/50`.  Therefore their `J` geometry has a genuine
intermediate small-total branch and cannot exercise the target-only identity
`alpha-eta=delta`.  The checker deliberately rejects that tuple rather than
weakening target validation.  The regression replacement uses degree 4 with
the final C10 support constants, so it tests precisely the ordered geometry
that D12 will use.
