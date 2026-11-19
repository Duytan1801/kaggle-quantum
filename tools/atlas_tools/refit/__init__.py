"""refit: numpy DF-THC weight refit for the chemistry (dfthcsos) task of Google's Verifiable Quantum Circuit
Compilation competition.

Lowers lambda_eff of a submission.npz by changing only W and H2_I, at fixed angle words (so the 15 angle-loader
circuits stay valid), while error_1, error_2 and E_gap keep a margin inside the verifier's gates.

Modules
  chemeval  exact metrics with the verifier's own math (finds the competition verifier at run time)
  model     the same metrics with analytic gradients (Model, SplitProblem, split, unsplit)
  grg       generalised reduced-gradient refit (numpy port of prvsiyan's refit_grg.py, Apache-2.0)
  grg2      GRG with a full Newton restoration (the variant used in our public notebooks)
  al        augmented-Lagrangian alternative (L-BFGS-B inner solver) and save_npz
CLI: python -m refit eval NPZ ... | python -m refit run --start NPZ --minutes M --out DIR

Licence: Apache-2.0. The competition verifier is not part of this package (Competition Data, not redistributed).
"""
__version__ = "2.0"
