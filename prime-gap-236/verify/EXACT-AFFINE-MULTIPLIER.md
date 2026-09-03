# Independent exact affine-multiplier backend

Status: low-dimensional backend and strict multiplier parser complete; no
`k=48`, D12 integration has been launched.

Frozen implementation SHA-256:

```text
exact_affine_multiplier.py       9c21d73af25f63ad16c62a2a1935a9cfd3a8d134d7b7ada2620eddc12e1c3d3e
test_exact_affine_multiplier.py  1c6c62124f21804a03d80f7b30108b8a4137b5cccfe02dedd8c0a0e2861ca061
```

## Exact trust boundary

The backend consumes only:

1. checked `(residual power, orbit partition)` labels and exact rational
   coefficients represented by `build_basis_terms`;
2. a byte-SHA-pinned `exact-stratum-linear-rational-vector` artifact whose
   labels must be the complete contiguous order
   `(R,1),(R,L),(R,Z)`;
3. a checked `Parameters` object; and
4. the orbit, radialization, polygon, and tagged two-affine primitives in
   `exact_capped_certificate.py`, currently SHA-256
   `1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c`.

It reads no matrix entries, moment cache, Decimal output, eigenvalue, or
claimed quotient.  The multiplier parser requires its caller-supplied byte
SHA, exact status, exact-form and block/direct gates, `k`, canonical labels,
and canonical rational strings.  A cutoff keeps every constant `a_R` and
zeros only `b_R,c_R` for `R` above the cutoff.  It rejects omission of any
count active in I or either J distinguished-fiber class.

For I, the audited residual-tag square is radialized face by face and tagged
with the exact square of

```text
a_R + b_R*(R*delta+X) + c_R*Y.
```

For J, zeroth and first distinguished-fiber marginals are derived directly
from the unexpanded residual-power basis.  A small fiber uses count `R`, adds
the first moment with coefficient `c_R`, and puts its fiber coordinate in Z.
A large fiber uses count `R+1`, adds the first moment with coefficient
`b_(R+1)`, and puts its fiber coordinate in L.  Fiber-slack and residual-slack
powers remain tagged.  The two degree-one left/right aggregate multipliers
are expanded only after face radialization; the existing two-affine exact
geometry routine then handles the fiber and residual powers.  All 16 ordered
branch pairs retain separate accumulation slots.

The final invariant is simply

```text
I == sum_r exact_I_r,
kJ == k*sum_r exact_J_r,
I > 0,
kJ-I > 0.
```

Every face result is a `Fraction`.  Forward/reverse face order and one/two
fork-worker modes must agree bit-for-bit.

## Completed regressions

- A signed k=3 polynomial and all nonzero `1,L,Z` channels agree exactly with
  the literal expanded-polynomial, 16-ordered-branch oracle in both face
  orders and both worker modes.
- A constant multiplier reproduces the existing audited tagged I and J
  backend exactly.
- The cutoff parser at k=2 agrees with the literal oracle and retains only the
  intended high-R constants.
- Required-SHA and malformed-label mutations fail closed.
- Six further deterministic signed random k=2/k=3 cases agree exactly.
- The real D4 affine artifact (SHA
  `ffa607e0f2a8a3b6648f248efb13dc7ac2f1e7ef5809771f31c5f04b30f53158`)
  parses to 16 exact coefficient triples with the requested cutoff semantics.

Normal and optimized runs each complete the three formal tests in about 4.5
seconds on the current machine:

```bash
python3 -m unittest prime-gap-236/verify/test_exact_affine_multiplier.py
python3 -O -m unittest prime-gap-236/verify/test_exact_affine_multiplier.py
```

## Runtime scope

The current implementation is a correctness core, not yet the final D12
scheduler.  It radializes an ordered marginal product separately for several
branch intersections.  At D12 the base has 272 source labels and the audited
cost model for the *unmultiplied* optimized tagged backend already has 1,575
base orbits, 344,018 face-split calls, and a hostile 712,530 radial-key
ceiling per face.  The established base-checker planning range is roughly
30 minutes--8 hours serial (20 minutes--5 hours with two workers), but the
present affine correctness core repeats more radial work and therefore has no
defensible D12 wall-time estimate yet.

Before a D12 exact launch, benchmark the parsed affine vector on the C10 D4
polynomial, record target/radial counts and peak RSS, then cache the four
immutable small/small, small/large, large/small, and large/large radial
families once per face.  A positive Decimal sign is the gate for that work.
No timing estimate or low-k equality is evidence about the D12 sign.
