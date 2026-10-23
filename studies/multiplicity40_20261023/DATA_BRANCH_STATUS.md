# Status on the data branch (23 Oct 2026)

This branch (`feature/cms-data-multiplicity40-20261023`, code at `baf3ff4`) holds the shared #40 module
and the data builder option. The task is COMPLETE. The cluster proof, `REPORT.md` and the final
`HANDOFF.md` are on `feature/cms-mc-multiplicity40-20261023` (which contains this branch), at `de012d2`.

Result for the data builder (VERIFIED BY RUNNING, jobs 5311263/5311264/5311265, run from a clone of `baf3ff4`):
- `--multiplicity-rule exact` == the 23 Oct sync42 proof's data delivery, 548/548 histograms, bit for bit;
- the default (upstream40) passes R1–R7 on the five-file smoke test (548 → 201 histograms).

`HANDOFF.md` on this branch stops at step 1 on purpose; the up-to-date one is on the MC branch.
