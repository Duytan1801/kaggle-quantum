#!/usr/bin/env bash
# watch_public.sh — SUPERSEDED by harness/watch_public.py (2026-11-19).
#
# WHY THIS FILE CHANGED
# ----------------------
# The bash v1 of this watcher had a DEAD dataset channel:
#
#     poll dataset "$KG" datasets list --sort-by dateCreated --page-size 40
#     poll "dataset-$u" "$KG" datasets list --user "$u" --sort-by dateUpdated --page-size 10
#
# `--sort-by dateCreated` and `--sort-by dateUpdated` are NOT valid values.  The
# Kaggle CLI accepts only:  hottest | votes | updated | active | published
# so EVERY dataset poll failed on EVERY cycle, and because `poll()` redirected
# stderr to /dev/null the failure was completely silent.  The dataset channel
# produced ZERO detections for its entire life.
#
# Second defect: the findings went to /tmp/opencode/watch/new_releases.log and
# NOTHING EVER READ THAT FILE.  The wake prompt asked "Public tree changed?" with
# no sensor wired to the answer.  The watcher DID detect `ozertuu/28-23163` at
# 23:49 UTC on 2026-11-18 and `manvenderraparia/vqcc-28-23163` at 01:45 UTC on
# 2026-11-19 — both better than the tree we adopted hours later — and both sat
# unread.
#
# The replacement (harness/watch_public.py):
#   * valid sort keys only, and every poll is VALIDATED (a bad answer is a loud
#     POLL-FAILED line, never a silent no-op);
#   * DURABLE state in work/harvest/ (survives reboot) instead of /tmp;
#   * VERSION-AWARE keys, so a dataset updated after we saw it re-enters the queue;
#   * a SELF-GROWING publisher list, so a new publisher cannot hide;
#   * output = work/harvest/PENDING.tsv, which the wake prompt REQUIRES the agent
#     to read and adjudicate.  That file is the sensor.
#
# This shim keeps the old entry point working (and correct) for anything that
# still calls it.
set -u
ROOT=/home/bandoc/Downloads/opencode
exec /usr/bin/python3 "$ROOT/harness/watch_public.py" "$@"
