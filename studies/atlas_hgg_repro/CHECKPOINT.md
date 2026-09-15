# Checkpoint — paused mid-task, 2026-09-15

This task (reproducing the ATLAS H→γγ likelihood-ratio significance from
BumpNet Figure 15, Part A, plus a corrected floating-width excess test,
Part B) was paused partway through because the laptop needed to shut down.
**Nothing here is finished.** This file exists so the next session can pick
up exactly where this one stopped, without re-deriving anything or
re-guessing what's safe to redo.

## What's actually finished (committed on this branch)

- Git setup verified: `origin/study/lr-toy-study` was at
  `08769374a47c4d6c528ac1a5f913ef76ea107835`, `origin/master` at
  `8cf737e1acf0fa736b78864e631dc6cc98e05772`, both as expected. Branch
  `study/atlas-hgg-lr-reproduction` created from the sync branch.
- **Part A1 (getting the real ATLAS data points) — DONE, committed.**
  HEPData has no record for this paper (checked two ways: by INSPIRE ID
  1124337, and by exact title search — zero hits both times). The 30
  unweighted diphoton-mass points (100–160 GeV, 2 GeV bins) were extracted
  by parsing the vector PostScript drawing commands in the actual EPS
  figure file from the paper's own arXiv e-print (NOT by reading pixels).
  Confirmed the correct (unweighted) sub-panel was used, not the
  ln(1+S/B)-weighted one, by cross-checking against the rendered PDF's own
  legend ("Data" circles vs "Data S/B Weighted" triangles). Validated two
  ways: extracted counts land within 0.48 events of a whole number before
  rounding (strong internal evidence of correctness), and a visual overlay
  (frame-to-frame coordinate mapping, independent of the extraction's own
  calibration) shows every point exactly on its real data marker.
  - `studies/atlas_hgg_repro/extract_atlas_fig4.py` — the extraction script
  - `studies/atlas_hgg_repro/make_extraction_overlay.py` — the overlay/check script
  - `studies/atlas_hgg_repro/results/atlas_hgg_fig4_points.csv` — the 30 data points
  - `studies/atlas_hgg_repro/results/atlas_hgg_fig4_extraction_overlay.png` — the visual check
- **`lr_core.py` extended — DONE, committed (mostly) + one small uncommitted addition.**
  Added a plain-polynomial background model (`polynomial_shape_density`,
  `polynomial_bin_expectation`) and matching fit functions
  (`fit_bkg_only_poly`, `fit_full_poly`, `fit_full_poly_floating_mass_width`,
  and `fit_full_poly_floating_width` — the last one is added but NOT YET
  COMMITTED, see below). All additions only — verified with
  `git diff studies/lr_toys/lr_core.py` showing zero removed/changed lines
  each time. `studies/lr_toys/test_lr_core.py` re-run and still passes
  (3 passed) after every addition.

## What's partially done (NOT committed — will be committed by this pause, see below)

- **Part A2 (fitting the real spectrum) — script written, only PARTLY run.**
  `studies/atlas_hgg_repro/fit_atlas_hgg.py` does, in order:
  1. Fit 1 (background-only, 4th-order polynomial) — **ran successfully.**
  2. Fit 2 (S+B, mass and width floating) — **ran successfully.**
  3. Saves the Figure-15-style fit plot — **done**,
     `studies/atlas_hgg_repro/results/A2_fit_result.png` exists.
  4. Profiled local significance at the best-fit mass, width floating vs.
     fixed — **status unknown, likely did not reach this** (see below).
  5. A 41-point mass scan (110–150 GeV, 1 GeV steps) on the real data for
     the observed max local Z — **status unknown.**
  6. **3,000 background-only toys, each re-doing that same 41-point scan,
     to get a toy-based + Gross–Vitells global significance — this is
     what was running when the process was killed.** It had been running
     for **16 minutes** with no sign of finishing (my estimate beforehand
     was ~8–10 minutes), and produced none of its intended output
     (`results/atlas_hgg_fit_results.json` and
     `results/_a2_local_z_curve.npz` do NOT exist). Stopped cleanly via
     `taskkill` (Windows PID, not a force-kill of anything git-related —
     just the stuck Python process), per instruction to stop cleanly if it
     wouldn't finish within 2 minutes.

  **Open problem to resolve before re-running:** this step is either much
  slower than my estimate, or got stuck on one particular toy (e.g. an
  ill-conditioned fit causing Minuit's strategy=1 to do many extra Hessian
  evaluations). Before just re-running it as-is: (a) add print-flushing /
  progress logging inside the toy loop (there was none — that's why I
  couldn't see how far it had gotten from the log file), (b) consider
  reducing `N_TOYS_GLOBAL` (currently 3000) or the mass-scan density
  (currently 1 GeV steps, 41 points) if a quick timed sub-run (e.g. 50
  toys) shows the per-toy cost is much higher than the ~170ms/toy I'd
  estimated from the earlier toy study's similar scan. Do NOT just
  re-launch the full 3000-toy run blind a second time.

## Not started at all

- **Part A3** (the four Z_LR variants V1–V4, digitizing BumpNet Figure
  15's own significance curve from its arXiv source — same vector-EPS
  approach as A1 should work, `refs/bumpnet_src/` was `mkdir`'d but never
  extracted or inspected — and the comparison/PASS-FAIL against the paper's
  curve).
- **Part B** (redoing the floating-width test with a background mismatch
  that produces a fake EXCESS instead of the earlier fake deficit).
- `studies/atlas_hgg_repro/REPORT.md` — not created yet.
- Any plots for A3 or Part B.
- Pushing this branch (this pause is the first push).

## Exact commands to resume

The scratch clone, venv, and downloaded reference papers are all outside
the repo, in `C:\Users\matan\hgg-repro-20260915-1656\` on this machine:

```
repo:  C:\Users\matan\hgg-repro-20260915-1656\repo      (branch: study/atlas-hgg-lr-reproduction)
venv:  C:\Users\matan\hgg-repro-20260915-1656\venv       (python.exe has numpy/scipy/matplotlib/iminuit/pymupdf/requests/pillow/pytest)
refs:  C:\Users\matan\hgg-repro-20260915-1656\refs       (downloaded PDFs/e-prints, NOT committed, still on disk)
```

If that scratch directory still exists on this machine, everything below
can run immediately with no re-downloading. If it's gone, re-create it:

```bash
mkdir -p ~/hgg-repro-resume/refs
cd ~/hgg-repro-resume
curl -sL -o refs/atlas_1207.7214.pdf https://arxiv.org/pdf/1207.7214
curl -sL -o refs/bumpnet_2501.05603.pdf https://arxiv.org/pdf/2501.05603
curl -sL -o refs/atlas_1207.7214_src.tar.gz https://arxiv.org/e-print/1207.7214
curl -sL -o refs/bumpnet_2501.05603_src.tar.gz https://arxiv.org/e-print/2501.05603
mkdir -p refs/atlas_src refs/bumpnet_src
tar -xzf refs/atlas_1207.7214_src.tar.gz -C refs/atlas_src
tar -xzf refs/bumpnet_2501.05603_src.tar.gz -C refs/bumpnet_src
git clone https://github.com/MatanBerko/atlas-utilization.git repo
cd repo && git checkout study/atlas-hgg-lr-reproduction
git remote add upstream https://github.com/Zhavi221/atlas-utilization.git
git remote set-url --push upstream DISABLED_NEVER_PUSH
python -m venv ../venv
../venv/Scripts/python.exe -m pip install numpy scipy matplotlib iminuit pymupdf requests pillow pytest
```

To resume exactly where this session stopped:

```bash
cd C:\Users\matan\hgg-repro-20260915-1656\repo\studies\atlas_hgg_repro
# First: time a SMALL toy run before trusting the full one again --
# temporarily set N_TOYS_GLOBAL and MASS_SCAN to something tiny (e.g. 20
# toys, 5 mass points) directly in fit_atlas_hgg.py, run it, measure
# ms/toy, THEN decide the real count. Do not just re-run 3000 blind.
C:\Users\matan\hgg-repro-20260915-1656\venv\Scripts\python.exe fit_atlas_hgg.py
```

Then continue with Part A3 (BumpNet Figure 15 extraction — same approach as
`extract_atlas_fig4.py`, but on `refs/bumpnet_src/` instead), Part B, the
plots, and `REPORT.md`, per the original task instructions.

## Safety confirmations for this pause

- Nothing was pushed to, merged into, or opened on the upstream
  (Zhavi221) repo.
- Nothing was pushed to or merged into `master` or `study/lr-toy-study`.
- No force-push, no branch deletion, no history rewrite.
- The only action taken to stop the stuck process was killing a local
  Python process by its Windows PID — no git state was touched by that.
