# Independent six-core pair/Ritz audit

## Verdict

**SCOPED AUDIT PASS.**  I independently reconstructed the fifteen unscaled
pair directions and their grouped-operation counts before launch, then
reconstructed the complete realized pencil

\[
 \operatorname{span}\{F_0,d_{10},d_9,d_6,d_8,d_5,d_{11}\}
\]

from the completed scalar outputs.  The denominator matrix has seven strictly
positive exact `Fraction` LDL pivots.  A separately written Decimal Jacobi
solve, at 100, 160, and 220 digits, gives

```text
q = 0.97097446824061912246471383200228048619601792680470210792117010867345830431076625910990221982848201708934524965...
base q = 0.97096984763378957411239000413955600374156456588852842689906065531110044998039627409775697657643829975827877396...
gain = 0.00000462060682954835232382786272448245445336091617368102210945336235785433036998501214524325204371733106647570...
shortfall = 0.0290255317593808775352861679977195138039820731952978920788298913265416956892337408900977801715179829...
```

Thus the declared continuation gate `gain >= 1/10000` **fails** by a factor of
about 21.6.  This retires the selected six-core extension tier.  It is not an
upper bound for the complete 20-coordinate space and is not a rigorous
integration certificate.

## Frozen independent artifacts

| object | SHA-256 |
|---|---|
| v2 pair manifest | `32d7e86840b0ba8a859cd41b30f3242bcde3cc8518e0a598f30a304e741ca4ad` |
| full-19 coordinate manifest | `967a004ed5f02dc08d07bd9ab8f5af1050b345427327935b96d0979ae531787f` |
| independent prelaunch checker | `e43880baff76c4af9b57c6fbc2fe2cf9884a9eb6c2d1c96f2a0f67d1d3a67e5a` |
| independent prelaunch artifact | `a67ef637f40cfb83ff26aa45e487af1874d25cddf7ff47769c23a276996063e9` |
| independent Ritz solver | `78820c6d1223b1c304c052a6f974fa4fda5a1c370d625815bc6f39ead770f279` |
| solver tests | `c9bf7770e3f9621d318d82a48efd3db77c78eeffe76f81386a51ee9c14be8d35` |
| independent result | `14b779ccddad14755a7b7152a9b6094c487683fdc73d8d9b7bd94c66dc6293b4` |
| capped sanitized result, compared only after freezing ours | `906a84cb233d107d6887ac71945ba7aa3eab61e08c75ffa198bd6e6227d80f24` |

The independent result is
`agents/small-delta-frontier/results/c10_D12_core6_pair_ritz_independent.json`.
It contains every exact serialized matrix entry, every exact LDL pivot, the
three precision runs, an 80-decimal-grid rationalized vector, its exact
particular quotient, and all input/stage/result hashes.

Run the low-dimensional algebra tests with

```bash
python3 agents/small-delta-frontier/test_solve_core6_pair_ritz_independent.py
python3 -O agents/small-delta-frontier/test_solve_core6_pair_ritz_independent.py
```

Both modes print `PASS 3/3`.  The tests include a known generalized pencil,
exact LDL reconstruction and indefinite rejection, and the unscaled-sum
polarization/factor-48 convention.

## Input and count reconstruction

The prelaunch checker does not import the pair producer.  It reconstructs each
literal sum `d_i+d_j` from the full-19 manifest, canonicalizes all orbit
labels, and recomputes the exact I-orbit, face, marginal-component, and J-domain
counts.  It checks all fifteen edges of the complete graph on
`(10,9,6,8,5,11)`, path uniqueness, positional diagonal-result hashes, and the
declared semantics

```text
A_ij   = (A_(i+j)   - A_ii   - A_jj)/2
B48_ij = (B48_(i+j) - B48_ii - B48_jj)/2.
```

Here `B48` is already `48J`; no further factor 48 occurs in polarization or in
the generalized quotient.  Permanent mutation tests reject a changed
coefficient, grouped count, polarization string, path alias, pre-existing
result, or builder provenance.

For readability, the fifteen reconstructed cross entries are displayed below
to 18 significant digits.  The artifact stores the exact fractions.

| pair | `A_ij` | `B48_ij` | `A` correlation |
|---|---:|---:|---:|
| d10,d9 | `5.115341465206615633E-100` | `1.639048026416332078E-100` | `.934138029991724` |
| d10,d6 | `6.906878748916116108E-100` | `2.199736129014873412E-100` | `.934265170958405` |
| d10,d8 | `1.992734173525227772E-98` | `6.665832808941056961E-99` | `.815663484888285` |
| d10,d5 | `2.690231201696531364E-98` | `8.942284675214089724E-99` | `.815915318242322` |
| d10,d11 | `4.720919082735136593E-101` | `1.500379640374879436E-101` | `.844587813705289` |
| d9,d6 | `2.178181787602929843E-98` | `7.207727959723481534E-99` | `.999979448582809` |
| d9,d8 | `6.948541448797422768E-97` | `2.392855125442301945E-97` | `.965303608385779` |
| d9,d5 | `9.379140731924973044E-97` | `3.210452274481671029E-97` | `.965444158219579` |
| d9,d11 | `1.611925334948904486E-99` | `5.290771448215903200E-100` | `.978750057739443` |
| d6,d8 | `9.379140731924973044E-97` | `3.211749511930308176E-97` | `.965128705286775` |
| d6,d5 | `1.266050870873011200E-96` | `4.309234577774256121E-97` | `.965310802289805` |
| d6,d11 | `2.176464838650578213E-99` | `7.101990396298803825E-100` | `.978882215192271` |
| d8,d5 | `4.334119244975295991E-95` | `1.524833887495712215E-95` | `.999977413895648` |
| d8,d11 | `7.304845696183037782E-98` | `2.470946010482867318E-98` | `.994175724191806` |
| d5,d11 | `9.861699086611491742E-98` | `3.315798177743880244E-98` | `.994483733462264` |

## Positive definiteness, conditioning, and residual

Exact LDL proves positivity for the realized serialized denominator matrix;
no positive-definiteness assumption is made.  Raw-coordinate conditioning is
about `4.13E33`, mostly because the six direction units have radically
different sizes.  After diagonal normalization, the denominator correlation
Gram eigenvalues are

```text
7.5017726155349159E-7, 2.5282314597445538E-5,
1.4863032218494020E-3, 6.9368124383945023E-3,
2.6827705663168009E-1, 9.9959412108559270E-1,
5.7236796741306243
```

and its condition number is `7629769.6124217913...`.  This explains why a
stable high-precision solve is required but does not invalidate the exact LDL
test.

The independently implemented Jacobi solver's off-diagonal residual falls
from `7.95E-88` at 100 digits to `5.98E-208` at 220 digits.  The three leading
eigenvalues agree through the requested precision gates.  Contracting the
80-digit-grid rationalized vector exactly gives the same displayed quotient;
its largest componentwise dimensionless residual

```text
max_i |(B48 x - q A x)_i| / sqrt(A_ii * (x^T A x))
    = 7.0098639297408326E-62.
```

Numerical optimality is still a discovery statement; the particular rational
contraction is exact only relative to the serialized Decimal100 forms.

## Independent comparison

Only after the independent output SHA `14b779cc...` was frozen did I read the
capped solver's sanitized result.  The two artifacts have string-for-string
identical exact `A`, exact `B48`, and exact LDL-pivot arrays.  Their top Ritz
values differ by `4.01E-189`, consistent with their different final precision
truncations.  Both independently say that the `1E-4` continuation gate fails.

The comparison supports the algebra and serialization; it does not supply an
integration error bound.  The stale capped artifact `8193ef60...` remains
superseded for candidate-emission policy and is not used here.
