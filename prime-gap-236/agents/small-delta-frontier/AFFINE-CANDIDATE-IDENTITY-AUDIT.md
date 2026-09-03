# C10 D12 transferred-affine candidate identity audit

Date: 2026-09-02 (Europe/Berlin)

## Verdict

**AUDIT PASS** for the candidate-identity question only.

Every ordered base label and coefficient, every raw and effective affine
coordinate, the support parameters, cutoff rule, and the I/J multiplier
insertion agree between Section 10 of the proof draft and both frozen dyadic
target loaders.  No target integral, matrix, eigenproblem, or quotient was
evaluated in this audit.  This verdict therefore proves no sign and does not
close `[CERT-C10-48]`.

The lightweight fail-closed checker is

```text
agents/small-delta-frontier/verify_affine_candidate_identity.py
SHA256 a24dbe781c2311420a5c8fa2366ee5959f28ddcd3e62aa69f94976eb78b8a950
```

It passes identically under normal and optimized Python in about one second.

## 1. Resolution of the candidate file identity

There is no file named `c10_d12_affine_vector.json` in the workspace.  Nor is
the Decimal D12 I-stage a coefficient source.  The function named in
Section 10 is the following exact composite datum:

1. the ordered 272-term base polynomial in
   `hb_c10_fullsimplex_noones_D12_integer_scaled.json`;
2. the ordered 48-entry raw affine vector in
   `c10_stratum_linear_cappedopt_D4_exact.json`;
3. the explicit cutoff 11 map which keeps every constant channel but sets
   the L and Z channels to zero for counts 12--15.

Thus, writing the ordered base labels as `(d_j,lambda_j)` and their integer
coefficients as `C_j`, the actual candidate is

\[
 P(t)=\sum_{j=1}^{272}C_j(1-\textstyle\sum_i t_i)^{d_j}P_{\lambda_j}(t),
\]

\[
 F(t)=1_T(t)P(t)
 \bigl(a_{R(t)}+b_{R(t)}L(t)+c_{R(t)}Z(t)\bigr),
\]

where

\[
 R=\#\{i:t_i>\delta\},\qquad
 L=\sum_{t_i>\delta}t_i,\qquad
 Z=\sum_{t_i\leq\delta}t_i,
\]

and, for the raw artifact entries `(u_{r,1},u_{r,L},u_{r,Z})`,

\[
 (a_r,b_r,c_r)=
 \begin{cases}
 (u_{r,1},u_{r,L},u_{r,Z}),&0\leq r\leq11,\\
 (u_{r,1},0,0),&12\leq r\leq15.
 \end{cases}
\]

This is precisely the two-step reading of proof-draft lines 962--966.  The
raw 48-vector by itself is **not** the candidate.

## 2. Pinned sources and ordered base identity

| item | SHA256 |
|---|---|
| `agents/structural-basis/PROOF-DRAFT-C10.md` | `30532156254193456faa6f8d1c9e6ac53395d7a46d633410bb749a0557773c2f` |
| original rational D12 source | `719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87` |
| integer-scaled D12 input | `8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93` |
| raw affine artifact | `ffa607e0f2a8a3b6648f248efb13dc7ac2f1e7ef5809771f31c5f04b30f53158` |
| grouped dyadic target loader | `bf0ad4b3c1288c1d2df67e92f9ebe9e63613b9dcd2892c3f96522217d920677b` |
| independent tagged-dyadic driver | `7e2ed20a68e3c3e95a9566b32cae3d403949a79a3a81adfa61b8dab833b640b9` |
| exact loader used by the independent driver | `5514f63159ad74e54142cf1db2d88a9c69f552cad3d253cd50ca66452cf2784e` |
| exact affine recurrence | `9c21d73af25f63ad16c62a2a1935a9cfd3a8d134d7b7ada2620eddc12e1c3d3e` |

The proof-draft hash above is the current post-edit hash.  Relative to the
earlier audited draft, the intervening edit added the pinned BFI 2019
correction-note source row and changed nonblocking citation item 5, both
outside Section 10.  I reread current Section 10 after that edit; its
candidate definition, support, cutoff, and multiplier formulas are unchanged.

The original and integer-scaled files have exactly the same 272 ordered
labels.  They are distinct, canonical labels with no part 1 and equal the
complete set

```text
{(d,lambda): d+|lambda| <= 12 and every part of lambda is at least 2}.
```

At every ordered index `j=0,...,271`, the checker verifies

```text
integer_coefficient[j] = base_LCM * source_coefficient[j].
```

The reconstructed base LCM is the positive 714-bit integer

```text
50000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
```

The original ordered label/vector payload SHA is
`8ea54de0e3bb4d9f978fee80a6788c81d542a7d6839ed8c69e22a5374845fe4e`.
The canonical scaled label/vector identity SHA computed by the audit is
`8a231352d24d2e683ab6cd1434297c6fce6a38da8421e55d572627e6ef7927fb`.

Both target loaders reconstruct this relation from the original source rather
than trusting the scaled file's metadata.  The grouped loader retains the
ordered list; the tagged loader constructs a label-keyed map in that same
order.  The audit compares all 272 values across those representations.

The original vector was discovered with full-simplex cap metadata
`beta1=beta2=beta3plus=79247/300000`.  That metadata is deliberately not
candidate support.  Both target loaders ignore it after pinning the ordered
polynomial payload and instantiate the C10 caps below.  Hence no discovery-
support value leaks into the candidate calculation.

## 3. Support and active counts

The proof draft, affine artifact, D12 Decimal I-stage metadata, grouped loader,
and tagged loader all give exactly

```text
k = 48
alpha = 79247/300000
eta = 76247/300000
delta = 1/100
beta1 = beta2 = 3/20
beta3plus = 97/625
```

Here `alpha=A_1+epsilon_s`, `eta=A_1-epsilon_s`, and
`alpha-eta=delta`.  The full I strata are exactly `R=0,...,15`, since

```text
B_15 - 15 delta = 13/2500 > 0,
B_16 - 16 delta = -3/625 < 0.
```

Consequently the 16-triple table defines the multiplier everywhere on `T`.
For J at common count 15 the small distinguished branch has total count 15;
the putative large branch has total count 16 and is geometrically empty.  No
missing count-16 multiplier is being hidden by a nonempty branch.

## 4. All 16 effective affine triples

The raw artifact's canonical ordered label/vector identity SHA is
`bb6de456712e864e0fe53283cfa0c173f359d57d0e0c049ecbaeac75317bd26e`.
After applying the declared cutoff, the effective identity SHA is
`47a31aac5187e9d315d9255bc040e435dc3d3bfa25c5fcd1f4c0a834c17db95e`.
The exact effective table is:

| R | a_R | b_R | c_R |
|---:|---|---|---|
| 0 | `2256324583545539/2097152` | `0` | `-357948862678097/65536` |
| 1 | `196848094965403/262144` | `1329291112637433/2097152` | `-132323044505347/32768` |
| 2 | `4406131684616137/8388608` | `4440898159390065/8388608` | `-6301336143815463/2097152` |
| 3 | `3071853522654055/8388608` | `1873137364900853/4194304` | `-4698099928525779/2097152` |
| 4 | `4232913310347573/16777216` | `199466972962147/524288` | `-3486959176947673/2097152` |
| 5 | `709371501689863/4194304` | `5479911013477801/16777216` | `-2545890370096675/2097152` |
| 6 | `7173430925319485/67108864` | `587856762287883/2097152` | `-7141009222270969/8388608` |
| 7 | `4002004595054959/67108864` | `989357683455707/4194304` | `-2292173843782275/4194304` |
| 8 | `844076225170843/33554432` | `3161733858020455/16777216` | `-1228386441950839/4194304` |
| 9 | `4003534272189999/983692931` | `142814001365361/1048576` | `-899728771009915/8388608` |
| 10 | `-1710825941077645/461657661` | `1389314285449129/16777216` | `-2400266686999653/268435456` |
| 11 | `-2451932254608170/928407469` | `5379436233629943/134217728` | `780926247516377/67108864` |
| 12 | `-322962281040557/268435456` | `0` | `0` |
| 13 | `-2353400356589888/925190623` | `0` | `0` |
| 14 | `958565777474811/961909265` | `0` | `0` |
| 15 | `604394101174906/998874949` | `0` | `0` |

The effective affine LCM used independently by both loaders is the positive
206-bit integer

```text
100608472057547700406782448767158942943016780835590106744094720.
```

Each loader multiplies all effective entries by this same factor.  Together
with the separate base LCM this multiplies `F` globally by their product and
therefore multiplies I and J by its positive square.

### The only projection, made explicit

The raw D4 artifact has eight nonzero entries which are deliberately not part
of the transferred D12 candidate:

| raw channel set to zero | raw value |
|---|---|
| `(12,L)` | `7799322466605125/268435456` |
| `(12,Z)` | `-56724332820617/8388608` |
| `(13,L)` | `1375565206469673/33554432` |
| `(13,Z)` | `-1918352129941379/67108864` |
| `(14,L)` | `4995855296921182/782137609` |
| `(14,Z)` | `-5165931429842995/268435456` |
| `(15,L)` | `297157523249592/901522019` |
| `(15,Z)` | `-3602318024650241/536870912` |

This is not silent: proof-draft lines 965--966 prescribe it, the Decimal
transfer uses `channel==1 or R<=11`, and both target loaders call the exact
parser with `linear_cutoff=11`.  All 16 constant channels survive.  The
effective space has 40 nominal channels and 39 nonzero coefficients because
the raw `(0,L)` coefficient is already exactly zero, as it must be when
`L=0` on the all-small stratum.  No base-polynomial label or coefficient is
projected.

## 5. I multiplier formula

On a grouped I face let `r` be the number of large coordinates and `h` the
small-box inclusion--exclusion shift count.  If X and Y are the two remaining
aggregate variables, then

\[
 L=r\delta+X,\qquad Z=h\delta+Y.
\]

The grouped engine's three channel polynomials are exactly

\[
 1,\quad r\delta+X,\quad h\delta+Y,
\]

and it inserts their affine combination before squaring.  The tagged engine
starts with `(a_r+b_r r delta,b_r,c_r)` and its inclusion--exclusion radial
shift adds `c_r h delta` to the constant.  Both therefore square precisely

\[
 a_r+b_r(r\delta+X)+c_r(h\delta+Y)
 =a_r+b_rL+c_rZ.
\]

There is no fixed-amplitude contraction, matrix projection, or post-squaring
multiplier insertion in either target path.

## 6. J multiplier formula

Fix the 47 common coordinates and let `t` be the distinguished coordinate.
Write `L_c,Z_c` for the common-coordinate sums and

\[
 M_0=\int P(u,t)\,dt,\qquad M_1=\int tP(u,t)\,dt
\]

on one branch.  The correct marginal is:

- on a small distinguished branch (`t<=delta`, total count R=r),

  \[
   (a_r+b_rL_c+c_rZ_c)M_0+c_rM_1;
  \]

- on a large distinguished branch (`t>delta`, total count R=r+1),

  \[
   (a_{r+1}+b_{r+1}L_c+c_{r+1}Z_c)M_0+b_{r+1}M_1.
  \]

The grouped implementation constructs `lbase=r delta+X` and
`zbase=h delta+Y`, adds the shifted first moment to Z on its two small
branches and to L on its two large branches, and only then combines each
branch with the appropriate total-count triple.  The tagged implementation
independently chooses total count `r` versus `r+1`, aggregate
`(a+b r delta,b,c)`, and shifted coefficient `c` versus `b`.  Its radial
shift supplies the `h delta` part of `Z_c`.  Thus the two formulas above
agree term by term before either ordered branch product is formed.

Both implementations retain the full small/small, small/large, large/small,
and large/large branch products.  Finally, the grouped driver returns `48J`
and the tagged result wrapper multiplies J by 48 exactly once.  No density or
cutoff factor is lost in the candidate identity.

## 7. Boundary conventions

Section 10 assigns `t_i=delta` to Z, consistently with the strict definition
of a large coordinate.  The integration engines decompose the region using
closed polynomial faces; equality edges can consequently be represented in
both adjacent algebraic closures.  They carry zero Lebesgue measure and the
engines do not expose a pointwise value of F there.  Hence this does not
change I or J and is exactly the a.e. boundary replacement already stated in
proof-draft lines 969--971 and Section 1's boundary discussion.

Likewise, integrating the closure of the half-open total-sum simplex computes
the same exact Lebesgue integral.  The audit found no positive-volume cell
whose R, L, Z, cap, alpha, or eta convention differs.  In particular, a
large distinguished coordinate changes the total count before selecting its
affine triple, while a small distinguished coordinate does not.

## 8. Reproduction and scope

From the repository root:

```bash
PYTHONPATH=prime-gap-236 python3 \
  prime-gap-236/agents/small-delta-frontier/verify_affine_candidate_identity.py
PYTHONPATH=prime-gap-236 python3 -O \
  prime-gap-236/agents/small-delta-frontier/verify_affine_candidate_identity.py
```

Both must print `AFFINE CANDIDATE IDENTITY AUDIT PASS`, the effective affine
identity SHA `47a31aac...`, 272 base coefficients, 16 triples, 40 nominal
channels, 39 nonzero channels, and the same eight deliberately overwritten
raw channels.

This audit is static.  It does not assert that the candidate satisfies
`48J-I>0`, does not validate a Decimal result, and does not upgrade either
dyadic driver from its pre-launch status.  A future positive output must still
be reconstructed and audited separately.
