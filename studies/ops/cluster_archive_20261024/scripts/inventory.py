#!/usr/bin/env python
"""Read-only inventory of /storage/agrp/berkom/atlas-utilization (Phase 1).

Per directory directly under the root, and one level deeper under every
top-level folder except envs/ and home_backup_20261018/ (single totals only):
inodes (files + dirs + links, what lfs quota counts), files, dirs, symlinks,
apparent bytes, allocated bytes (st_blocks*512) and the newest mtime of any
entry. Never follows symlinks; only lstat/scandir. Writes one JSON.
"""
import json
import os
import sys
import time

ROOT = "/storage/agrp/berkom/atlas-utilization"
TOTALS_ONLY = {"envs", "home_backup_20261018"}


def walk(path):
    st = os.lstat(path)
    t = {"inodes": 1, "files": 0, "dirs": 1, "links": 0, "bytes": 0,
         "alloc_bytes": st.st_blocks * 512, "newest_mtime": st.st_mtime, "errors": 0}
    stack = [path]
    while stack:
        d = stack.pop()
        try:
            it = list(os.scandir(d))
        except OSError:
            t["errors"] += 1
            continue
        for e in it:
            try:
                s = e.stat(follow_symlinks=False)
            except OSError:
                t["errors"] += 1
                continue
            t["inodes"] += 1
            t["alloc_bytes"] += s.st_blocks * 512
            t["newest_mtime"] = max(t["newest_mtime"], s.st_mtime)
            if e.is_symlink():
                t["links"] += 1
            elif e.is_dir(follow_symlinks=False):
                t["dirs"] += 1
                stack.append(e.path)
            else:
                t["files"] += 1
                t["bytes"] += s.st_size
    t["newest"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(t["newest_mtime"]))
    return t


def main():
    out = {"root": ROOT, "generated": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "top": {}, "sub": {}}
    for e in sorted(os.scandir(ROOT), key=lambda e: e.name):
        if e.is_dir(follow_symlinks=False):
            out["top"][e.name] = walk(e.path)
            if e.name not in TOTALS_ONLY:
                out["sub"][e.name] = {}
                for c in sorted(os.scandir(e.path), key=lambda c: c.name):
                    if c.is_dir(follow_symlinks=False):
                        out["sub"][e.name][c.name] = walk(c.path)
                    else:
                        s = c.stat(follow_symlinks=False)
                        out["sub"][e.name][c.name] = {
                            "inodes": 1, "files": 1, "dirs": 0, "links": int(c.is_symlink()),
                            "bytes": s.st_size, "alloc_bytes": s.st_blocks * 512,
                            "newest_mtime": s.st_mtime,
                            "newest": time.strftime("%Y-%m-%d %H:%M", time.localtime(s.st_mtime)),
                            "errors": 0, "loose_file": True}
        else:
            s = e.stat(follow_symlinks=False)
            out["top"][e.name] = {"inodes": 1, "files": 1, "bytes": s.st_size, "loose_file": True}
    out["total_inodes_including_root"] = 1 + sum(v["inodes"] for v in out["top"].values())
    json.dump(out, open(sys.argv[1], "w"), indent=1)
    print("total inodes under root:", out["total_inodes_including_root"])
    for k, v in out["top"].items():
        print(k, v.get("inodes"), v.get("bytes"))


if __name__ == "__main__":
    main()
