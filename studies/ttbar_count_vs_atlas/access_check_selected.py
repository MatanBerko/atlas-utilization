"""Record the Step 1 access check for the ONE ATLAS file Maryna selected.

Touches only that exact path and its parent components. Does not list, browse or
search any directory under /storage/agrp/marybo/, and writes nothing there.
"""
import io, json, os, stat, subprocess, datetime

SELECTED = ("/storage/agrp/marybo/DDP/BumpNet4AtlasOpenData/"
            "Test_master_atlas-utilization/data/"
            "atlas_mc_UnlimetedJets_test_ttbar_mc_20261003_210612/"
            "histograms/atlas_opendata_bumpnet.root")
OUT = ("/storage/agrp/berkom/atlas-utilization/work/ttbar_count_vs_atlas/dev/"
       "studies/ttbar_count_vs_atlas/evidence/access_check_2026-10-05.json")


def run(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, _ = p.communicate()
    return p.returncode, out.decode("utf-8", "replace").strip()


rec = {
    "date": datetime.date.today().isoformat(),
    "what": "Step 1 access check on the single ATLAS file selected by Maryna",
    "selected_file": SELECTED,
    "run_as": {"uid": os.getuid(), "whoami": run(["id", "-un"])[1],
               "groups": run(["id", "-Gn"])[1]},
    "method": "test -r / os.access / os.stat / getfacl on each path component",
    "components": [],
    "file_readable": None,
    "read_attempts": [],
    "parent_enterable": None,
    "blocking_component": None,
}

# Walk the path components top-down.
parts = [p for p in SELECTED.split("/") if p]
cur = ""
for p in parts:
    cur = cur + "/" + p
    entry = {"path": cur}
    try:
        st = os.stat(cur)
        entry["mode"] = stat.filemode(st.st_mode)
        entry["uid"] = st.st_uid
        entry["gid"] = st.st_gid
        entry["ctime"] = datetime.datetime.fromtimestamp(st.st_ctime).isoformat()
        entry["mtime"] = datetime.datetime.fromtimestamp(st.st_mtime).isoformat()
        entry["is_dir"] = stat.S_ISDIR(st.st_mode)
        if entry["is_dir"]:
            entry["enterable"] = os.access(cur, os.X_OK)
            if not entry["enterable"] and rec["blocking_component"] is None:
                rec["blocking_component"] = cur
        else:
            entry["readable"] = os.access(cur, os.R_OK)
    except OSError as e:
        entry["stat_error"] = "%s: %s" % (type(e).__name__, e.strerror)
        if rec["blocking_component"] is None:
            # the first component we cannot even stat is below the real blocker
            pass
    rc, out = run(["getfacl", "-p", cur])
    entry["getfacl_rc"] = rc
    entry["getfacl"] = out
    rec["components"].append(entry)

# Three independent read attempts, to rule out a transient mount problem.
for i in range(3):
    rc, out = run(["test", "-r", SELECTED])
    rec["read_attempts"].append({"attempt": i + 1, "test_r_rc": rc,
                                 "readable": rc == 0})
rec["file_readable"] = all(a["readable"] for a in rec["read_attempts"])
rec["parent_enterable"] = os.access(os.path.dirname(SELECTED), os.X_OK)

rec["conclusion"] = (
    "BLOCKED. The file is not readable and its parent directory is not "
    "enterable. The blocking component is %s. Steps 2-5 of the request cannot "
    "start." % rec["blocking_component"])

io.open(OUT, "w", encoding="utf-8", newline="\n").write(
    json.dumps(rec, indent=2, sort_keys=False) + "\n")
print(json.dumps({k: rec[k] for k in
                  ("file_readable", "parent_enterable", "blocking_component")},
                 indent=2))
print("WROTE", OUT)
