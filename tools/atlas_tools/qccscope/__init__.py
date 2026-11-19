"""qccscope: fast static / semistatic diagnosis of kickmix (kmx) circuits for the Google QCC competition.

Modules: kmx (parser), cost (task cost models, exchange rates), census, liveness (width profile, peaks, idle-gap
cover), structure (static motif detectors), values (bit-sliced sampled simulation, value fingerprints),
motifs (catalog, bounds, savings), report (markdown).  CLI: python -m qccscope report FILE --task invsqrt|dqi|chem
"""
__version__ = "0.1"
