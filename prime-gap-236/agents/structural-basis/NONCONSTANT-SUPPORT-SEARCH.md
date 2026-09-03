# Nonconstant support schedules: an exact finite search

## Status

This is a new analytic-support mechanism, not a sieve certificate.  It gives
an exact finite sufficient test for a count-dependent schedule \(B_m\), and
it validates one C10 schedule which strictly contains the original C10
support.  No monotonicity of the Rayleigh quotient under support inclusion is
claimed.

## 1. Correct prefix-crossing lemma

Let \(y_1,\ldots,y_N\geq\delta>0\), with total \(T\leq S\).  Given two
bin capacities \(C,D>0\), we seek a subset of sum \(U\leq D\) whose
complement has sum at most \(C\).  Put

\[
 \ell=(T-C)_+,
 \qquad L=(S-C)_+,
 \qquad r=\left\lceil\frac L\delta\right\rceil.
\]

If \(T\leq C\), take the empty subset.  Otherwise sort the entries and take
the *minimal prefix* with sum \(U_j\geq\ell\).  It exists whenever the
selected pool has mandatory mass \(N_g\delta\geq L\), and \(j\leq r\).
If the pool has \(N_g\) entries and total at most \(S_g\), then

\[
 U_j\leq \frac{S_g}{N_g}\quad(r=1),                         \tag{1}
\]

and, when \(r\geq2\),

\[
 U_j\leq L+\frac{S_g-L}{N_g-r+1}.                           \tag{2}
\]

Indeed, \(U_{j-1}<\ell\leq L\), while the last
\(N_g-j+1\) entries are all at least \(y_j\).  Hence

\[
 S_g\geq U_{j-1}+(N_g-j+1)y_j.
\]

For \(j\geq2\), this gives

\[
 U_j \leq L+\frac{S_g-L}{N_g-j+1},
\]

which increases with \(j\leq r\).  For \(j=1\), the preceding prefix is
exactly zero, giving the sharper (1).  Since \(U_j\geq\ell\), its complement
has sum at most \(C\).  Thus (1) or (2) being strictly below \(D\) proves the
two-bin partition.

The pool may be all \(m+m'\) entries, or either one of the two groups.  For
a one-group choice, use \((N_g,S_g)=(m,B_m)\) or
\((m',B_{m'})\), provided \(N_g\delta\geq L\).  This is often substantially
sharper than combining both groups.

The initially proposed sentence “take the \(r\) smallest” with upper bound

\[
 L+\frac{S-(r-1)\delta}{N-r+1}
\]

is false.  For example, \(\delta=1,L=1.1,N=3,S=100,r=2\), and three
equal entries have two-smallest sum \(200/3>50.6\).  The minimal-crossing
prefix above is the required repair.

## 2. Linear cells and the finite search

Fix \(\delta,A\), hence every analytic capacity.  For a count pair put

\[
 N=m+m',\qquad S=B_m+B_{m'},\qquad L=S-C.
\]

The empty-subset cell is \(S<C\).  Otherwise, fix a pool
\(g\in\{\text{combined},m,m'\}\) and an integer \(r\).  The cell conditions
are

\[
 (r-1)\delta<L\leq r\delta,\qquad r\leq N_g,\qquad
 N_g\delta\geq L.                                            \tag{3}
\]

For \(r=1\), (1) is the linear inequality

\[
 S_g<N_gD.                                                    \tag{4}
\]

For \(r\geq2\), writing \(q=N_g-r+1\), (2) is equivalent to

\[
 (q-1)(S-C)+S_g<qD.                                         \tag{5}
\]

Thus, after enumerating the finite choices \((g,r)\) for every count pair,
all constraints are strict rational linear inequalities in the finitely many
\(B_m\).  They can be searched as exact LP cells or as a rational MILP.

The remaining constraints are also linear:

- Definition 1: \(\delta<B_1\),
  \(B_m\leq B_{m+1}\leq B_m+\delta\);
- active count \(m\): \(m\delta\leq B_m\); a certified first empty count
  \(M\): \(M\delta>B_M\), followed by constant extension;
- the scalar Type-II/III and Type-0 inequalities in
  `verify_direct_hb_frontier.py`;
- (3)--(5) for both \(\omega_*=0\) and \(\omega_*=A-1/4\), using the first
  two proof-safe, inward-shrunk IIa/IIb/III capacities described below; and
- (3)--(5) for the literal uniform repaired-IIc pair from the proof draft's
  equation (27),

  \[
   C=\frac{4601199986563}{15000000000000},\qquad
   D=\frac{776499995341}{15000000000000}.                   \tag{6}
  \]

Here \(h=10^{-10}\), \(\zeta_{\max}=h/1000\), and
\(r_0=h/10\).  With the notation of the proof draft's Section 6.4, the
literal IIa lower capacities are

\[
 g_a(\omega_*)-3\zeta_{\max}-r_0,\qquad
 d_a(1/2,\omega_*)-r_0,                                    \tag{7}
\]

and the literal IIb lower capacities are

\[
 g_b(\omega_*)-3\zeta_{\max}-r_0,\qquad
 \frac12-g_a(\omega_*)-2\omega_*-6\zeta_{\max}-r_0.        \tag{8}
\]

The second entries in (7)--(8) use the correct monotone endpoint.  The
unused third IIb capacity is
\(2\omega_*+d_b(g_b(\omega_*),\omega_*)\) and must separately be positive.
For Type III the exact Section-7 capacities are

\[
 \frac13+\frac43\delta_3(\omega_*)-\frac43\omega_*-h,
 \qquad
 \frac16-\frac13\delta_3(\omega_*)+\frac43\omega_*-h.      \tag{9}
\]

Thus the checker uses the actual repaired inward endpoints throughout, not
the slightly more conservative frontier shorthand from the preliminary
support search.  The exact pairs used by its universal loop are:

| branch | \(\omega_*\) | first capacity | second capacity |
|---|---:|---:|---:|
| IIa | \(0\) | \(4140000001897/10^{13}\) | \(49999999923/(7\cdot10^{11})\) |
| IIa | \(2747/300000\) | \(4579520001897/10^{13}\) | \(28023999923/(7\cdot10^{11})\) |
| IIb | \(0\) | \(10700000008691/(3\cdot10^{13})\) | \(429999998947/(5\cdot10^{12})\) |
| IIb | \(2747/300000\) | \(4299200002897/10^{13}\) | \(356019996841/(15\cdot10^{12})\) |
| III | \(0\) | \(239999999869/(6\cdot10^{11})\) | \(359999999831/(24\cdot10^{11})\) |
| III | \(2747/300000\) | \(207035999869/(6\cdot10^{11})\) | \(138313333277/(8\cdot10^{11})\) |
| IIc | uniform | \(4601199986563/(15\cdot10^{12})\) | \(776499995341/(15\cdot10^{12})\) |

The unused IIb third capacities are respectively
\(350000001/35000000000\) and \(2972900003/105000000000\), both positive.
A practical objective is a weighted sum \(\sum_m w_mB_m\), with nonnegative weights from
the capped eigenvector's stratum sensitivities; lexicographic maximization of
the high-m caps is a deterministic fallback.  Once a rational point is
found, the independent interval-cover program remains the adversarial check.

## 3. Exact C10 schedule

Keep \(\delta=1/100\), \(A=77747/300000\), and support enlargement
\(1/200\).  The following grid-\(10^{-5}\) schedule passes (3)--(9):

| \(m\) | \(B_m\) |
|---:|---:|
| 1,2 | \(3/20\) |
| 3 | \(97/625\) |
| 4 | \(15837/100000\) |
| 5 | \(16183/100000\) |
| 6 | \(8193/50000\) |
| 7 | \(16623/100000\) |
| 8 | \(16797/100000\) |
| 9 | \(16877/100000\) |
| 10 | \(17013/100000\) |
| 11 | \(1069/6250\) |
| 12 | \(17179/100000\) |
| 13 | \(17241/100000\) |
| 14 | \(17293/100000\) |
| 15 | \(17337/100000\) |
| 16 | \(543/3125\) |
| 17 | \(17411/100000\) |
| \(m\geq18\) | \(3489/20000\) |

The exact checker prints

```text
C10 NONCONSTANT SCHEDULE EXACT PREFIX PASS
active_counts=1..17 first_empty=18
III omega_worst_prefix_margin=899021332939/5600000000000 pair=13,14
IIc uniform_worst_prefix_margin=499995341/15000000000000 pair=3,3
```

The checker also prints every exact capacity it used.  In particular its
IIc line is

```text
IIc uniform_capacities=4601199986563/15000000000000,776499995341/15000000000000
```

The schedule is all-in-first for IIa, IIb, and Type III at \(\omega_*=0\).
It is **not** all-in-first for Type III at \(\omega\): that false margin is

\[
 -\frac{1896000131}{600000000000}.
\]

The repaired prefix lemma and the checker's complete pair loop prove that
branch with the positive margin shown above.  A separate exact interval-box
engine, given the same literal inward capacities, certifies each of the two
critical pairs \((3,3)\) and \((13,14)\) in one robust box.  These are
adversarial spot reconstructions, not the universal proof.

Reproduction:

```bash
python3 prime-gap-236/agents/structural-basis/code/verify_c10_nonconstant_schedule.py

python3 prime-gap-236/agents/structural-basis/code/spotcheck_c10_nonconstant_intervals.py
```

The new support contains the original C10 support: \(B_1,B_2,B_3\) are
equal, and \(B_m>97/625\) for \(4\leq m\leq17\).  It also restores the
previously empty large-count strata 16 and 17.  This is a strict geometric
enlargement, but neither \(J/I\) nor the sign of \(48J-I\) is monotone under
that enlargement.

The universal exact checker has SHA-256
`578969faf9dd80ed652402509963d230ea8a00422252619721c00b3cfd06e8d1`.
The independent interval-box spot checker has SHA-256
`5dd57176e9080eaf6cd9dc51c50d45be4f0e3ca37933330a7df161f0a7488efd`.

## 4. C662 comparison

The separately checked C662 point is

\[
 \delta=\frac{331}{50000},\quad
 A=\frac{15617}{60000},\quad
 B_m=\frac{7253}{50000}\quad(m\geq1).
\]

It has first empty count 22 and passes the original exact two-bin test; its
tight least-entry margin is again
\(249997/7500000000\).  Its total-simplex endpoint is
\(15917/60000\), larger than C10 by exactly \(169/150000\), but its uniform
large-coordinate cap \(0.14506\) is smaller than every C10 cap.  Hence the
supports are incomparable.

A useful geometry proxy comes from the uniform full simplex
\(\sum t_i\leq\alpha\).  With \(k=48\) and \(z=1-\delta/\alpha\),

\[
 \mathbb E R=48z^{48},\qquad
 \mathbb E\sum_{t_i>\delta}t_i
 =48\alpha z^{48}\left(1-\frac{48}{49}z\right).
\]

These are approximately \((7.529,0.11435)\) for C10 and
\((14.270,0.16980)\) for C662.  Thus C662 gains only \(0.0011267\) in the
total endpoint while putting the typical full-simplex large-coordinate mass
above its \(0.14506\) cap.  The count-dependent C10 schedule instead keeps
the same total endpoint and relaxes precisely the strata cut away by the
original cap.  This predicts that C662 may suffer a larger cap-transfer loss,
but it is only a geometry heuristic; a capped quotient calculation is the
falsification test.

## 5. Next exact experiment

If the 20-dimensional C10 reoptimization remains below 1, evaluate the same
finite degree-band space first on this nonconstant C10 support, then on C662.
The nonconstant support requires the grouped evaluator to accept an explicit
finite \(B_m\) table rather than the current three-value schedule.  Before
any high-degree run, reproduce its degree-4 matrix in both the generalized
schedule integrator and the independent interval/face implementation.
