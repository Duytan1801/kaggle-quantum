# refit: numpy DF-THC weight refit (chemistry task)

Lowers `lambda_eff` of a chemistry `submission.npz` by changing **only** `W` and `H2_I`, at fixed angle words, so the
15 `angle_k_*.kmb` loader circuits of the submission stay valid. Every saved point is checked with the verifier's own
math (`dfthcsos.scoreinfra.dfthc_math`): `error_1 < 0.02`, `error_2 < 0.02` and `E_gap > 3.914898`, each with a slack of
at least `--accept-margin` (default 1e-9 Ha).

This is the code that produced the chemistry weights of our public notebook
[QCC 27.3122 | Frontier + Finer Chemistry Refit](https://www.kaggle.com/code/asteriospanoras/qcc-27-3122-frontier-finer-chemistry-refit)
(versions 2, 4 and 5; results in `contributions/chemistry_refits/`, files in `factorizations/`). Version 5 of that notebook runs it in
the notebook itself for 22 minutes.

## Use it in a Kaggle notebook

Attach this dataset **and** the competition data (the verifier is Competition Data and is not included here).

```python
import subprocess, sys
TOOLS = "/kaggle/input/qcc-circuit-atlas/tools"
subprocess.run([sys.executable, "-m", "refit", "eval", "/kaggle/working/sub/dfthcsos/submission.npz"], cwd=TOOLS, check=True)
subprocess.run([sys.executable, "-m", "refit", "run", "--start", "/kaggle/working/sub/dfthcsos/submission.npz",
                "--minutes", "20", "--out", "/kaggle/working/refit"], cwd=TOOLS, check=True)
# -> /kaggle/working/refit/submission.npz and refit_report.json; then run the official dfthcsos/verify.py
```

or from Python:

```python
import sys; sys.path.insert(0, "/kaggle/input/qcc-circuit-atlas/tools")
from refit import chemeval as ce
ce.setup()                       # finds .../verifiers under /kaggle/input
print(ce.evaluate_npz("/kaggle/input/qcc-circuit-atlas/factorizations/5a75386681c8.npz")["lambda_eff"])
```

Off Kaggle: `--verifiers DIR` (the folder that contains `dfthcsos/`) or `QCC_VERIFIERS=DIR`; `--fcidump FILE` or
`QCC_FCIDUMP` when the FCIDUMP is not next to the verifier.

## Files

| File | What it is |
|---|---|
| `chemeval.py` | Exact metrics of a submission.npz with the verifier's functions; finds the verifier at run time. |
| `model.py` | The same metrics (error_1, error_2, E_gap, Lambda, lambda_eff) with analytic gradients at fixed words; `SplitProblem` writes the weights as non-negative parts so the L1 terms of Lambda are linear. |
| `grg.py` | Generalised reduced-gradient refit on the active constraint surface (L-BFGS direction projected on the tangent space, Newton restoration for every trial point). |
| `grg2.py` | GRG with a full Newton restoration (Jacobian recomputed each step); the variant used in our notebooks. |
| `al.py` | Augmented-Lagrangian alternative (L-BFGS-B inner solver), Newton restoration, `save_npz`. |
| `__main__.py` | CLI: `python -m refit eval NPZ ...`, `python -m refit run --start NPZ --minutes M --out DIR`. |
| `tests/test_refit.py` | Tests in seconds without competition data (split algebra, gradients of the split problem against finite differences, gates, CLI); one optional test against the verifier. |

CPU and memory: building the model takes about a minute and ~1 GB RAM (the (R*B)^2 matrices); each GRG iteration
takes a few seconds for the (8, 143, 44) table. The time budget is checked at every exact check (`--check-every`), so a run can end a few minutes after `--minutes`.

## Credits

* **prvsiyan** — the generalised reduced-gradient refit (`code/refit_grg.py`) and `chemlib.py` in the dataset
  [prvsiyan/vqcc-verified-best-of-circuits-1106a](https://www.kaggle.com/datasets/prvsiyan/vqcc-verified-best-of-circuits-1106a)
  (Apache-2.0). `grg.py` is a numpy port of `refit_grg.py` (torch autograd replaced by the analytic gradients of
  `model.py`, any table shape, a save callback); `grg2.py` adds the full Newton restoration.
* **Lera (marculera)** — the DF-THC refit line (`refit_weights.py`, the augmented-Lagrangian refit `refit_al.py`)
  and the gauge ideas of her public notebooks and datasets (e.g.
  [df-thc 11.2x](https://www.kaggle.com/code/marculera/df-thc-11-2x-codes-on-the-xor-of-five-words)), Apache-2.0;
  the error_2 expansion through the Gram matrix follows her code and prvsiyan's.
* The metric formulas are the competition verifier's (Google Quantum AI / Qualtran).

Licence of this folder: Apache-2.0. Ported parts keep the copyright of their authors (Apache-2.0).
