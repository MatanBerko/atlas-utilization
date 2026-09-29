# Trigger matching specification for DoubleMuon and SingleMuon

Step 1 of the trigger-matching task. Every claim below is either **VERIFIED
BY RUNNING** (read directly from a real UL2016 NanoAODv9 file) or
**VERIFIED FROM SOURCE** (the exact CMSSW release that produced these
files, quoted verbatim, fetched from GitHub) or **UNVERIFIED** (stated as
such, with the consequence).

---

## 0. Which CMSSW release actually produced these files

**VERIFIED BY RUNNING** (CERN Open Data portal API,
`https://opendata.cern.ch/api/records/30522`, `metadata.methodology.description`):

> Step NANO: Release: **CMSSW_10_6_26**, Global tag: 106X_dataRun2_v35
> (Configuration: ReReco-Run2016G-DoubleMuon-UL2016_MiniAODv2_NanoAODv9)

This is the exact release whose `PhysicsTools/NanoAOD/python/triggerObjects_cff.py`
defines the `TrigObj_filterBits` bit meanings for these specific files —
not a guessed or nearby tag. The same portal query, run for record 30530
(SingleMuon), returns the identical NANO-step release/tag (both G-era
records were reprocessed together as part of the same UL2016 campaign).

## 1. TrigObj_id and TrigObj_filterBits — read directly from the actual files

**VERIFIED BY RUNNING** (`uproot`, branch `.title` strings, read live over
XRootD from the exact files this study's own pilot uses):

- DoubleMuon, record 30522, file 0:
  `root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v2/2430000/05DD095C-F6C3-9A4F-9FB3-348A5A6403D5.root`
- SingleMuon, record 30530, file 0:
  `root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/130000/0A4230E2-0C75-604D-890F-A4CE5E5C164E.root`

Both files' `TrigObj_id` title (byte-identical between the two datasets,
as expected — same central production):

> ID of the object: 11 = Electron (PixelMatched e/gamma), 22 = Photon
> (PixelMatch-vetoed e/gamma), **13 = Muon**, 15 = Tau, 1 = Jet, 6 =
> FatJet, 2 = MET, 3 = HT, 4 = MHT

Both files' `TrigObj_filterBits` title, muon portion (byte-identical
between the two datasets):

> ... **1 = TrkIsoVVL, 2 = Iso, 4 = OverlapFilter PFTau, 8 = IsoTkMu,
> 1024 = 1mu (Mu50) for Muon** ...

(Electron/Tau/Jet/HT/MHT portions of the same string are quoted in full
in the evidence JSON, `evidence/trigobj_branch_titles.json`, but are not
relevant to this task's scope — muons only.)

## 2. Cross-check against the CMSSW source (CMSSW_10_6_26)

**VERIFIED FROM SOURCE** — `PhysicsTools/NanoAOD/python/triggerObjects_cff.py`
at tag `CMSSW_10_6_26`
(`https://raw.githubusercontent.com/cms-sw/cmssw/CMSSW_10_6_26/PhysicsTools/NanoAOD/python/triggerObjects_cff.py`).

The file defines a **default (Run 2, latest-era) Muon `qualityBits`**
formula, then a separate **2016-era override** (`if sel.name=='Muon':`
block) that *replaces* the whole formula for 2016 reprocessing. The
override, quoted verbatim:

```python
sel.qualityBits = cms.string(
    "filter('*RelTrkIso*Filtered0p4') + "
    "2*filter('hltL3cr*IsoFiltered0p09') + "
    "4*filter('*OverlapFilter*IsoMu*PFTau*') + "
    "8*filter('hltL3f*IsoFiltered0p09') + "
    "1024*max(filter('hltL3fL1sMu*L3Filtered50*'),"
    "filter('hltL3fL1sMu*TkFiltered50*'))"
)
```

with documentation string:

> "1 = TrkIsoVVL, 2 = Iso, 4 = OverlapFilter PFTau, 8 = IsoTkMu, 1024 =
> 1mu (Mu50)"

This **matches the two real files' own branch titles exactly** (Section
1) — confirming these files were built with the 2016-era override, not
the newer Run-2-latest formula (which additionally defines bits 16/32/
64/128/256/512/2048 that do **not** appear in these files' own titles —
consistent, not a discrepancy: the newer formula is simply not the one
used here).

**The key structural fact, from the filter-name patterns themselves**:

| Bit | Value | Filter name pattern | Meaning |
|---|---|---|---|
| bit 1 | TrkIsoVVL | `*RelTrkIso*Filtered0p4` | generic dimuon "TrkIsoVVL" leg filter (wildcarded on both sides) |
| bit 2 | Iso | `hltL3cr*IsoFiltered0p09` | L3 filter name contains **"cr"** = **c**ombined-**r**eco (Global-muon-seeded) isolated single-muon path |
| bit 8 | IsoTkMu | `hltL3f*IsoFiltered0p09` | L3 filter name has **no "cr"** = **tracker-only-seeded** ("Tk") isolated single-muon path |

The "cr" vs. no-"cr" distinction in the filter-name pattern is exactly
CMS's own standard naming convention for Global-muon-seeded ("combined
reconstruction") vs. Tracker-only-seeded HLT muon paths — i.e. **IsoMu24**
(Global) vs. **IsoTkMu24** (Tracker). This is not an assumption: it is
the literal filter-name substring the CMSSW config itself keys on to set
each bit.

## 3. DoubleMuon acceptance definition

1. `HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ` OR
   `HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ` fired (event-level HLT branch
   — unchanged from `--population generic`'s own trigger set).
2. AND **two distinct** selected (offline) muons, each with
   dR(offline muon, trigger object) < 0.1 to **some** `TrigObj` with
   `id == 13` and `filterBits & 1 != 0` (bit 1, "TrkIsoVVL").
3. Among the matched pairs, the **higher-pT matched trigger object's own
   `TrigObj_pt` must be ≥ 17 GeV** (the approximation for the 17 GeV leg
   — see below); no further pT floor is imposed on the second matched
   object beyond what bit 1 + the trigger firing already imply (≈8 GeV).

**Can the bits distinguish the 17 GeV leg from the 8 GeV leg? NO —
stated explicitly, not assumed.** Bit 1's own filter-name pattern
(`*RelTrkIso*Filtered0p4`) is wildcarded on *both* sides and matches the
TrkIsoVVL filter of *every* dimuon leg in *both* DZ paths (17 GeV leg, 8
GeV leg, and the TkMu8 variant) identically — there is no separate bit
for "this is the 17 GeV leg" vs. "this is the 8 GeV leg". **Approximation
used**: require at least two distinct offline-muon-to-bit-1-object
matches, and require the *leading* (highest-pT) matched trigger object's
own online pT to clear 17 GeV — following this task's own suggested
fallback exactly. This does not certify that the specific two matched
online objects correspond one-to-one to the path's own two legs (a
lower-pT online object above 8 GeV could in principle be a duplicate/
second reconstruction of the same physical leg rather than the "other"
leg) — this is a known, stated limitation of the approximation, not
resolved further here.

## 4. SingleMuon acceptance definition

1. `HLT_IsoMu24` fired (**only** this path, per Maryna's explicit
   instruction — `HLT_IsoTkMu24` is deliberately excluded from the
   trigger requirement itself, though the bit-level distinction below
   still matters for matching purity).
2. AND **≥1** selected (offline) muon with dR(offline muon, trigger
   object) < 0.1 to **some** `TrigObj` with `id == 13`,
   `filterBits & 2 != 0` (bit 2, "Iso" = Global/combined-reco path), AND
   `TrigObj_pt >= 24` GeV.

**Can the bits distinguish IsoMu24's objects from IsoTkMu24's? YES, at
the object level** (Section 2): bit 2 ("cr", Global-seeded) and bit 8
("IsoTkMu", Tracker-seeded) are structurally different filters, and this
delivery's matching requires bit 2 specifically, excluding bit-8-only
objects. **This is a genuine bit-level distinction, not merely a pT-based
approximation** — stated with the confidence the cross-checked CMSSW
source supports. One residual caveat, stated plainly: bit 2's own filter
pattern (`hltL3cr*IsoFiltered0p09`) is *also* wildcarded on pT, so it
would equally match `HLT_IsoMu27`'s own Global-seeded L3 filter object
(a **different** path, not requested here, also not vetoed at the
trigger level since `HLT_IsoMu27` is not part of this study's trigger
set at all). The **online pT ≥ 24 GeV** requirement is the safeguard
against mis-attributing a bit-2 object to the wrong path threshold —
combined with the event already having fired `HLT_IsoMu24` specifically
(checked first, independently, at the event level), this is a reasonable
and explicitly-stated approximation, not a perfect one.

## 5. Matching criterion: dR < 0.1

**As specified in this task's own instruction — adopted.** One relevant
cross-check, reported honestly: the community-standard `nanoAOD-tools`
framework's own generic `matchObjectCollection`/`matchObjectCollectionMultiple`
utility functions (`cms-nanoAOD/nanoAOD-tools`,
`python/postprocessing/tools.py`) default to **`dRmax = 0.4`**, not 0.1.
This is **not muon-specific** — it is a single catch-all default shared
across every object type that utility serves (jets, taus, muons, etc.),
and 0.4 is the conventional CMS jet cone size, not a muon-matching
recommendation. Given muons are point-like, well-isolated, and precisely
reconstructed, a tighter cone is standard practice for muon-specific
trigger matching, and this task's own specified 0.1 is adopted as the
working criterion. **This is a genuine "docs indicate a different
standard" finding for the generic tool, reported as instructed, but not
treated as overriding the task's own explicit 0.1 instruction for this
muon-specific use case.**

## 6. What cannot be established, and the consequence

1. **Exact per-leg identity for the dimuon trigger** (Section 3): not
   resolvable from `TrigObj_filterBits` alone for these 2016-era files.
   Consequence: DoubleMuon's matched acceptance uses the stated online-pT
   approximation (leading matched object ≥ 17 GeV) rather than a
   bit-certified per-leg match. This could, in principle, accept a
   vanishingly small number of events where the "17 GeV-leg" role is
   filled by a duplicate reconstruction of the muon that actually fired
   the 8 GeV leg — not measured further here (out of this task's scope).
2. **IsoMu24 vs. IsoMu27 discrimination purely from bits** (Section 4):
   bit 2 alone does not distinguish them (both are Global-seeded); the
   online-pT ≥ 24 GeV floor plus the event-level `HLT_IsoMu24` check
   together are the safeguard. Since `HLT_IsoMu27` is never part of this
   study's own trigger requirement, this is a minor residual caveat
   rather than a practical risk for this task specifically.
3. **Whether every DZ-vs-non-DZ dimuon path variant shares bit 1
   identically**: `HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ` and
   `HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ` both use TrkIsoVVL-named
   filters matching the same wildcard pattern, per Section 2 — treated as
   equivalent for matching purposes, consistent with the OR already used
   for the trigger requirement itself in `--population generic`.

**No STOP condition was reached**: both the DoubleMuon and SingleMuon
trigger objects were identified with reasonable confidence, cross-checked
against the exact CMSSW release that produced these specific files, with
explicit, stated approximations where the bits are not fully
discriminating. Proceeding to Step 2 (implementation).
