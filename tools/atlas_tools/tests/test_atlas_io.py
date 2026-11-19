"""Fast tests for atlas_io and contributions/index.json (seconds, no network, no kickmix).

    python tools/tests/test_atlas_io.py      or      pytest tools/tests

Licence: Apache-2.0.
"""
import hashlib
import os
import sys

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
import atlas_io as A  # noqa: E402


def test_root_and_lookup():
    root = A.root()
    assert os.path.exists(os.path.join(root, "circuits.csv"))
    row = next(r for r in A.circuits().values() if r["task"] == "invsqrt" and r["included"] == "True")
    p = A.local_path(row["sha12"])
    assert os.path.exists(p) and len(A.read_bytes(p)) > 0


def test_metadata_only_raises():
    row = next((r for r in A.circuits().values() if r["included"] != "True"), None)
    if row is None:
        return
    try:
        A.local_path(row["sha12"])
    except FileNotFoundError as e:
        assert row["sha12"] in str(e)
    else:
        raise AssertionError("metadata-only file must raise")


def test_contributions_index():
    idx = A.contributions()
    for name, c in idx.items():
        assert c["task"] in ("invsqrt", "dqi", "chemistry") and c["first_public"]["url"].startswith("https://www.kaggle.com/code/")
        if c.get("path"):
            data = A.read_bytes(c["path"])
            if c["task"] == "chemistry":       # byte for byte the published npz
                assert hashlib.sha256(data).hexdigest() == c["sha256"], name
            else:
                assert data.startswith(b"APPEND_TO_REGISTER"), name
        for rid in c.get("receipts", []):
            assert any(f.startswith(rid + "__") for f in os.listdir(os.path.join(A.root(), "contributions", "receipts"))), rid


if __name__ == "__main__":
    for name, f in sorted(globals().items()):
        if name.startswith("test_") and callable(f):
            f()
            print("ok", name)
