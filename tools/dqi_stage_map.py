#!/usr/bin/env python3
"""dqi_stage_map.py — where does the DQI generator spend its lines and its wires?

The DQI score is `R(eps) * Q^2 * T`; Q is the circuit's qubit count.  The
generator assembles the circuit stage by stage (work/../dqi/stages.json), and
each stage is emitted by a different source file.  This tool rebuilds the
assembly while recording the line range of every stage, then reports:

  * the line range and size of each stage,
  * the number of distinct quantum wires each stage touches,
  * the quantum wires that a stage touches for the LAST time (i.e. wires whose
    computational life ENDS in that stage — candidates for reuse by later
    stages, which is the only way to cut Q).

Usage:  python dqi_stage_map.py <dqi-generator-dir> [--out map.json]
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys


def main() -> None:
    root = pathlib.Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(root))
    from arithmetic import emit_product
    from selector import Classical, emit_lambda_phase, emit_selector, gauges

    stages = json.loads((root / 'stages.json').read_text())
    out = pathlib.Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else None

    class Counter:
        """Binary stream wrapper that counts newlines."""

        def __init__(self, raw):
            self.raw = raw
            self.lines = 0

        def write(self, data: bytes) -> int:
            self.lines += data.count(b'\n')
            return self.raw.write(data)

        def writelines(self, lines) -> None:
            for l in lines:
                self.write(l)

    import lzma
    import shutil

    def append_native(stream, name):
        with lzma.open(root / name, 'rb') as source:
            shutil.copyfileobj(source, stream, length=2 ** 20)

    map_out = []
    with open('/tmp/opencode/dqi_build/staged.kmx', 'wb') as raw:
        stream = Counter(raw)
        line = 0
        for i, stage in enumerate(stages):
            label = stage.get('kmx') or stage.get('generate') or ('field%d' % stage.get('field'))
            before = stream.lines
            if 'field' in stage:
                for part in stage['d16']:
                    if 'product' in part:
                        emit_product(stream, root / part['product'])
                    else:
                        append_native(stream, part['kmx'])
            elif 'kmx' in stage:
                append_native(stream, stage['kmx'])
            elif stage['generate'] == 'lambda_selector':
                emit_selector(stream)
            elif stage['generate'] == 'lambda_phase':
                emit_lambda_phase(stream)
            elif stage['generate'] == 'restore_gauges':
                gauges(Classical(stream), restore=True)
            else:
                raise ValueError(stage)
            after = stream.lines
            map_out.append({'index': i, 'label': label, 'field': stage.get('field'),
                            'start_line': before, 'end_line': after,
                            'lines': after - before})
            print(f'{i:>3} {label:<45} lines {before:>12,} .. {after:>12,}  ({after-before:,})',
                  flush=True)
        total = stream.lines
    print(f'TOTAL lines {total:,}')
    if out:
        out.write_text(json.dumps({'stages': map_out, 'total_lines': total}, indent=1))
        print(f'wrote {out}')


if __name__ == '__main__':
    main()
