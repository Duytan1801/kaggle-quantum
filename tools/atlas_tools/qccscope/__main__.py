"""CLI: python -m qccscope report FILE [FILE ...] --task invsqrt|dqi|chem [--lanes N] [--exhaustive] [--out OUT.md]"""
import argparse
import sys

from . import report as Rp


def main(argv=None):
    ap = argparse.ArgumentParser(prog="qccscope")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report", help="markdown diagnosis report")
    r.add_argument("files", nargs="+")
    r.add_argument("--task", required=True, choices=["invsqrt", "dqi", "chem"])
    r.add_argument("--lanes", type=int, default=256, help="sampled inputs for the value scan")
    r.add_argument("--exhaustive", action="store_true", help="invsqrt: simulate every x (3,133,452 lanes, seconds)")
    r.add_argument("--no-values", action="store_true", help="skip the value scan")
    r.add_argument("--cache", default=None, help="directory for the parsed-op cache (use for the DQI file)")
    r.add_argument("--width-test", type=int, default=0, metavar="LANES",
                   help="run the peak-episode rebuild test with this many sampled lanes (> live wires, e.g. 1024)")
    r.add_argument("--npz", default=None, help="chem: submission npz with angle_words (default: *.npz next to the files)")
    r.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    res = [Rp.analyse(f, a.task, lanes=a.lanes, exhaustive=a.exhaustive, values=not a.no_values, cache_dir=a.cache,
                      width_lanes=a.width_test, npz=a.npz)
           for f in a.files]
    text = Rp.render_family(res) if (a.task == "chem" and len(res) > 1) else "\n".join(Rp.render(x) for x in res)
    if a.out:
        open(a.out, "w").write(text)
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
