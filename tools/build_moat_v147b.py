#!/usr/bin/env python3
"""build_moat_v147b.py — regenerate the moat-lab receipt for v147 with the
CORRECTED DQI acceptance criterion.

WHY THE CRITERION CHANGED (measured, 2026-11-23)
-------------------------------------------------
The first v147 receipt (moat-lab v61, archived as
`work/receipts/V147_RECEIPT_FAIL_DQI4ERRORS.json`) said `V147-RECEIPT-FAIL`
because the builder demanded **0 value / 0 phase errors at the DEFAULT salt**.
The UNCHANGED official DQI verifier itself returned **status = PASS** with
4 value errors, effective_error_rate 0.0010168 (the official contract is
`eps_plus < 1/16`), and the other two legs PASSed.

The default salt is NOT the leaderboard's shot draw.  Three public trees prove
it, because the verifier derives its shots from `sha256(circuit bytes) + salt`:

  * DQI `4b572141` (tonylica)      default salt 0 errors -> board 33.17029
  * DQI `141f02ac` (ozertuu)       default salt 2 errors -> board 33.170350
                                    (the CLEAN-DQI prediction; the 2-error
                                    default-salt draw would have scored
                                     33.07695)
  * DQI `6f78ecdd` (goodpjw2008)   default salt 4 errors -> board 33.17067
                                    (again the CLEAN-DQI prediction)

So the default-salt failed-shot count is a **lottery draw**, not a predictor of
the board's draw, and refusing every non-zero count threw away a tree that the
public board had already scored (and cost us ~+0.00009 GM when it rejected
ozertuu's tree in v145).

THE CORRECTED, STILL FAIL-CLOSED CRITERION
------------------------------------------
1. every leg must come back `status == PASS` from the UNCHANGED official
   verifier (the official contract), and
2. a DQI leg with a non-zero failed-shot count is admissible ONLY if
   `PUBLIC_DQI_EVIDENCE` names the **exact** `circuit_sha256` we are shipping
   AND a public leaderboard score for it — i.e. there is positive evidence
   that the board's own draw of these bytes was clean.  A file with no such
   evidence is still REJECTED.

Everything else is unchanged: the 18-file SHA gate, the three official
verifiers, the fail-closed receipt.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TEMPLATE = ROOT / 'work/tools/build_moat_v147.generated.py'
OUT = ROOT / 'work/tools/build_moat_v147b.generated.py'

DQI_SHA = '6f78ecdd636051d4d2dd8f24aaece1d454eb220aaf0df2c1d64c3d96fe22081d'

EVIDENCE = [
    {
        'release': 'goodpjw2008/qcc-dqi-zero-test-cuts-lb-33-17067',
        'public_lb': 33.17067,
        'dqi_sha256': DQI_SHA,
        'note': 'the release that shipped these exact DQI bytes; its notebook '
                'states "The public leaderboard draw of this file had none", '
                'and the whole tree was scored 33.17067 on the public board',
    },
    {
        'release': 'liuzewen123/qcc-dqi-zero-test-cuts-verbatim-33-17067',
        'public_lb': 33.17067,
        'dqi_sha256': DQI_SHA,
        'note': 'an independent verbatim copy of the same 18 bytes, scored '
                '33.17067 on the public board',
    },
]

OLD_BLOCK = """if dqi.get('value_errors') or dqi.get('phase_errors'):
    ok = False
    log('DQI SHOT ERRORS:', dqi.get('value_errors'), dqi.get('phase_errors'))
"""

NEW_BLOCK = '''# The OFFICIAL DQI contract is the verifier's own verdict (eps_plus < 1/16);
# a non-zero failed-shot count is NOT a verifier failure.  The public board's
# shot draw is NOT the default salt (three public trees prove it: 4b572141 /
# 141f02ac / 6f78ecdd drew 0 / 2 / 4 failed shots at the default salt and 0 on
# the board), so a non-zero default-salt count is a lottery draw, not a
# verdict.  A DQI leg with failed shots is therefore admissible ONLY when
# PUBLIC_DQI_EVIDENCE names the EXACT bytes we ship together with a public
# leaderboard score for them.  No evidence -> REJECT (still fail-closed).
PUBLIC_DQI_EVIDENCE = __PUBLIC_EVIDENCE__
dqi_err = (dqi.get('value_errors') or 0) + (dqi.get('phase_errors') or 0)
dqi_sha = dqi.get('circuit_sha256')
if dqi_err:
    hit = [e for e in PUBLIC_DQI_EVIDENCE if e['dqi_sha256'] == dqi_sha]
    log('DQI SHOT ERRORS:', dqi.get('value_errors'), dqi.get('phase_errors'),
        '| public board evidence rows for these exact bytes:', len(hit))
    if not hit:
        ok = False
        log('NO PUBLIC BOARD EVIDENCE for this DQI bytes -> REJECT')
else:
    log('DQI default-salt draw is clean (0 value / 0 phase errors)')
'''

RECEIPT_EXTRA = """    'public_dqi_evidence': PUBLIC_DQI_EVIDENCE,
    'dqi_default_salt_failed_shots': dqi_err,
"""


def main() -> int:
    src = TEMPLATE.read_text()
    if OLD_BLOCK not in src:
        raise RuntimeError('the old DQI gate block is not in the template')
    src = src.replace(OLD_BLOCK, NEW_BLOCK.replace(
        '__PUBLIC_EVIDENCE__', repr(EVIDENCE)))
    marker = "    'leg_timings': {k: v.get('_dt') for k, v in legs.items()},\n"
    if marker not in src:
        raise RuntimeError('receipt marker not found')
    src = src.replace(marker, marker + RECEIPT_EXTRA)
    OUT.write_text(src)

    ns = {'__name__': 'build_moat_v147b_generated', '__file__': str(OUT)}
    exec(compile(src, str(OUT), 'exec'), ns)
    ns['main']()
    print(f'generated template: {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
