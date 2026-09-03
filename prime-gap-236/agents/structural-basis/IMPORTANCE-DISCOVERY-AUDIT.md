# Hostile audit of importance-Ritz discovery infrastructure

## Verdict

**AUDIT PASS AFTER REPAIRS**, scoped to point evaluation, analytic
one-coordinate marginals, exact D4-oracle conversion, density adapters,
conditional-stratum normalizers, and the bounded J-envelope identities.
These components are discovery infrastructure only.  They do not produce a
rigorous integration error bound, a certified Rayleigh quotient, or any new
prime-gap theorem.

**BLOCKED:** the original ordinary global-chain full-matrix calibration in
`IMPORTANCE-RITZ-DESIGN.md`.  Its frozen missing-stratum rule is infeasible,
and its direct `m_i/m_0` J estimator has an actual cancellation-zero hazard.
The stratified/envelope design is the only audited continuation.  Even that
design is not a literally finite-sample unbiased MCMC method; it is an
asymptotically consistent discovery calculation with bounded J observables.

No D12 Markov chain or other heavy computation was run during this audit.

## Inputs and frozen repaired files

The initially audited point/sampler/design hashes were
`e006f998...`, `23f5a09d...`, and `874d9f8f...`; the initial oracle/density
hashes were `8c60c15b...` and `29190c12...`.  The following repaired files
supersede them:

| Component | Frozen SHA-256 |
|---|---|
| `code/importance_point_eval.py` | `ea88f6d29b744f59ad146bdebf9b2003a2d57e40eea5b7a03fb48f2309cdfc01` |
| `tests/test_importance_point_eval.py` | `d2ae3f04696626502122d850daa6cd2f6b82262353b1d7d5a84f5f042bbffc21` |
| `code/importance_sampler.py` | `54c936221fff3c2f981b98fee4110abfc384cf9b3e65d759b3997ff27c9812e4` |
| `tests/test_importance_sampler.py` | `e332eba3314149794f089b477d7339df1a5e2c891c0a0d4f6a1a56d4bcea8e00` |
| `code/importance_oracle.py` | `e58734919154fe841b42e9fcb49b05a61258bc6f892742756458ac16c85b0545` |
| `tests/test_importance_oracle.py` | `d29af0bb8fab05264757d8b17956e59cb1bb26c0248bcc6a655840abd201250f` |
| `code/importance_density.py` | `d656c788b3cbedf6029a95e74ac5a1cc9e8b6e3794ea9ca3d624af460ced9380` |
| `tests/test_importance_density.py` | `ab222509bbe157e45951cc430a9641b45543c1aecf8b725abfe72b349581d654` |
| `code/importance_stratum_weights.py` | `c2d8b4e7027f75b6701636fb31e377362afa42b3b6bc831ef97a0b7375705304` |
| `tests/test_importance_stratum_weights.py` | `0e4eae01a2f91750e6630eca3b37b0a9391a64465ba77c97056d790393941cfa` |
| `code/importance_envelope.py` | `7c28633e89987c6d2d3493d4f05e699914b5fb7a023d31ccb458878587bc7110` |
| `tests/test_importance_envelope.py` | `90ac791e01b2221772babb7039b71b1624a6bdc828d6f3d203ef6f73d58e96eb` |
| `tests/test_importance_hostile_crosscheck.py` | `ef2626aa714202f52c389ca297d929579a663f89e146bb38c70a5877c163db11` |
| `IMPORTANCE-RITZ-DESIGN.md` | `e2fcce57f9d053844b17fab62f028e9c296efae8b5dc7d877809d804b2cbbbd3` |
| `IMPORTANCE-STRATIFICATION.md` | `93cb320eb2c77f4382148d3f32367f96a1ebb2ac12447a9aebc1636540837595` |

The exact D4 oracle is byte-pinned to
`fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86`.
The D4 Decimal160 stratum traversal is pinned to `96e0655e...`; the explicit
unscaled-J D12 transfer fixture is pinned to `e83d3610...`.

## Independent algebra checks

### Orbit normalization and marginals

The monomial dynamic program has the correct normalization.  A state counts
how many coordinates have received each distinct exponent.  Updating states
in descending cardinality prevents a coordinate from being reused.  Equal
parts therefore select an unordered coordinate subset once; unequal parts
retain every assignment to distinct coordinates.  There is no missing or
extra repeated-part factorial.  The permanent hostile test exhausts all
partitions of lengths zero through four with parts one through four at a
signed rational four-point input and agrees exactly with literal orbit
enumeration.

For a common point with large count `r`, large sum `L`, small sum `Z`, and
total `s`, the independently recovered distinguished intervals are

```text
small: [0,min(delta,alpha-s)] if r=0 or L<=beta(r),
large: [delta,min(alpha-s,beta(r+1)-L)] if the upper end exceeds delta.
```

On the small branch the multiplier is `L^a(Z+t)^b`; on the large branch it
is `(L+t)^a Z^b`.  A deterministic 200-case rational test reconstructs
`t -> F(u,t)` by an independent Vandermonde interpolation and integrates
these multipliers literally.  It agrees exactly with every tested channel,
including repeated parts, `t=delta`, the `sum(u)=eta` boundary, and cap/total
upper-bound switches.

### D4 oracle and density adapter

The exact oracle now requires the complete 16 diagonal I blocks and exactly
the 876 canonical J entries: `16*21` within-stratum upper-triangle entries
plus `15*36` adjacent-stratum entries.  Missing and nonlocal J entries fail.
Each channel `(a,b)` is divided by `alpha^(a+b)`; a bilinear entry receives
the sum of both channel degrees.  Raw J is multiplied by 48 exactly once.

Independent constant-channel recombination gives

```text
I0 = sum_r I[(r,0,0),(r,0,0)],
B0 = 48 * (sum_r J_rr + 2*sum_r J_r,r+1).
```

These are exactly the normalizers emitted by the repaired oracle.  The
density adapter's constant tagged marginals sum to the directly integrated
`m0`; unnormalized versus normalized channels differ by the required alpha
power.  Active support strata are exactly 0 through 15: an explicit
15-large-coordinate point is accepted and its degree-zero feature occupies
offset 90, while the corresponding 16-large-coordinate point fails the C10
cap.

### Proposal detailed balance

For exact `Fraction` states, pair redistribution preserves the chosen pair
total and has conditional density `1/total` in both directions, for both
physical/physical and physical/slack moves.  Restricting the support to one
stratum adds only a symmetric rejection and needs no Hastings factor.

Floating states are not an exact reversible arithmetic model.  The original
code returned the explicit outside-simplex candidate

```text
state=(0.08713125686893501,0.14560806566611612,0.02026067746494888),
upper=.253, pair=(0,1), fraction=.03588663142896331,
sum(candidate)=.25300000000000006.
```

It now rejects that proposal without changing the state.  This is adequate
for heuristic discovery, but all normal-band claims must retain a numerical
kernel caveat; exact detailed balance is established only for the exact
arithmetic model.

## Concrete defects repaired

1. Basis and partition values were vulnerable to Boolean/nonintegral
   coercion; nonfinite point, coefficient, and parameter values were not
   uniformly rejected.
2. The sampler returned a floating outside-simplex state at a boundary.
   `reverse_fraction` also accepted the mismatched totals `(1e-20,0)` and
   `(2e-20,0)` at upper bound `.5`.  Both now fail closed, and malformed real
   scalars/pairs are rejected.
3. The original oracle used duplicate-key-tolerant JSON, did not bind the
   exact source hash, accepted noncanonical exact fields, accepted incomplete
   J support, and could silently treat missing entries as zero.
4. The density adapter silently applied `int(...)` to basis labels and did
   not pin its parameter artifact.  It now strictly parses exact vector data,
   validates basis dimension/order/distinctness, pins the exact oracle, and
   prebuilds the full distinguished-marginal partition evaluator.
5. The stratum-weight loader originally hashed a path and then reread it for
   parsing, allowing hash/parse TOCTOU.  It now reads once, rejects duplicate
   keys and underspecified Decimal normalizers, validates the exact C10
   parameter point, and requires the producer's J convention explicitly as
   scale `1` or `48`.
6. The first envelope guard bounded `z` by the observed number of nonzero
   constants; a leaked third tagged constant could therefore pass.  The
   adapter now validates channel metadata, permits nonzero constants only in
   final strata `r` and `r+1`, enforces at most two, reconstructs `m0`, and
   checks the absolute `z<=2` bound.

Every listed defect has a permanent normal and `python -O` regression.

## Rare strata and the bounded J repair

The exact D4 I probabilities include

```text
p13 = 1.0250326662413018e-7,
p14 = 7.349174419474934e-11,
p15 = 8.160396385878369e-18.
```

The capped D12 base traversal has tail probabilities about `1.0650e-9`,
`2.8220e-13`, and `4.6325e-20`.  An ordinary global chain cannot visit every
retained stratum at useful multiplicity.  Dropping those rows is forbidden;
the global full-matrix calibration is therefore retired.

The valid I decomposition is

```text
E_muI[HH^T] = sum_r (I_r/I0) E_muI,r[HH^T],
```

with a separate conditional target in every positive-weight stratum.  The
weights come from exact D4 I blocks or byte-pinned Decimal traversal buckets,
never from global-chain visit counts.

The direct J ratios have a real zero hazard.  With the exact D4 coefficients,
putting all 47 common coordinates equal to `z` gives, in the same common
stratum zero,

```text
m0(0) =
 110294507629667837212636441736309635471835667151011871138563
 / 3200000000000000000 > 0,

m0(1/200) =
 -285271895286769881553027313549556951762648658585209506388402297306140285921
 / 810000000000000000000000000000000000000 < 0.
```

For the D12 base, independent Decimal100 and Decimal180 evaluations agree in
sign along one fixed common-stratum-one segment:

```text
m0(101/10000,0,...,0) = 2.95481408665576414517e-14 > 0,
m0(101/10000,1/250,...,1/250) = -1.14574098851185847716e-22 < 0.
```

Thus neither pinned base has a usable positivity invariant.

For a finite retained marginal list, set

```text
g=sum_i m_i^2,  y_ij=m_i*m_j/g,  z=m0^2/g,
```

and sample the conditional common-stratum law `nu_r` proportional to `g`.
Then exactly

```text
E_nu,r[y_ij]=J_ij,r/Z_r,
E_nu,r[z]=J0,r/Z_r,
J_ij/J0=sum_r (J0,r/J0) E[y_ij]/E[z].
```

The bounds `0<=y_ii<=1`, `|y_ij|<=1/2`, and `0<=z<=2` follow immediately.
The stored `j_by_common_r` buckets are the right weights: the grouped code
accumulates each marginal product under the outer 47-dimensional large count
before summing over branch pairs.  The explicit producer scale check closes
the 48-versus-unscaled convention difference.

This exact identity removes cancellation singularities but does not make a
finite ratio-of-means estimator unbiased.  Exact iid draws would admit a
formal Russian-roulette reciprocal construction because `z` is bounded, but
no exact iid sampler or controlled-variance implementation exists here.
Ordinary conditional MH plus batch ratios remains discovery-only.

## Reproduction

From `prime-gap-236/`:

```bash
for t in \
  agents/structural-basis/tests/test_importance_point_eval.py \
  agents/structural-basis/tests/test_importance_sampler.py \
  agents/structural-basis/tests/test_importance_oracle.py \
  agents/structural-basis/tests/test_importance_density.py \
  agents/structural-basis/tests/test_importance_stratum_weights.py \
  agents/structural-basis/tests/test_importance_envelope.py \
  agents/structural-basis/tests/test_importance_hostile_crosscheck.py
do
  python3 "$t" && python3 -O "$t" || exit 1
done
```

The frozen run passes 47 tests in normal mode and the same 47 tests under
`python -O`.
