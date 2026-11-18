#!/usr/bin/env python3
"""gh_push.py — push a staging directory to GitHub via the Git Data API
(no git binary needed on this box; token comes from $GH_TOKEN, never a file).

Usage: python3 gh_push.py <staging_dir> <repo=Owner/name> <branch> <message>
  - mirrors staging_dir contents INTO repo root (upsert; existing files at the
    same paths are updated, other paths untouched)
  - skips files > 95 MB (GitHub hard limit) with a printed warning
  - safe against compaction: all state passes through explicit API calls

Layout convention for the campaign (staging dirs):
  state/    ledgers + hypothesis state (RESEARCH_STATE.md, GOALS.md, ...)
  harness/  wake prompt + gates + scripts
  tools/    work/tools scripts
  trees/vN/ gated submission.zip + SHA_TABLE.json + RECEIPT.json (NOT raw
            kmb > 100 MB; the zip preserves the exact submitted bytes)
"""
import base64, json, os, sys, urllib.request

REPO_LIMIT = 95 * 1024 * 1024
BLOB_LIMIT = 10 * 1024 * 1024   # above this, upload as a release asset (raw binary)


class GH:
    def __init__(self, repo, token):
        self.repo, self.tok = repo, token
        self.n = 0
    def req(self, method, path, body=None, raw=False, data=None, ctype=None):
        url = path if path.startswith("http") else f"https://api.github.com/repos/{self.repo}/{path}"
        payload = data if data is not None else (None if body is None else json.dumps(body).encode())
        hdrs = {
            "Authorization": f"Bearer {self.tok}",
            "Accept": "application/vnd.github+json",
        }
        if payload is not None:
            hdrs["Content-Type"] = ctype or "application/json"
        r = urllib.request.Request(url, data=payload, method=method, headers=hdrs)
        with urllib.request.urlopen(r) as resp:
            self.n += 1
            b = resp.read()
            if raw:
                return b, resp.status
            return json.loads(b) if b else None
    def blob(self, path):
        content = base64.b64encode(open(path, "rb").read()).decode()
        j = self.req("POST", "git/blobs", {"content": content, "encoding": "base64"})
        return j["sha"], hashlib(path), os.path.getsize(path)

    def upload_asset(self, rel_path, src, label):
        """Big file → release asset (raw binary upload, up to 2GB)."""
        tag = "assets"
        try:
            rel = self.req("GET", f"releases/tags/{tag}")
        except urllib.error.HTTPError:
            rel = None
        if not rel:
            rel = self.req("POST", "releases", {
                "tag_name": tag, "name": "campaign-assets",
                "body": "Binary assets too large for the git blob API (kmb/zip trees)."})
        upload_url = rel["upload_url"].split("{")[0]
        name = rel_path.replace("/", "__")
        import urllib.parse
        q = urllib.parse.urlencode({"name": name, "label": label[:100]})
        # delete pre-existing asset with same name
        for a in rel.get("assets", []):
            if a["name"] == name:
                self.req("DELETE", f"releases/assets/{a['id']}")
        with open(src, "rb") as f:
            data = f.read()
        out, status = self.req("POST", f"{upload_url}?{q}", data=data,
                               ctype="application/octet-stream", raw=True)
        j = json.loads(out)
        print(f"asset {rel_path} {len(data)}B → {j.get('browser_download_url')} (id {j.get('id')})", flush=True)
        return j.get("id")

def hashlib(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def collect(root):
    out = []
    for r, _, names in os.walk(root):
        if "__pycache__" in r:
            continue
        for n in sorted(names):
            p = os.path.join(r, n)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            out.append((rel, p))
    return out

def main():
    if len(sys.argv) != 5:
        print(__doc__); sys.exit(2)
    staging, repo, branch, msg = sys.argv[1:]
    tok = os.environ.get("GH_TOKEN", "")
    if not tok:
        # durable fallback: ~/.config/qcc/gh_token (mode 600, never committed)
        try:
            tok = open(os.path.expanduser("~/.config/qcc/gh_token")).read().strip()
        except Exception:
            tok = ""
    if not tok:
        print("GH_TOKEN not set (and ~/.config/qcc/gh_token missing)"); sys.exit(1)
    gh = GH(repo, tok)

    # ref check FIRST: empty repo must be bootstrapped before blob creation
    parents = []
    try:
        ref = gh.req("GET", f"git/ref/heads/{branch}")
        parents = [ref["object"]["sha"]]
    except Exception as e:
        try:
            body = json.loads(e.read() or b"{}")
        except Exception:
            body = {}
        if "empty" not in str(body.get("message", "")).lower():
            raise
        print("empty repo → bootstrapping first commit via Contents API", flush=True)
        files_pre = collect(staging)
        small = min(files_pre, key=lambda f: os.path.getsize(f[1]))
        if os.path.getsize(small[1]) > 1024 * 1024:
            print("no small file to bootstrap with — abort"); sys.exit(1)
        content = base64.b64encode(open(small[1], "rb").read()).decode()
        gh.req("PUT", f"contents/{small[0]}", {"message": msg + " (bootstrap)", "content": content, "branch": branch})
        parents = [gh.req("GET", f"git/ref/heads/{branch}")["object"]["sha"]]

    files = collect(staging)
    skipped, assets, tree_entries = [], [], []
    for rel, p in files:
        sz = os.path.getsize(p)
        if sz > REPO_LIMIT:
            skipped.append((rel, sz)); continue
        if sz > BLOB_LIMIT:
            assets.append((rel, p)); continue
        bsha, lsha, lsz = gh.blob(p)
        tree_entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": bsha})
        print(f"blob {rel} {lsz}B sha={lsha[:12]}", flush=True)
    for rel, p in assets:
        gh.upload_asset(rel, p, msg)
    for rel, sz in skipped:
        print(f"SKIP (>100MB limit): {rel} {sz/1e6:.0f}MB — record its sha + how to rebuild instead", flush=True)

    # base commit
    if not parents:
        parents = [gh.req("GET", f"git/ref/heads/{branch}")["object"]["sha"]]

    tree = gh.req("POST", "git/trees", {"tree": tree_entries, "base_tree": parents[0]} if parents else {"tree": tree_entries})
    if parents:
        base = gh.req("GET", f"git/trees/{parents[0]}?recursive=1")
        have = {e["path"]: e for e in base["tree"] if e["type"] == "blob"}
        merged = {e["path"]: e for e in tree_entries}
        for path, e in have.items():
            if path not in merged:
                merged[path] = {"path": path, "mode": e.get("mode", "100644"), "type": "blob", "sha": e["sha"]}
        tree = gh.req("POST", "git/trees", {"tree": list(merged.values())})
    commit = gh.req("POST", "git/commits", {"message": msg, "tree": tree["sha"], "parents": parents})
    if parents:
        gh.req("PATCH", f"git/refs/heads/{branch}", {"sha": commit["sha"], "force": False})
    else:
        gh.req("POST", "git/refs", {"ref": f"refs/heads/{branch}", "sha": commit["sha"]})
    print(f"PUSHED commit {commit['sha'][:12]} on {branch}: {len(tree_entries)} blobs, {len(assets)} assets, {len(skipped)} skipped, {gh.n} api calls")

if __name__ == "__main__":
    main()
