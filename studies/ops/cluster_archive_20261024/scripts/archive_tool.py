#!/usr/bin/env python
"""Cluster archive, Phase 2: manifest and verification of one folder's archive.

  manifest --root R --rel REL --out M
      Walk R/REL without following links and write a TSV, sorted by path:
        type  size  sha256  path
      type d (folder), f (regular file, sha256 of its content), l (symlink:
      size 0, sha256 "-", the target in a 5th column). Paths are relative to
      R, so they start with REL (the archive members have the same paths).

  verify --manifest M --archive A --out J
      1. gzip integrity: `gzip -t A`;
      2. stream A (tarfile 'r|gz'); the member set (path, type) must equal
         the manifest's exactly, with the same count;
      3. every regular member's sha256, recomputed from the stream, must
         equal the manifest's (a hard-link member takes its target's sha256;
         a symlink's target must equal the manifest's);
      4. writes J with the counts and verified true/false; exit 0 only if
         everything matches.

Read-only on the folder and the archive.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def cmd_manifest(a):
    rows = []
    top = os.path.join(a.root, a.rel)
    if os.path.islink(top) or not os.path.isdir(top):
        sys.exit(f"STOP: {top} is not a real folder")
    stack = [a.rel]
    while stack:
        rel = stack.pop()
        full = os.path.join(a.root, rel)
        rows.append(("d", 0, "-", rel, ""))
        for e in os.scandir(full):
            r = os.path.join(rel, e.name)
            if e.is_symlink():
                rows.append(("l", 0, "-", r, os.readlink(e.path)))
            elif e.is_dir(follow_symlinks=False):
                stack.append(r)
            elif e.is_file(follow_symlinks=False):
                rows.append(("f", e.stat(follow_symlinks=False).st_size, sha256_file(e.path), r, ""))
            else:
                sys.exit(f"STOP: unsupported file type at {e.path}")
    rows.sort(key=lambda t: t[3])
    for t in rows:
        if "\t" in t[3] or "\n" in t[3]:
            sys.exit(f"STOP: a path contains a tab or newline: {t[3]!r}")
    with open(a.out, "x") as f:   # never overwrite
        for t in rows:
            f.write("\t".join(str(x) for x in t[:4]) + ("\t" + t[4] if t[0] == "l" else "") + "\n")
    n = {k: sum(1 for t in rows if t[0] == k) for k in "dfl"}
    print(json.dumps({"rel": a.rel, "n_dirs": n["d"], "n_files": n["f"], "n_links": n["l"],
                      "n_entries": len(rows), "bytes": sum(t[1] for t in rows)}))


def cmd_verify(a):
    man = {}
    for line in open(a.manifest):
        p = line.rstrip("\n").split("\t")
        man[p[3]] = {"type": p[0], "size": int(p[1]), "sha": p[2], "target": p[4] if len(p) > 4 else None}
    res = {"manifest": a.manifest, "archive": a.archive,
           "archive_bytes": os.path.getsize(a.archive), "n_manifest_entries": len(man)}
    res["gzip_test_ok"] = subprocess.run(["gzip", "-t", a.archive]).returncode == 0
    seen, sha_by_path, bad = {}, {}, []
    with tarfile.open(a.archive, "r|gz") as tf:
        for m in tf:
            path = m.name.rstrip("/")
            if m.isdir():
                seen[path] = "d"
            elif m.issym():
                seen[path] = "l"
                if man.get(path, {}).get("target") != m.linkname:
                    bad.append(("symlink target", path))
            elif m.islnk():
                seen[path] = "f"
                sha = sha_by_path.get(m.linkname)
                sha_by_path[path] = sha
                if man.get(path, {}).get("sha") != sha:
                    bad.append(("hardlink sha256", path))
            elif m.isfile():
                seen[path] = "f"
                h = hashlib.sha256()
                f = tf.extractfile(m)
                for block in iter(lambda: f.read(1 << 20), b""):
                    h.update(block)
                sha_by_path[path] = h.hexdigest()
                ent = man.get(path)
                if ent is None or ent["sha"] != sha_by_path[path] or ent["size"] != m.size:
                    bad.append(("content", path))
            else:
                seen[path] = "?"
                bad.append(("unsupported member type", path))
    man_set = {(p, v["type"]) for p, v in man.items()}
    arc_set = set(seen.items())
    res["n_archive_members"] = len(seen)
    res["members_equal_manifest"] = man_set == arc_set and len(seen) == len(man)
    res["only_in_manifest"] = sorted(man_set - arc_set)[:20]
    res["only_in_archive"] = sorted(arc_set - man_set)[:20]
    res["n_files_sha_checked"] = sum(1 for v in seen.values() if v == "f")
    res["n_sha_or_target_mismatches"] = len(bad)
    res["mismatches"] = bad[:20]
    res["verified"] = bool(res["gzip_test_ok"] and res["members_equal_manifest"] and not bad)
    with open(a.out, "x") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: v for k, v in res.items() if not isinstance(v, list)}))
    return 0 if res["verified"] else 1


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("manifest")
    s.add_argument("--root", required=True)
    s.add_argument("--rel", required=True)
    s.add_argument("--out", required=True)
    s = sub.add_parser("verify")
    s.add_argument("--manifest", required=True)
    s.add_argument("--archive", required=True)
    s.add_argument("--out", required=True)
    a = ap.parse_args()
    return cmd_manifest(a) if a.cmd == "manifest" else cmd_verify(a)


if __name__ == "__main__":
    sys.exit(main())
