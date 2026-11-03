# ZZTo2L2Nu cross-section check — RESULT (3 Nov 2026)

**Verdict (Matan's rule: R2 within 0.85–1.15 → confirmed): R2 = 0.967 → CONFIRMED. The low-m(ℓℓ) explanation
holds and the D14 value 1.135 pb stands.** Calibration on our delivered ZZTo4L: R4 = 0.985.

Check only: no production, no registry or config change, no cross section applied, no other card changed.
All numbers VERIFIED BY RUNNING (PBS job 5433201, then `zz2l2nu_check_numbers.json`), unless marked otherwise.

## Numbers

| | ZZTo2L2Nu (75567) | ZZTo4L (75589, calibration) |
|---|---:|---:|
| files read (portal file index) | 0, 1, 2 | 0, 1 |
| events used / read | 2,299,000 / 2,299,000 | 252,000 / 252,000 |
| f_on = Σw(both pairs in 60–120 GeV) / Σw | **0.5818** | **0.1100** |
| portal (generator) σ | 0.9738 pb | 1.325 pb |
| σ_on = portal σ × f_on | **0.5665 pb** | **0.1458 pb** |
| on-shell NLO expectation | 14.51 × 2 × 0.10099 × 0.2000 = **0.5861 pb** | 14.51 × 0.10099² = **0.1480 pb** |
| **ratio** | **R2 = 0.967** | **R4 = 0.985** |
| R with window 66–116 GeV (information only) | 0.954 | 0.966 |
| R with window 81–101 GeV (information only) | 0.858 | 0.859 |

Where the rest of the ZZTo2L2Nu cross section sits (Σw fractions):
- m(ℓℓ) < 60 GeV: **0.393**, of which m(ℓℓ) < 12 GeV: 0.283. This is the virtual-photon peak just above the generator cut of 4 GeV (left plot).
- m(ℓℓ) > 120 GeV: 0.013.
- m(νν) outside 60–120 GeV: **0.020**. As expected, it is almost 0: νν comes only from a Z, so this is just the Z line-shape tails.

ZZTo4L: Z1 < 60 GeV 0.424, Z2 < 60 GeV 0.882 (both pairs can be γ*, hence only 11 % "both on-shell").

So the 42 % excess of the portal value over the on-shell NNLO total is the low-mass γ* → ℓℓ part. The on-shell part
alone (0.567 pb) matches the on-shell NLO prediction (0.586 pb) to 3 %. The proposed normalisation keeps the D9
convention: 0.9738 × 16.91 / 14.51 = **1.135 pb (unchanged, PROPOSED as in XSEC_PROPOSALS_v2.md card 13)**.

Plots: `plots/lhe_masses_ZZTo2L2Nu.png` (m(ℓℓ), m(νν)), `plots/lhe_masses_ZZTo4L.png` (Z1, Z2). Both are LHE level, 0–200 GeV,
log scale, normalised to Σw. Bins with no events are drawn at the 10⁻⁹ floor.

## Method

- Script `lhe_mass_check.py` (run mode in PBS, plot mode locally).
  - It uses the NanoAOD LHE particles `LHEPart_{pt,eta,phi,mass,pdgId,status}`, keeps outgoing ones (status +1), and `genWeight`.
  - Charged leptons are |pdgId| 11, 13, 15; neutrinos are 12, 14, 16.
- Required topology:
  - ZZTo2L2Nu: exactly 2 charged leptons + 2 neutrinos.
  - ZZTo4L: exactly 4 charged leptons.
  - **No event failed it** (0 of 2,299,000 and 0 of 252,000).
- ZZTo4L pairing rule:
  - Z1 = the same-flavour opposite-sign pair with mass closest to 91.1876 GeV; Z2 = the other two leptons.
  - Z2 was SFOS in every event.
- Fractions are genWeight-weighted. The negative-weight share is 0.1 % for ZZTo2L2Nu, so it does not matter.
- File URLs: the CERN Open Data portal file index (`fetch_file_list`), the same call the production input sweep and the
  26 and 31 Oct probes use. The exact URLs are in `evidence/lhe_mass_check.json`.
- Expectation: arXiv:1405.2219 Table 1, NLO 14.51 pb (the POWHEG samples are NLO qq̄ → ZZ). Z branching ratios: PDG
  S044 (D6). These values were read on 26 and 31 Oct (`XSEC_PROPOSALS_v2.md`) and were not re-read today.

## Caveats (noted; the rule above is applied as decided)

- **Window.** "On-shell" is defined here as 60–120 GeV. The NLO total is for on-shell ZZ (labelled 'inclusive ZZ' in its Table 1, no γ* part; whether it uses zero width is not re-checked here, UNVERIFIED).
  - A narrower window cuts into the Breit-Wigner tails: 81–101 GeV gives R2 = 0.86, still inside 0.85–1.15.
  - R4 moves the same way (0.86), which shows this is a window effect, not a ZZTo2L2Nu problem.
  - With 60–120 GeV, both ratios are within 3.5 % of 1.
- **Statistics.** 3 of 15 files (2.3 M of 15.9 M events) for ZZTo2L2Nu and 2 of 99 files (0.25 M of 52.1 M) for ZZTo4L. This assumes the files are
  representative; the statistical error on f_on is far below 1 %.
- **Same-flavour interference in 4ℓ.** For eeee and μμμμ the "Z1 closest to mZ" pairing is a choice, and the generator
  includes the interference between pairings. This only affects the calibration, which agrees anyway.
- **τ leptons.** τ appear undecayed in the LHE record (|pdgId| 15), so they are counted as charged leptons; the expectation
  uses BR(Z → ℓℓ) with ℓ = e, μ, τ.
  - The 31 Oct question of whether POWHEG's `leptons-nu` includes τ is answered **indirectly**: R2 ≈ 1 with ℓ = e, μ, τ.
    Without τ the expectation would be 2/3 as large and R2 ≈ 1.45.
  - The τ share was not counted directly (UNVERIFIED).
- **ZZ → ℓℓνν with the same lepton and neutrino flavour** could in principle also get W+W− diagrams. The POWHEG ZZ code omits them
  (arXiv:1311.1365 §1), and m(νν) is a clean Z peak (only 2 % outside 60–120 GeV), consistent with that.
- The comparison is at LHE level. Parton shower and final-state radiation do not change the cross section.

## Run record

- Script committed and pushed before submission: `6eb2a34`. Pinned checkout
  `/storage/agrp/berkom/atlas-utilization/checkouts/zzcheck_20261103/repo_6eb2a34544418dd18e63543b0786ab9514425b23`
  (HEAD asserted; log prints `commit=6eb2a34…`). Work dir `work/zzcheck_20261103/{logs,out}`.
- PBS job **5433201**: queue N, io=25, mem 4 GB, walltime 2 h, `-m n`. Exit status 0, wall time 1:15, max memory 1.4 GB.
- Logs: `evidence/zzcheck.{out,err}`. Raw output: `evidence/lhe_mass_check.json`. Numbers: `zz2l2nu_check_numbers.json`.
- `ssh wipp-campus`: "No route to host" (one try), so `wipp-home` was used.
- File count (`lfs quota -u berkom /storage`):
  - before: **93,638**. The quota line was mis-parsed at submission, so this is reconstructed: 95,319 right after submission
    minus the 1,681 files of the two new directories. It equals the 31 Oct measurement.
  - after the job: **95,324**.
  - Under 125,000.
