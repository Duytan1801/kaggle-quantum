"""Static counts of a kmx text file: qubits (max qN index + 1), Toffoli-like ops (CCX, CCZ, CSWAP), op count
(every line except REGISTER / APPEND_TO_REGISTER). Used for circuits whose kmx text was exported by kickmix."""
import gzip, re, sys
QRE = re.compile(r"\bq(\d+)\b")
def stats(path):
    op = gzip.open if path.endswith(".gz") else open
    nq, toff, ops = -1, 0, 0
    with op(path, "rt") as f:
        for line in f:
            t = line.split(None, 1)
            if not t: continue
            if t[0] in ("REGISTER",):
                continue
            for m in QRE.findall(line):
                nq = max(nq, int(m))
            if t[0] == "APPEND_TO_REGISTER":
                continue
            ops += 1
            if t[0] in ("CCX", "CCZ", "CSWAP"):
                toff += 1
    return nq + 1, toff, ops
if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, *stats(p))
