## §22 (2026-11-16 ~02:4x–03:2x UTC) — the three cost models, read off the official verifiers (where the remaining GM actually lives)

We stopped guessing exchange rates and read the three official verifiers line by line. Every
"cost" in this competition is *exactly* one of these:

### Task I — invsqrt (`work/toolchain/verifiers/invsqrt/verify_submission_invsqrt.py`)

```python
toffolis = toffoli_count + t_count/4 + n_rot*rotation_t_count(eps)/4
score    = circuit.num_qubits * toffolis          # <-- the DECLARED qubit count
eps      = pi * min_margin / 2**64 / n_rot
rotation_t_count(eps) = 0.56*log2(1/eps) + 5.3
```
* `circuit.num_qubits` is the **declared register count**, not the live peak ⇒ a purely
  *relabeling* win is possible if any declared qubit is never touched.
  Measured on v121/v122/v123: 44 declared, 44 distinct used, max **44 simultaneously dirty**
  (symbolic dirty analysis, `work/tools/dirty_width.py`) ⇒ **no free relabel win**; the
  44 = 22 x-register + 22 scratch split is structural.
* Value of one qubit: cost ×43/44 ⇒ r_inv ×44/43 ⇒ **+0.216 GM** (the single biggest lever
  in the whole competition). maoxin123 got 46→44 (public file `f2cdab0b`, 2026-11-16 02:13 UTC)
  by "rescheduling which values live when" — the method is *not* documented in their notebook,
  only the artifact is published.
* Value of one Toffoli: 44/4 score units ⇒ **+0.0014 GM**. One rotation fewer: +0.0012 GM.
  Margin doubling: +0.0029 GM. ⇒ the invsqrt task is *width-bound*, not Toffoli-bound.

### Task II — DQI (`verifiers/dqi/verify_submission_dqi.py`)

```python
eps_hat  = (value_errors + phase_errors)/num_shots
eps_plus = clopper_pearson_upper_bound(k, n=102400, log2_delta=-128)
rep      = ln2 / -ln(1/2 + 2*sqrt(eps_plus))
score    = rep * (num_qubits ** 2) * toffolis
```
* **The repetition factor is already at its floor**: at k=0 errors the one-sided
  Clopper-Pearson bound is 8.6606e-4 ⇒ rep = 1.19126; at k=1 it is 9.1042e-4 ⇒ rep = 1.19673
  (worse), k=13 ⇒ 1.23736. So **zero observed errors is optimal** and "salt hedging"
  cannot lower the cost; deliberately degrading a file is counterproductive. (Verified
  numerically with the verifier's own functions.)
* `num_qubits**2` dominates: 890² = 792 100 vs T = 368 139 ⇒ width is worth **2.15× the
  Toffoli count**. One dqi qubit ⇒ −2/890 cost ⇒ **+0.021 GM**; 1% of T ⇒ +0.093 GM.
* The dqi circuit's Toffoli count is already 368 139.49 (boristown's C-merge + 8× HW-27 +
  C8 product retention); the public alternatives are dearer (4b350932 → 368 547.76;
  manwithacat HW-27 → 368 539.89).
* The *private* board re-runs with an unknown salt: alexchilton measured ccc2ab84 at
  0 errors (default salt) and 1 error (salt `notebook-verification`) ⇒ private cost may be
  ~0.4% worse on dqi, but the task still PASSes (the bound only fails above eps ≥ 1/16).

### Task III — chemistry (`verifiers/dfthcsos/verify.py`)

```python
score = lambda_eff * T_total * Q_total
T_total = angles_toffoli (2 * 4025) + heuristic_toffoli (6662) = 14712
Q_total = persistent(124) + max(temporary: inner_state_prep 303, angles 77) = 427
```
* **Q and the heuristic part of T are analytic functions of the npz tensor shape**
  (`SpinFreeData_V1(R=w.shape[0]=8, B=143, C=44, N=76, chi=10, beta=8)`):
  `b2 = ceil(log2 B)+chi+1 = 19`, `k2_opt = QR(R*C*B, b2)`, and the inner temporary is
  `ceil(log2(R*C*ceil(B/2^k2))) + (2^k2-1)*b2`. The model's `optimize_qubits` loop lowers
  `k2_opt` until that value fits under `beta*(N-1) = 600`; for **every** C we tested
  (32…88) the first fitting k2 is 4 ⇒ temporary 297 ⇒ inner workspace 303 ⇒ **Q = 427 is
  pinned**. Shrinking the ensemble dimension C therefore buys *nothing* in Q — the chem
  task is **loader-Toffoli-bound**, not shape-bound. (−3% of L = +0.16 GM; our re-plan
  lanes for the c44 words at k=1,2,3,8 all end in NO PLAN ⇒ closed.)
* `lambda_eff` refit is exhausted: tools/refit GRG for 25 min on the C8 npz moved
  46.92179043 → 46.92178792 (−2.5e-6). boristown's Stage-A/B Schur-nullspace refit
  (`f6e12f02`) reached 46.92161841 — only 1.7e-4 better.

### What this means for the campaign
1. The public best-of-each tree (v123 = maoxin123 `f2cdab0b` + boristown `ccc2ab84` +
   `f6e12f02`) is **GM 28.09487**, and it is the best *public* file on every task
   (cross-checked against alexchilton's verified-candidate table).
2. The remaining gap to the 30.285 frontier is therefore in **private width work**
   (invsqrt 44→43 = +0.216 GM; dqi 890→870 = +0.42 GM) — compiler projects, not
   configuration changes.
3. The cheap lane is still **adoption**: the public frontier moved three times in 90
   minutes tonight (8b410e77 → 2c125b39 → f2cdab0b), so we keep `harness/watch_public.sh`
   running and re-gate every new component.

**v123 receipt**: gate v38 (kernel version 38, 2026-11-16 03:03:43 UTC) —
`V123-RECEIPT-PASS`: shas 18/18, dqi @102,400 PASS 347,375,470,571.73 (0 value / 0 phase
errors), dfthcsos in-kernel PASS 294,762,732.98, invsqrt local PASS 75,006.366.
Submitted as ref 58412822.
