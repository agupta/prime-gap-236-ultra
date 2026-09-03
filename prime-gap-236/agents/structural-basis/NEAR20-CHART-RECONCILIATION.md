# Near-20 affine-chart reconciliation

The two independent line reconstructions report different numbers under the
label `infinity`: `0.9650080905...` in the endpoint-displacement chart and
`0.8004430412...` in the raw preconditioned-direction chart.  This is expected
and is not a discrepancy between their finite maxima.

Write the serialized endpoint as

\[
y=\gamma(\theta+t d),\qquad h=y-\theta.
\]

Then

\[
\theta+s h=\lambda(s)(\theta+u(s)d),\qquad
\lambda(s)=1+(\gamma-1)s,
\quad u(s)={\gamma t s\over\lambda(s)}.
\]

Consequently the `h`-chart point at infinity maps to the finite raw point
`u=gamma*t/(gamma-1)`, while raw infinity maps to the finite `h`-chart point
`s=-1/(gamma-1)`.  The two displayed infinity quotients therefore refer to
different projective points.  Only the set of stationary Rayleigh values and
its maximum is chart invariant.

The serialized base action is not exactly Euler-consistent with the separately
accumulated base form.  If

\[
E_D=\theta\mathbin{\cdot}A\theta-D_0,qquad
E_N=\theta\mathbin{\cdot}B\theta-N_0,
\]

the exact Fraction relation between the two reconstructed quadratics is

\[
Q_h(s)-\lambda(s)^2 Q_{\rm raw}(u(s))
=2(\gamma-1)E_Qs(1-s),\qquad Q\in\{D,N\}.
\]

The checker verifies this identity coefficient by coefficient.  Here
`E_D/D0=2.04215736656e-61` and `E_N/N0=9.74966794291e-62`.  At the maximizing
point the relative chart residuals are `7.5611e-62` for `D` and `3.6062e-62`
for `N`.  The two maximizing quotients differ by only
`3.84383000299e-62`:

```text
endpoint-displacement chart  0.971931517517355979068168524004296277247680251248806621019402223...
raw-direction chart          0.971931517517355979068168524004296277247680251248806621019402262...
```

Both are below one by about `0.02806848`; the negative discovery conclusion is
unaffected.  Neither number is an exact capped integral.

Run:

```sh
python3 agents/structural-basis/code/reconcile_near20_charts.py
python3 agents/structural-basis/tests/test_reconcile_near20_charts.py
python3 -O agents/structural-basis/tests/test_reconcile_near20_charts.py
```

The checker pins the displacement-chart artifact SHA `bf227a7f...` and the
independent raw-chart artifact SHA `6046a35c...`.
