# Mac toolchain smoke test — 2026-10-14

- **Date/time:** 2026-10-14 11:21:14 IDT (Mac local clock)
- **Machine:** Mac17,2, architecture `arm64` (Apple Silicon)
- **macOS:** 27.0.1 (build 26A434)
- **Branch:** `test/mac-toolchain-check-20261014` (created from `master`)
- **master / origin/master commit:** `ba89791b5fe0167070c7e1bb2f3c231802f064fd` — "Ignore local Mac config (config.mac.yaml)"
- **upstream/master commit:** `e1ce8bb2bd648a7c35d80b4efe490a20025892b9` — "Add ATLAS-style overlap removal (#32)"
- **Remotes:** `origin` = git@github.com:MatanBerko/atlas-utilization.git (fetch+push); `upstream` = https://github.com/Zhavi221/atlas-utilization.git (fetch), push URL `DISABLED` (added in this session)

All outputs below were captured by running the commands.

## Local environment

```
$ which python
/opt/homebrew/Caskroom/miniforge/base/envs/hep/bin/python
$ python --version
Python 3.11.17
$ conda info --envs
base                     /opt/homebrew/Caskroom/miniforge/base
hep                  *   /opt/homebrew/Caskroom/miniforge/base/envs/hep
research311              /opt/homebrew/Caskroom/miniforge/base/envs/research311
$ python -c "import uproot, awkward, vector, numpy, matplotlib, yaml; print(...)"
5.7.7 2.14.0 1.9.0 2.4.6 3.11.2
   (uproot 5.7.7, awkward 2.14.0, vector 1.9.0, numpy 2.4.6, matplotlib 3.11.2; yaml imported OK)
$ python -c "import ROOT; print(ROOT.gROOT.GetVersion())"
6.40.04
$ python -c "import XRootD; print('xrootd python bindings OK')"
xrootd python bindings OK
$ sw_vers
ProductName:		macOS
ProductVersion:		27.0.1
BuildVersion:		26A434
$ uname -m
arm64
```

## Cluster (read-only, alias `wipp-campus`, connected on first try)

```
$ ssh -o BatchMode=yes -o ConnectTimeout=15 wipp-campus 'hostname; whoami; date; ls -d .../envs/atlas-pipeline && echo ENV_OK; ls /storage/agrp/berkom/atlas-utilization | head -30; qstat -u berkom 2>&1 | head -20'
wipp-an1
berkom
Wed Oct 14 11:21:23 IDT 2026
/storage/agrp/berkom/atlas-utilization/envs/atlas-pipeline
ENV_OK
checkouts
envs
logs
output
work
zsh:1: command not found: qstat
```

Note: `qstat` was not on the PATH of the non-interactive SSH shell (likely the PBS module/profile is not loaded for non-interactive logins). Not investigated further, per the read-only scope.

## Results

| Check | Result |
|---|---|
| Local Python env (`hep`, Python 3.11.17, core packages) | PASS |
| ROOT (6.40.04) | PASS |
| XRootD Python bindings | PASS |
| Cluster SSH (`wipp-campus` → wipp-an1 as berkom) | PASS |
| Cluster conda env present (`envs/atlas-pipeline`) | PASS |
| Cluster job query (`qstat`) | FAIL — command not found in non-interactive shell |
| Git push to fork | PASS — see commit message / `git ls-remote` check in the session report |
