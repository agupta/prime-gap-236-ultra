# Current task statement

You are running in a fresh workspace with no prior repository context. Work as an
autonomous mathematical research lead. Use GPT-5.6 Sol at Ultra reasoning effort and use
multiagent v2 aggressively and dynamically if it is available. Do not ask me to plan the
work for you, and do not stop after one unsuccessful round.

Your primary task is to prove a new unconditional bound

\[
H_1:=\liminf_{n\to\infty}(p_{n+1}-p_n)\le 236,
\]

where \(p_n\) is the \(n\)-th prime. Numerically lowering the upper bound from 240 to
236 is the first target. This corresponds to making the Stadlmann/Maynard--Tao sieve
criterion work with \(k=48\), since an optimal admissible 48-tuple has diameter 236.
If you rigorously complete 236 with substantial time remaining, continue toward the next
natural rung \(H_1\le226\) at \(k=47\).

The starting point is Julia Stadlmann's new paper:

- PDF: https://arxiv.org/pdf/2608.31126
- abstract and version history: https://arxiv.org/abs/2608.31126
- TeX source is linked from the abstract page and should be downloaded when useful.

Read the entire paper before treating any formula as established. Extract and check the
definitions and dependencies yourself, especially Definitions 1, 3, and 5;
Propositions 1--3; the Section 5 integration recurrences; and Section 6's parameter
verification. Also consult the primary predecessors when a proof step depends on them:

- Polymath8b, *Variants of the Selberg sieve, and bounded intervals containing many
  primes*: https://doi.org/10.1186/s40687-014-0012-7
- Stadlmann, *On primes in arithmetic progressions and bounded gaps between many
  primes*: https://arxiv.org/abs/2309.00425
- MIT narrow admissible tuple database: https://math.mit.edu/~primegaps/
- candidate 48-tuple file:
  https://math.mit.edu/~primegaps/tuples/admissible_48_236.txt

The 2026 paper proves \(H_1\le240\) with \(k=49\). Its key criterion is this. For a
symmetric square-integrable \(F\) supported on
\(T_k(\delta,A,B,\varepsilon)\), and a prime minorant \(\rho\) satisfying all four
hypotheses of Proposition 1, it is enough to prove

\[
\frac{k(1-c_1)J(F;\delta,A,B,\varepsilon)
      -kc_2K(F;\delta,A,B,\varepsilon)}
     {I(F;\delta,A,B,\varepsilon)}>1.
\]

For a finite symmetric basis \(G_1,\ldots,G_\ell\), writing
\(F=\sum_i c_iG_i\), Section 5 turns this into the exact Rayleigh quotient
\(cM_2c^T/(cM_1c^T)>1\). Floating-point eigenvectors are only a discovery aid: the
paper rationalizes the vector and checks the quotient exactly.

The published baseline parameters are

\[
\varepsilon=0.0075=3/400,\quad
A=(-\varepsilon,0.253),\quad
\delta=0.028=7/250,
\]

\[
B_{1,1}=B_{1,2}=0.15=3/20,\qquad
B_{1,m}=0.17=17/100\ (m\ge3),
\]

and
\((\xi_1,\xi_2,\xi_3)=(0.38,0.4,0.4)=(19/50,2/5,2/5)\). For this setup the paper
uses \(\rho=1_{\mathbb P}\), hence \(c_1=c_2=0\), and reports a successful \(k=49\)
exact quotient. The introduction describes a degree-at-most-21 calculation while
Section 5 calls the actual basis \(B_{19}\); resolve that convention discrepancy from
the definitions/source rather than silently choosing one. The paper says its exact
matrix computation took days and substantial memory, and explicitly states that larger
bases, the general support, and the prime-minorant machinery were developed for stronger
bounds but were not fully exploited because of resource and time limits.

## What counts as a solution

A complete solution must prove exactly \(H_1\le236\), unconditionally. It must contain
both of the following:

1. An analytic proof that every hypothesis of the exact version of Proposition 1 used
   in the argument is satisfied for the chosen support, equidistribution parameters,
   and prime minorant.
2. A reproducible exact certificate that the resulting finite-dimensional quotient is
   strictly greater than 1 for \(k=48\), together with a small independent checker.

The final implication must also verify directly that the supplied 48-tuple is admissible
and has diameter 236. For a finite set \(\mathcal H\) of 48 distinct integers, admissible
means that for every prime \(q\), the residues \(\mathcal H\bmod q\) do not cover all
classes modulo \(q\); it suffices to check primes \(q\le48\).

Partial progress is not a solution. In particular, none of the following is enough:

- a floating-point eigenvalue or numerical integration result;
- a quotient for \(k=49\), which only reproduces 240;
- a \(k=48\) quotient whose support or equidistribution hypotheses are unproved;
- setting \(c_1=c_2=0\) when Proposition 2 does not justify \(\rho=1_{\mathbb P}\);
- a conditional argument using Elliott--Halberstam or another unproved conjecture;
- a new admissible tuple without the analytic \(k=48\) sieve certificate;
- a reduction to an unproved lemma of essentially the same strength;
- a candidate proof without an independent adversarial audit and executable checker.

Work under the search prior that a 236 certificate is attainable by a serious extension
of Stadlmann's framework. This is a search heuristic, never a premise in the proof. Never
round an inequality in the favorable direction, omit a hard parameter case, or promote a
numerical near miss to a theorem.

## Multi-agent research protocol

Use multiagent v2 aggressively and dynamically. Use as many concurrent agents as the
session safely supports, but cap simultaneous memory-heavy computations so the machine
does not thrash. Do not make a one-time fixed assignment such as “two agents per
strategy.” The root agent must manage repeated adaptive rounds.

- Begin with a genuinely diverse portfolio. Seed independent work on source-fidelity
  extraction, exact integration, symmetry/sparsity compression, basis design, support
  parameter optimization, use of the nontrivial prime minorant, analytic inequalities,
  generalized-eigenvalue numerics, exact rational certification, and hostile proof
  auditing. These are approach families, not a fixed allocation.
- Do not tell most first-round agents the currently favored route. Give them the formal
  target and primary paper, and preserve independence long enough to reveal genuinely
  different mechanisms.
- Maintain an explicit `approach-registry.md`. Group attempts by mathematical mechanism,
  not superficial wording. For each family record its exact claim, evidence, blocker,
  falsification tests, and whether it is active, blocked, or retired.
- If many agents converge on merely raising the degree in the same implementation,
  redirect some toward support optimization, alternative symmetric bases, analytic
  comparison inequalities, exact block compression, or the general \(c_1,c_2,K\) route.
- Do not let an elegant reduction dominate if its remaining lemma is equivalent in
  strength to obtaining the desired quotient. Mark theorem-strength gaps as blocked.
  Reopen a blocked route only when an agent proposes a materially new invariant,
  construction, bound, or computational representation.
- Keep several incompatible routes alive across multiple rounds. Cross-pollinate only
  after independent agents have stated concrete formulas and exact blockers.
- Every agent must return concrete lemmas, parameter inequalities, algorithms, code,
  matrices, certificates, or explicit counterexamples to proposed sublemmas. Reject
  vague status reports, optimism, and claims that a large compatibility check is
  “routine.”
- Use adversarial agents throughout. A discovery agent must not be the final checker of
  its own certificate. Give auditors the claim and primary definitions, not the
  discoverer's persuasive narrative.
- The root agent must repeatedly synthesize, challenge, redirect, and launch new rounds.
  Do not stop because the first wave reports that the computation is too large or that a
  missing lemma is hard.

## Required research program

Create a working directory `prime-gap-236/` and checkpoint durable artifacts throughout.
Do not spend the whole session discussing possibilities in chat.

### Phase 1: source fidelity and collision check

1. Download the paper, its TeX source, and all indispensable cited primary results.
   Record URLs, versions, dates, and hashes in `sources.md`.
2. Read Stadlmann's paper end to end. Write `paper-map.md` containing an exact dependency
   graph from Proposition 1 to Theorem 1 and a notation table for
   \(T_k,I,J,K,M_1,M_2,A,B,\delta,\varepsilon,\xi_i,c_1,c_2\).
3. Search once, carefully, for a newer paper version, author code, coefficient vector,
   independent reproduction, or an already-posted \(H_1\le236\) claim. Record exact
   findings and dates. If a credible 236 proof already exists, audit it rather than
   claiming priority. After this initial gate, do mathematics; do not repeatedly browse
   for someone else's solution.
4. Resolve textual ambiguities by comparing PDF and TeX. In particular, settle the
   \(B_{19}\) versus degree-21 wording and check whether all displayed parameter
   inequalities are strict or non-strict.

### Phase 2: reproduce before extending

Build a clean implementation of Section 5's exact recursion/matrix multiplication. First
reproduce enough of the published \(k=49\) setup to validate the implementation, but do
not allow reproduction to consume the entire session.

- Use exact rational arithmetic wherever inputs are rational.
- Derive the recurrence from the paper; do not transcribe a black-box matrix dump.
- Check the integrator on low-dimensional, low-degree cases by an independent method
  such as direct symbolic integration or rigorous interval quadrature.
- Exploit permutation symmetry using integer partitions/orbit sums and cache canonical
  monomial types. Investigate sparse, block, streaming, and out-of-core constructions so
  degree 21--27 is feasible without excessive RAM.
- Profile time and memory. Preserve benchmark tables and exact regression tests.
- If the published coefficient vector is unavailable, state that explicitly and use
  internal cross-checks; do not claim to have independently validated the paper's
  headline merely because the formulas compile.

### Phase 3: attack \(k=48\) through genuinely different levers

Run adaptive rounds over at least these approach families, retiring any family only with
a concrete obstruction:

1. **Fixed-support, larger-basis route.** Keep Stadlmann's published rational parameters,
   compute \(B_D\) for increasing \(D\) through at least the practicable part of
   20--27, and determine the certified margin to 1 for \(k=48\).
2. **Better basis route.** Explore symmetry-adapted orthogonal bases, piecewise
   polynomials aligned with support strata, Schur/power-sum/monomial orbit bases, and
   basis pruning guided by generalized eigenvectors. Any numerically learned basis must
   be converted to an exact finite list.
3. **Support-parameter route.** Optimize rational
   \((\delta,A,B,\varepsilon,\xi_1,\xi_2,\xi_3)\) subject to every exact inequality in
   Propositions 2 and 3. Use numerics to search, then move the winning point into the
   strict interior and certify all constraints with rational or outward-rounded interval
   arithmetic.
4. **General-minorant route.** Test whether Stadlmann's intended Harman-sieve minorant
   with nonzero \(c_1,c_2\) enlarges the usable support enough to overcome the negative
   \(kc_2K\) term. Keep all signs and density losses exact.
5. **Structural-comparison route.** Seek monotonicity, interlacing, dimension-reduction,
   or perturbation lemmas comparing the \(k=49\) and \(k=48\) optimization problems.
   Reject any comparison that merely assumes the desired loss is small.
6. **Implementation route.** Find exact algebraic reorganizations—tensor contraction,
   partition-algebra blocks, sparse recurrences, modular arithmetic plus rational
   reconstruction, or certified interval linear algebra—that permit a substantially
   richer search than the original resource-limited calculation.

Maintain a machine-readable experiment ledger. Every numerical run must record the git
or file hash, parameters, basis, precision, estimated quotient, rigorous/error status,
wall time, and peak memory. A failed experiment is data; do not rerun it under a new name.

### Phase 4: exact certification

Once a numerical candidate exceeds 1 with comfortable margin:

1. Rationalize all parameters and the coefficient vector \(c\).
2. Rebuild \(M_1,M_2\) exactly, or with rigorously outward-rounded intervals whose total
   error is explicit.
3. Verify \(cM_1c^T>0\) and
   \(c(M_2-M_1)c^T>0\) exactly in the \(c_1=c_2=0\) case. In the general case, verify
   the corresponding exact \(M_2\) including the \(-kc_2K\) contribution. Do not assume
   \(M_1\) is invertible or that either matrix is positive definite; the certificate is
   the particular quadratic inequality.
4. Independently verify every support, minorant, and equidistribution hypothesis. Treat
   all cases of Proposition 3, including small-index branches and subset-sum/partition
   cases; testing samples is not a universal proof.
5. Verify the 48-tuple's size, diameter, distinctness, and admissibility modulo every
   prime at most 48.
6. Write a standalone checker that reconstructs rather than trusts serialized matrix
   entries. Run it in normal and optimized modes if possible. It must print the exact
   positive margin and fail closed on malformed or incomplete input.

## Adversarial audit checklist

Assign independent agents to try to break every proposed proof. At minimum test these
failure modes:

- accidentally proving only the already-known \(k=49\) case;
- changing \(k\) without recomputing every \(k\)-dependent combinatorial factor;
- favorable floating-point rounding or an unstable generalized eigenproblem;
- confusing a high-precision decimal with an exact proof;
- trusting precomputed matrix entries rather than reconstructing them;
- hidden linear dependence or singularity in the chosen basis;
- assuming positive definiteness where the paper does not provide it;
- incorrect inclusion--exclusion or double-counting on
  \(S_{BV}\cup S_Z\) and its intersections;
- mishandling open/closed support boundaries or the epsilon-enlargement step;
- applying a smooth-moduli equidistribution theorem to a modulus class outside its
  hypotheses;
- silently dropping the prime-minorant density loss or the negative \(K\) term;
- verifying Proposition 3 only numerically or for sampled tuples;
- circularly treating the fresh, unreviewed \(H_1\le240\) computation as an axiom;
- claiming \(H_1\le236\) without independently checking the admissible 48-tuple;
- novelty or priority claims based only on absence of a search-engine hit.

For every candidate proof, require an auditor to produce either `AUDIT PASS` with a
line-by-line dependency check or a smallest explicit failure/counterexample. Repair and
reaudit after every material change.

## Deliverables

Keep the following files current inside `prime-gap-236/`:

- `sources.md` — primary sources, versions, hashes, and collision check;
- `paper-map.md` — exact definitions and proof dependency graph;
- `approach-registry.md` — active/blocked/retired mechanisms and exact blockers;
- `experiments.tsv` — reproducible numerical/exact experiment ledger;
- `PROOF.md` — polished proof if the target is closed;
- `CERTIFICATE.md` plus compact machine-readable certificate data;
- `verify/` — independent standalone checker and tests;
- `AUDIT.md` — adversarial findings and repairs;
- `RESULT.md` — honest top-level status, exact theorem proved, exact verification
  commands, and remaining gap.

The final answer in chat must be concise and point to these artifacts. A valid success
answer states the exact theorem, exact positive certificate margin, verification command,
and audit status. Do not make any public post, contact authors, or claim priority.

If the target is not closed, do not disguise a near miss as success. At the hard session
limit, return only the strongest rigorously proved derivation, the best reproducible
certified lower bound on the quotient, the exact shortfall to 1, which approach families
were genuinely exhausted, and the next concrete experiment. A numerical quotient without
a rigorous error bound must be labeled heuristic.

Do not return merely because current approaches fail or agents report theorem-strength
gaps. Continue adaptive rounds, reopening blocked approaches only for genuinely new
mechanisms. Spend at least eight hours of active research before considering giving up,
unless the platform imposes a shorter hard wall; if so, checkpoint early and use every
available minute. The goal is a complete, auditable \(H_1\le236\) proof, not a literature
summary or an explanation of why the problem is difficult.
