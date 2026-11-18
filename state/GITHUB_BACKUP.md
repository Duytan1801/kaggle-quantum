# GITHUB BACKUP — durable campaign mirror

**Repo:** `Duytan1801/kaggle-quantum` (branch `main`) — created by the user for
this campaign. **Do not touch** `Duytan1801/quantum-result` (unrelated project).

## Why
`/tmp/opencode` is volatile scratch; contexts compact; the machine can restart.
GitHub is the independent, durable, verifiable copy of the campaign's state.
Local disk = working copy; GitHub = durable copy. Both must reconstruct the
campaign.

## What is mirrored
| Path | Contents |
|------|----------|
| `state/` | `KERNEL_WATCH.md`, `MOAT_LOOP.md`, `RESEARCH.md`, `work/RESEARCH_STATE.md` (live hypothesis queue), `work/GOALS.md`, `work/RESEARCH_DOCTRINE.md`, `work/CALIBRATION.md` |
| `harness/` | `CONTINUE_PROMPT.md` (wake prompt), `submit_gate.sh` (mechanical two-receipt gate), `run_capped.sh`, watcher/poller scripts |
| `tools/` | `work/tools/*.py|sh` — the campaign's actual capability (analysis, build, gate, lint, push tools) |
| `trees/vN/` | the **gated** `submission.zip` (exact submitted bytes) + `SHA_TABLE.json` + `RECEIPT.json` + `README.txt` |
| `MANIFEST.json` | sha256 + size of every mirrored file |

## Why the tree zip is a release asset, not a git blob
Raw `dqi.kmb` is 457 MB — over GitHub's hard 100 MB file limit — and even the
50 MB zip exceeds what the git-blob API accepts in one base64 POST (502).
Large binaries therefore upload to the repo's `assets` release
(`https://github.com/Duytan1801/kaggle-quantum/releases/download/assets/...`).
The zip preserves the exact submitted bytes (verified: remote sha ==
local gated sha).

## How to sync
```bash
bash harness/gh_sync.sh "label describing what changed"
```
- Token: `$GH_TOKEN`, else `~/.config/qcc/gh_token` (mode 600). The token is
  **never** committed to the repo, the prompt, or the ledgers.
- Implementation: `work/tools/gh_push.py` (GitHub Git Data API — this box has
  no `git` binary; blobs for small files, release assets for big ones, tree +
  commit + ref update; upsert-only, never deletes remote paths).
- Log: `work/gh_sync.log`.

## Verification (byte-exactness matters)
```bash
export GH_TOKEN="$(cat ~/.config/qcc/gh_token)"
curl -sL -H "Authorization: Bearer $GH_TOKEN" -H "Accept: application/octet-stream" \
  "https://api.github.com/repos/Duytan1801/kaggle-quantum/releases/assets/<ID>" -o /tmp/a.zip
sha256sum /tmp/a.zip /tmp/opencode/gate_zip.*/submission.zip
```
Verified for v131: `33cc1850f91301b2…` == local gated zip. ✔

## Cadence
Every wake (enforced by `harness/CONTINUE_PROMPT.md`), and immediately after
any change to a gated tree, a scored submission, or the hypothesis queue.
