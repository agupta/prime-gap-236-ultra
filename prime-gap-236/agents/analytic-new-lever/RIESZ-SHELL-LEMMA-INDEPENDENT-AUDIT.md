# Independent audit of the Riesz shell lemma

## Verdict

**AUDIT PASS, with the stated single-outer-band scope essential.**

The factor `k`, the literal Definition-5 cutoff, symmetry, disjoint-support
polarization, square-integrability, and the sufficient inequalities in
`agents/structural-basis/RIESZ-SHELL-LEMMA.md` are correct when `V` is one
outer band.  A multiband extension that discards the outer `J(H)` term is
false.  The smallest obstruction is already the two-band kernel below, and
an explicit symmetric square-integrable function can make `J(H)<0`.

## Literal Definition 5 and the factor `k`

Write \(\eta_m=A_m-\varepsilon\).  For a fixed distinguished coordinate,
literal Definition 5 has the band-pair cutoff

\[
s=t_1+\cdots+t_{k-1}
 \leq \max(\eta_m,\eta_{m'}).
\]

If symmetric \(F\) and \(H\) are supported on distinct single bands \(U,V\),
respectively, and

\[
m_i^F(x)=\int F(x_1,\ldots,x_{i-1},u,x_i,\ldots),du,
\]

then the coordinate-\(i\) cross term is

\[
\int_{\sum x\leq\eta_{UV}}m_i^F(x)m_i^H(x)\,dx,
\qquad
\eta_{UV}=\max(\eta_U,\eta_V).
\]

All \(k\) coordinate terms are equal by symmetry.  Therefore Definition 5's
single-distinguished-coordinate bilinear form satisfies

\[
kJ(F,H)=\sum_{i=1}^k
 \int_{\sum x\leq\eta_{UV}}m_i^F(x)m_i^H(x)\,dx.
\]

Fubini then gives exactly

\[
kJ(F,H)=\int_V H(t)
 \sum_i1_{\sum_{j\ne i}t_j\leq\eta_{UV}}
 m_i^F(t_{\widehat i})\,dt=\langle G_F,H\rangle_I.
\]

Thus there is one factor \(k\), not \(k^2\), and the cutoff cannot be omitted.
For the frozen active-25 inner/outer pair this specializes to the stated
\(A_2-\varepsilon=3031/12000\).  For multiple outer bands it must instead be
recomputed pairwise as \(\max(A_m-\varepsilon,A_{m'}-\varepsilon)\); there is
no common lower cutoff that can replace those maxima.

## Symmetry and square-integrability

Permutation of the coordinates sends the summand indexed by \(i\) in
\(G_F\) to the summand indexed by the permuted coordinate.  Since \(F,U,V\)
are symmetric, the full sum is symmetric.  The factor \(1_V\) gives the
claimed support.

The supports are bounded.  If every coordinate fiber has length at most
\(L<\infty\), Cauchy--Schwarz gives

\[
|m_i^F(x)|^2\leq L\int |F(x,u)|^2\,du,
\qquad
\int |m_i^F(x)|^2\,dx\leq L I(F).
\]

Replicating this marginal along a bounded `V` fiber and summing the finite
set of \(k\) coordinates shows \(G_F\in L^2(V)\).  Rational-polytope
boundaries are null, so disjoint bands also give
\(\langle F,G_F\rangle_I=0\).

## Polarization and the sufficient inequality

The Definition-5 bilinear form is symmetric after swapping the two band
indices and the two distinguished fiber variables.  Hence

\[
I(F+G_F)=I(F)+I(G_F)
\]

and

\[
kJ(F+G_F)=kJ(F)+2kJ(F,G_F)+kJ(G_F)
          =kJ(F)+2I(G_F)+kJ(G_F).
\]

Because `V` is a *single* band, its self kernel is the scalar indicator
\(1_{s\leq\eta_V}\), so \(J(G_F)\geq0\).  It follows exactly that

\[
I(G_F)>I(F)-kJ(F)
\]

implies \(kJ(F+G_F)>I(F+G_F)\).

For a finite family \(H_i\subset L^2(V)\), put
\(A_{ij}=I(H_i,H_j)\), \(b_i=kJ(F,H_i)\), and
\(H=\sum_i c_iH_i\).  Direct expansion gives

\[
kJ(F+H)-I(F+H)
\geq -\{I(F)-kJ(F)\}+2c^Tb-c^TAc.
\]

This proves the stated general sufficient inequality.  If \(Ac=b\), then
\(c^TAc=c^Tb\), yielding the stated condition
\(c^Tb>I(F)-kJ(F)\).  No invertibility of \(A\) is used.

In the one-dimensional case, for one nonzero outer function \(H\), define

\[
A=I(H)>0,\qquad b=kJ(F,H)=\langle G_F,H\rangle_I,
\qquad D=I(F)-kJ(F).
\]

Taking the exact scalar \(c=b/A\) gives

\[
2cb-c^2A=\frac{b^2}{A}.
\]

Hence the single-direction sufficient test is exactly

\[
\frac{b^2}{A}>D.
\]

After normalizing by the positive value \(I(F)\), this is

\[
\frac{b^2}{A\,I(F)}>
\frac{I(F)-kJ(F)}{I(F)}.
\]

This is the squared `I`-norm of the orthogonal projection of \(G_F\) onto
\(\operatorname{span}\{H\}\), divided by \(I(F)\); no outer `J(H)` entry is
used beyond its valid single-band nonnegativity.

## Smallest multiband obstruction

For two bands with \(\eta_1<\eta_2\), fix a rest sum
\(\eta_1<s\leq\eta_2\).  If \(M_1,M_2\) are the two band marginals, the
literal Definition-5 density is

\[
\begin{pmatrix}M_1&M_2\end{pmatrix}
\begin{pmatrix}0&1\\1&1\end{pmatrix}
\begin{pmatrix}M_1\\M_2\end{pmatrix}.
\]

The determinant is \(-1\).  Already the rational vector \((1,-1)\) gives
quadratic value \(-1\).  Thus disjoint support diagonalizes `I`, but it does
not diagonalize `J` and does not make the cross-band `J` kernel positive.

This is realizable by a symmetric square-integrable function, not merely a
formal matrix vector.  Take \(k=2\), \(\varepsilon=e=1/100\),
\(A_1=1/4\), \(A_2=3/10\), and loose caps containing the two total-sum
strips.  Put \(U_1=A_1+e\), \(w=e/10\), and, for
\(u=t_1+t_2\), define

\[
H(t_1,t_2)=
 \begin{cases}
  1/w,&U_1-w\leq u\leq U_1,\\
 -1/w,&U_1\leq u\leq U_1+w,\\
 0,&\text{otherwise}.
 \end{cases}
\]

The first strip lies in band 1 and the second in band 2; `H` is symmetric and
square-integrable.  Its distinguished marginals are

\[
(M_1(s),M_2(s))=
\begin{cases}
(1,-1),&s<U_1-w,\\
((U_1-s)/w,-1),&U_1-w\leq s\leq U_1,\\
(0,-(U_1+w-s)/w),&U_1\leq s\leq U_1+w,\\
(0,0),&s>U_1+w.
\end{cases}
\]

Below \(\eta_1=A_1-e\), the all-ones kernel gives zero because
\(M_1+M_2=0\).  On \((\eta_1,U_1-w)\), the indefinite kernel gives \(-1\).
The transition integral on \([U_1-w,U_1]\) is zero, and the final positive
integral is \(w/3\).  Consequently

\[
J(H)=-(U_1-w-\eta_1)+\frac w3
    =-2e+\frac{4w}{3}=-\frac7{375}<0.
\]

Therefore any multiband energy summation that drops `kJ(H)` as nonnegative is
invalid absent an exact outer-`J` computation or a separate sign argument.
The truncated v3 support avoids this obstruction by retaining exactly one
outer band.
