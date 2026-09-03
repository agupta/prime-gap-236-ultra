# Direct Bombieri--Vinogradov support at `A_1=1/4`

This is an independent analytic support family for Proposition 1 of
Stadlmann v1 (`prop:GPYsieve`).  It does **not** use Propositions 2 or 3, the
Harman minorant, or any claimed distribution beyond the classical
Bombieri--Vinogradov theorem.  It reduces the remaining `k=48` problem to the
finite-dimensional `M_{48,epsilon}`-type variational calculation described
below.

## Exact parameters

Let

```
k = 48,                 n = 1,
A_0 = -e,               A_1 = 1/4,
0 < e < 1/4,            delta = 7/250,
R = A_1+e = 1/4+e,      V = A_1-e = 1/4-e,
B_{1,m} = R             (1 <= m <= floor(1/delta)).
```

Here `e` can be **any** fixed positive rational below `1/4`; in particular
`e=1/10000` and `e=1/100000` are legitimate.  There is no lower bound on `e`
in Definition 1 or Proposition 1.

Definition 1 is satisfied:

* `e>0` and `delta>0`;
* `A_0=-e<A_1=1/4<1/2-e`, the last inequality being equivalent to `e<1/4`;
* `delta<R`, since `7/250<1/4<R`;
* `B_{1,m}=B_{1,m+1}` lies between `B_{1,m}` and
  `B_{1,m}+delta`.

Moreover its support is exactly the open full simplex (up to a null
boundary)

```
T_k = {t_i >= 0 : t_1+...+t_k < R}.
```

Indeed the stratum condition on the total sum is `[0,R)`.  For
`I={i:t_i>delta}`, its subsidiary condition is automatic because
`sum_{i in I}t_i <= sum_i t_i<R=B_{1,|I|}`.  Conversely every point in the
defined support has total sum in `[0,R)`.

The constant schedule is already maximal for the support: any schedule with
all `B_{1,m}>=R` gives the same full simplex.  Consequently count-dependent
optimization of `B_m` cannot enlarge this particular support.  (Values below
`R` only delete points.)

## Every relevant modulus is below the BV level

Fix the `epsilon_0>0` appearing in Definition 2.  For any representation of a
modulus `q` in any one of the sets `Q(...)`, put

```
X  = e_0  f_1 ... f_m,
X' = e'_0 f'_1 ... f'_{m'}.
```

(The subscripts on `e_0,e'_0` here distinguish the smooth integer factors
from the support parameter `e`.)  The two total-product inequalities in
Definition 2 give, exactly,

```
log_x X  <= (1-epsilon_0)(A_1-e),
log_x X' <= (1-epsilon_0)(A_1+e).
```

Since `q=XX'`, addition cancels the support enlargement:

```
log_x q <= (1-epsilon_0)(2A_1)
          = (1-epsilon_0)/2.
```

This proof uses neither the `B_m` bounds nor smoothness and remains valid for
`m=0` or `m'=0`.  (As printed, Definition 2 refers to the nonexistent entries
`B_{j,0}` in those cases.  Under either natural repair--omit the empty-product
constraint, or assign it any nonnegative bound--the two displayed
total-product constraints and hence this argument are unchanged.)

For fixed `epsilon_0>0` and every fixed `C`,

```
x^((1-epsilon_0)/2) <= x^(1/2)/(log x)^C
```

for all sufficiently large `x`.  The classical Bombieri--Vinogradov theorem,
in its standard prime-counting discrepancy form, therefore gives for every
`D>0`

```
sum_{q <= x^((1-epsilon_0)/2)} max_{(a,q)=1}
 | sum_{x<=p<=2x, p=a (q)} 1
   - (1/phi(q)) sum_{x<=p<=2x, (p,q)=1} 1 |
 <<_{D,epsilon_0} x/(log x)^D.
```

This is also the usual partial-summation corollary of the von-Mangoldt
form of Bombieri--Vinogradov.  Restricting a nonnegative sum to the squarefree
subset `Q^*` proves Definition 3.  The residue condition in Definition 3 is
more than sufficient: because `q<=x`, `(a,p)=1` for every prime `p<=x`
implies `(a,q)=1`.

No `W` factor is missing here.  Definition 3 is explicitly stated for `Q^*`.
In Stadlmann's proof of Proposition 1, line 429 of the TeX source absorbs the
actual `W`-containing sieve modulus into `Q^*(...,epsilon_0/2)` before invoking
Definition 3.  The same exponent calculation with `epsilon_0/2` still gives a
fixed power saving from `1/2`, so BV applies.

## Proposition 1 with the prime indicator

Take

```
rho(n;x)=1_P(n),       c_1=c_2=0,       beta=1/2.
```

The four hypotheses are checked line by line.

1. `0 <= rho <= 1_P`, so the prime-minorant hypothesis holds with `c_2=0`.
2. Equidistribution was proved in the preceding section directly from BV.
3. If `rho(n;x)!=0` and `n in [x,2x]`, its only prime factor is `n>x^beta`.
   Also `beta=1/2>B_{1,1}=1/4+e`, because `e<1/4`.
4. The prime number theorem gives
   `sum_{x<=n<=2x}rho(n;x)=(1+o(1))x/log x`, so `c_1=0`.

Thus Proposition 1 is unconditional for every parameter `0<e<1/4`.  In
particular no hypothesis of Proposition 1 imposes a positive lower bound on
`e`; its strict positivity comes only from Definition 1.

## Exact variational problem left by this family

For the full simplex above, the two relevant forms become

```
I(F) = integral_{sum(t_i)<R} F(t)^2 dt,

J(F) = integral_{s=sum_{i<k}t_i <= V}
          ( integral_0^(R-s) F(t_1,...,t_{k-1},u) du )^2
       dt_1...dt_{k-1}.
```

After `t_i=(1/4)u_i`, this is exactly one quarter of Polymath8b's quotient
`M_{48,eta}`, with `eta=4e`:

```
k J(F)/I(F) = (1/4) M_{48,4e}(scaled F).
```

Therefore this route closes `H_1<=236` precisely if an exact finite function
certificate proves `M_{48,4e}>4` for some rational `e>0`.  The analytic side
has no remaining Proposition 2/3 case split.

The independent script `code/full_simplex_basis.py` reconstructs exact
rational `I,J` matrices for a complete symmetric power-sum polynomial basis.
Its high-precision eigensolve is discovery-only.  The checker
`verify_direct_bv.py` verifies all rational parameter/exponent assertions in
this note and deliberately makes no claim about the unresolved quotient.

## Relation to known numerics and current experiments

Polymath8b records `M_{50,1/25}>4.0043` at polynomial degree 27 and
`M_{51,1/50}>4.00156` at degree 22; it does not state a `k=48` certificate.
For our complete (but low-degree) power-sum basis at the original
`e=3/400`, high-precision discovery values are:

```
degree 5: kJ/I = 0.886223224479836193...
degree 6: kJ/I = 0.907422113126813406...
degree 8: kJ/I = 0.936614843070637899...
```

These are heuristics from an eigensolve over matrices whose entries have an
exact rational formula; they are not certificates and are far below 1 at low
degree.  Smaller `e`, higher degree, and the Polymath even-signature basis must
be explored before declaring this mechanism exhausted.

