# Active25 D19/D14 one-band exact A stage

## Outcome

The natural D14 outer coordinate passed the calibrated two-seed screen and its
one-band norm has now been reconstructed exactly.  The theorem-facing strict
aggregate status is

```text
EXACT D14 ONE-BAND A AGGREGATE STRICT-V2 PASS
```

For the evaluation vector scaled by `10^38`,

```text
A = I(H 1_V)
  = 5.827639719675758042725284281148949297939045992e-68.
```

Undoing the square scale gives

```text
A_unscaled = 5.827639719675758042725284281148949297939045992e-144,
A / I_D14(full simplex) = 0.0513902228424459418766367911364162.
```

The full exact fractions are in
`results/d14_one_band_a_aggregate_exact_v2_strict.json`.  This is an A-only
result.  The cutoff-aware `b=48J(F_D19,H_D14)` remains separate, and no
certificate claim follows from A alone.

## Frozen geometry and coordinate

The single outer band is

```text
alpha1 = 103/400,
alpha2 = 9500917/36000000,
eta    = 8960917/36000000,
delta  = 1/60.
```

Its 12-entry cap head in millionths is

```text
140375,157041,168544,174338,185488,190375,
193097,197146,202047,207090,211668,211668,
```

followed by the terminal plateau.  Counts 0 through 12 are active and count 13
is first empty.  The analytic support result has SHA-256
`c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f`.

The outer coordinate uses the 195-term D14 even basis and the selected
`10^-38` common-grid vector.  Its exact natural dilation is

```text
d = alpha1/alpha2 = 9270000/9500917.
```

The evaluation vector is multiplied by `10^38` before dilation.  This makes
all starting coefficients integral.  It multiplies A by `10^76` and b by
`10^38`, leaving `b^2/A` exactly invariant.  A separate R=6 calculation proved
the scaled/unscaled A ratio is exactly `10^76`.

## Candidate screen and conditioning ledger

The cache-free direct reconstruction covers D12, D14, and D16.  The common
random-number two-seed projection aggregate gave

| coordinate | projected energy / inner I | standard error | three-SE lower |
|---|---:|---:|---:|
| D12 | 0.0136197394837 | 0.000488320979 | 0.0121547765463 |
| D14 | 0.0221860541077 | 0.000531000956 | 0.0205930512403 |
| D16 | 0.0301540356368 | 0.000436462094 | 0.0288446493562 |

The exact D19 normalized deficit is
`0.013206916304391244341329...`.  D12 was inconclusive at three standard
errors.  D14 and D16 both passed the threshold and the additional 0.020 floor;
D14 was selected because its globally collected cutoff-aware b inventory is
104,902 keys, versus 157,438 for D16.

Rounding the legacy D14 vector to common grids `10^-12`, `10^-14`, or `10^-16`
collapsed the exact full-simplex quotient from about 0.975206 to 0.229--0.235.
Those grids are rejected as a conditioning obstruction; their aborted MCMC
screen created no output.  Grids `10^-38`, `10^-40`, and `10^-42` preserve the
exact quotient.  The coarsest, `10^-38`, changes it by only
`1.8760668547e-21`.  Its quick CRN capped projection differs from the original
by `2.2881e-15 +/- 1.7789e-15`, with relative proposal-weighted L2 change
`1.97165e-12`.

The complete decisions and hashes are frozen in
`results/active25_d19_d14_one_band_decision_ledger_v1.json`.

## Exact A algorithm

Write the original coordinate as

```text
F(t) = sum_(a,lambda) theta_(a,lambda)
       (1-sum(t))^a P_lambda(t).
```

The natural dilation stays in the same basis:

```text
F(d t) = sum theta_(a,lambda) binom(a,b)
         (1-d)^(a-b) d^(b+|lambda|)
         (1-sum(t))^b P_lambda(t).
```

The producer globally collects its square into 508 orbit groups and 3,034
nonzero `(orbit,residual-power)` terms.  On a fixed translated count face
`(R,h)`, the polynomial in powers of `1-sum(t)` is independent of whether the
radial endpoint is alpha1 or alpha2.  The paired v2 kernel therefore constructs
one exact Fraction face polynomial and integrates it against both nested
domains.  Their exact difference is the band contribution.

There is one immutable shard for each R=0,...,12.  The producer exposes no
all-count or resume path and uses one worker, a 768 MiB address-space limit,
and exclusive file creation.  Every shard checks:

1. the pinned vector and geometry;
2. two algebraically distinct natural-dilation expansions;
3. exact equality of grouped and termwise constant stratum volumes;
4. exact positivity of high, low, and high-minus-low square integrals;
5. exact `A_scaled=10^76 A_unscaled`.

The strict aggregate hardcodes all 13 shard hashes, rejects missing or
duplicate counts and noncanonical JSON/rationals, rechecks every arithmetic
identity, and pins the strict-v2 D19 inner result.  Normal and `python3 -O`
assembly are byte-identical.  The summed shard time was 2,836.873 seconds and
maximum shard RSS was 91,312 KiB.

An independent radial backend has also reconstructed the R=12 high, low, and
band values exactly, with the same 508/3,034 inventory.  Its final report is
to be pinned separately when the hostile audit completes.

## Frozen files

```text
lower-vector checker       9d5224cd36190dee55f3eebc69e78ef93f81273acaa29ba6db13cd1c5b2fe0b2
lower-vector result        77884ae1197beace517fd758323e53b92d4cc8ef055ddf873ae4cd858625dbe4
lower-vector tests         99b4437b535b3049b56f46d8374135d86a17b0fafff8c58ecd53ffb31707179c
projection source          82a9a357d6605faa349c830d56b410cb7bd5c45f2b2ab05d81754ed55b8a84a7
projection seed 2361817    9104c3dddd40a4b508d7dc49340dd2c2fff0d12bec84a6b5837dd9fb887d3199
projection seed 2361818    0c020286f2abb92c73c9c209ae46095cd0e862231c5b40215b12c2c5ec1423de
projection tests           8207f7d2c5066b7720e8126fff43e1a24f2628bd4a73d25118170772d79ec41a
projection aggregate src   62933a575e2bd2e11b40415be1f28053d936de009fc8a80fbefe25540a66f65f
projection aggregate       db0c2768869fb3584198b5b8005ea710642befe0f7a84061ca6f24dff321bfee
projection aggregate tests fa4a4d8fa346096767f3fe0c26a255cbb72477a78205d95731a9a1fa40e88710
fine-grid source           83dfdd7d88ee7f2f2a4dfbf492af693b9ae99c2bfaf983816c0fdcdec3229a57
fine-grid result           722082591e80d8e1634f974a9ca531903f176f540fbf5342821c062aaaf511a0
fine-grid tests            d7f0f8856f677080495a59dcb04f93c732e7a7103546da9f65311916796e49c3
fine-grid CRN source       789aeeb6a95b9cd52e93a649abdc4a9c8ada55fb2c0d1309d196894a662e38f6
fine-grid CRN result       6c2349a1c9c62004f5babe57a786d81f45795c4abad6b0b5f5d7ee48a8043f50
fine-grid CRN tests        0e1a9888c27c14974d4062ec4b3e848bde382ca9966562fb6546d768ab292512
A producer                 2e91dbd8bcb8d0bfd102f964236d3a7d60d974bfecedab96a4a19a1124e81c2d
A producer tests           4d5402a8e9940755ca18e69c5a346426bc6081d78ea5206236191dc34e527afc
strict A aggregate source  b7ef412482642221dd9b5ff1beab23e4dc9545fc9905edade06fa71236c0b6bd
strict A aggregate result  e00feb75871e9a4f9be34e9042283f0eda1aa16d139fe27dd2c5deb044865c44
strict A aggregate tests   fbe51513ab504f5bf493300394613f50e488c921fa2be6e42fca0a331d888621
strict D19 checker         ff2046ce180394a6328fdec2c112d575a4c540ff964f5dede28c6db6091506c5
strict D19 result          8b0d47b22b09c057633022682332f0de4b7e47d4b6ab6d630690be081c58e170
strict D19 tests           5f03f8cdbc9235dd739c36901fab42cd44216b1213009fd019dfb1ae32fa6d27
```

The older A aggregate result with SHA
`1e0e8e35449a19ce83bfc37896f75431c61ea39ccb82abbf99eb5669319fae22`
contains the same exact A and the same shard bindings, but its ancillary D19
metadata points to the older v1 checker/result.  It is preserved as superseded
metadata and is not theorem-facing.
