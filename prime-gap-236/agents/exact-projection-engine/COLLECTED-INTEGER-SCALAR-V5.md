# Exact globally collected scalar contraction

This note records the algebraic change in
`collected_integer_scalar.py`.  It changes only the representation of one
already-radialized branch integral; the Definition-5 cutoff, the four branch
domains, the cap schedule, and every inclusion--exclusion sign are inherited
unchanged from `symmetric_cutoff_cross.py`.

Fix a common-large count `r`, one endpoint, one branch, and a surviving
small-coordinate inclusion--exclusion shift `h`.  After the audited v3
family/radial denominator clearing, write the packed integer radial terms as

\[
  \sum_{\tau,x,y} c_{\tau,x,y}X^xY^y,
  \qquad c_{\tau,x,y}\in\mathbb Z,
\]

where the tag \(\tau=(p,q)\) selects two affine powers.  For this branch and
shift let

\[
  A_{\tau,h}(X,Y)=\sum_{a,b}u_{\tau,h,a,b}X^aY^b
\]

be their exact product.  The shift substitution is made before expansion:
the first affine constant becomes \(f_0+f_yh\delta\), and likewise for the
second affine.  Thus the literal old aggregate \(Y_{old}=Y+h\delta\) is
preserved.

Let \(U_h\) be the LCM of all denominators among all
\(u_{\tau,h,a,b}\).  V5 first forms the complete product polynomial

\[
 C_{i,j}=\sum_{\substack{\tau,x,y,a,b\\x+a=i,\ y+b=j}}
 c_{\tau,x,y}(U_hu_{\tau,h,a,b})\in\mathbb Z.
\]

This collection is global across tags.  In particular, terms that reach the
same final monomial through different affine powers collide and cancel
exactly before any geometric moment is multiplied.

For the exact branch domain \(D_h\), request only the surviving moments

\[
 m_{i,j,h}=\int_{D_h}X^iY^j\,d\mu_{r,47-r}.
\]

These are reconstructed by the pinned polygon/interval/point recurrence, not
read from a table.  With \(M_h\) the LCM of their denominators, the shift
contribution is evaluated as

\[
 \frac{\sum_{i,j}C_{i,j}(M_hm_{i,j,h})}{U_hM_h}.
\]

Expanding \(C_{i,j}\) proves this is term-for-term identical to the reference
contraction.  The upstream family and radial denominators are restored once
after both endpoints, as in v3.  Hence there is no numerical approximation
and no change to the exact value.

The computational gain is that the older target r=0 shard performed
89,911,320 affine-coefficient/moment scalar products across its high and low
endpoints.  (The separate value 22,244,880 in that artifact counts terms
distributed while constructing the radial families, not scalar products.)
V5 still performs the necessary integer polynomial collection, but
multiplies the much larger exact moment integers only once per surviving
final monomial.  This is a cost claim, not a proof premise; target use remains
gated on an independent hostile audit and an immutable result-level check.
