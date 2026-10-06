# Trigger matching specification for DoubleEG, MuonEG and SingleElectron

Step 1 of the electron-dataset **preparation** task. This document specifies
acceptance; it does not implement it. Nothing in the production pipeline is
changed by this branch.

It mirrors `studies/cms_datasets/matching/TRIGGER_MATCHING_SPEC.md` (the muon
spec) in structure and in standard of evidence. Every claim is **VERIFIED BY
RUNNING** (read from a real UL2016 NanoAODv9 file, naming the script),
**VERIFIED FROM SOURCE** (the exact CMSSW release that produced these files,
quoted), or **UNVERIFIED** (stated as such, with the consequence).

---

## 0. The datasets, records and trigger paths

**VERIFIED BY RUNNING** — record IDs and trigger sets read from
`studies/cms_datasets/cluster/datasets_records.py`; file counts from the Open
Data portal file lists via `fetch_file_list` (`evidence/file_counts.json`):

| dataset | record G | record H | files G | files H | total | trigger path(s) required |
|---|---:|---:|---:|---:|---:|---|
| DoubleEG | 30521 | 30554 | 47 | 86 | **133** | `HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ` |
| MuonEG | 30528 | 30561 | 29 | 19 | **48** | `HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ` **OR** `HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ` |
| SingleElectron | 30529 | 30562 | 71 | 80 | **151** | `HLT_Ele27_WPTight_Gsf` |
| | | | | | **332** | |

These are the existing trigger sets from the code and the preflight, reused
unchanged. MuonEG uses the **DZ** paths because the non-DZ variants are
prescaled (preflight Step 1c); `HLT_Ele27_WPTight_Gsf` was tested unprescaled.
All required branches are present in the files checked
(`evidence/trigobj_titles_electron_datasets.json`).

One menu note, **VERIFIED BY RUNNING**: `HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL`
(the **non-DZ** variant) is absent from the MuonEG H file inspected, while its
DZ counterpart is present. Harmless here — the DZ paths are the ones required —
but a reader comparing menus should not be surprised.

## 1. `TrigObj_id` and `TrigObj_filterBits` — read from the actual files

**VERIFIED BY RUNNING** (`read_trigobj_titles.py`, branch `.title` strings read
live over XRootD from file 0 of **all eight** (dataset, era) combinations).
The `TrigObj_filterBits` title is **byte-identical across all eight files**
(one distinct sha256), so a single quote covers every dataset.

`TrigObj_id` title:

> ID of the object: **11 = Electron (PixelMatched e/gamma)**, 22 = Photon
> (PixelMatch-vetoed e/gamma), **13 = Muon**, 15 = Tau, 1 = Jet, 6 = FatJet,
> 2 = MET, 3 = HT, 4 = MHT

`TrigObj_filterBits` title, **Electron** portion, verbatim:

> extra bits of associated information: **1 = CaloIdL_TrackIdL_IsoVL,
> 2 = 1e (WPTight)**, 4 = 1e (WPLoose), 8 = OverlapFilter PFTau, **16 = 2e,
> 32 = 1e-1mu**, 64 = 1e-1tau, 128 = 3e, 256 = 2e-1mu, 512 = 1e-2mu,
> 1024 = 1e (32_L1DoubleEG_AND_L1SingleEGOr), 2048 = 1e (CaloIdVT_GsfTrkIdT),
> 4096 = 1e (PFJet), 8192 = 1e (Photon175_OR_Photon200)

`TrigObj_filterBits` title, **Muon** portion, verbatim:

> **1 = TrkIsoVVL, 2 = Iso**, 4 = OverlapFilter PFTau, 8 = IsoTkMu,
> 1024 = 1mu (Mu50)

## 2. Cross-check against CMSSW_10_6_26

**VERIFIED FROM SOURCE** (`read_cmssw_bit_definitions.py`, fetching
`PhysicsTools/NanoAOD/python/triggerObjects_cff.py` at tag `CMSSW_10_6_26`,
the NANO-step release the portal records for these datasets).

The 2016 HLT-menu override loop replaces the `qualityBits` formula for
**`Muon` and `Tau` only** — the measured list of overridden selections is
exactly `['Muon', 'Tau']`. **The Electron selection is not overridden**, so the
electron bits in these 2016 files are the default Run-2 formula. That is
consistent with what the files show: the Electron portion of the title carries
all 14 bits, while the Muon portion carries only the 5 override bits.

Each electron bit therefore traces to a filter-name pattern in the config
(all four confirmed present in the source):

| bit | title meaning | filter pattern that sets it | which path it belongs to |
|---:|---|---|---|
| 1 | `CaloIdL_TrackIdL_IsoVL` | `*CaloIdLTrackIdLIsoVL*TrackIso*Filter` | generic leg filter, shared by DoubleEG and MuonEG legs |
| 2 | `1e (WPTight)` | `hltEle*WPTight*TrackIsoFilter*` | **SingleElectron** (`Ele27_WPTight_Gsf`) |
| 16 | `2e` | `hltEle*Ele*CaloIdLTrackIdLIsoVL*Filter` | **DoubleEG** (dielectron filter) |
| 32 | `1e-1mu` | `hltMu*TrkIsoVVL*Ele*CaloIdLTrackIdLIsoVL*Filter*` | **MuonEG** (electron leg of the cross trigger) |

This is a **genuine bit-level separation per dataset**, and it is better than
what the 2016 muon bits allow. That asymmetry is the central finding of Step 1
and is spelled out in Section 6.

## 3. DoubleEG acceptance definition

1. `HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ` fired (event-level HLT branch,
   unchanged from `--population generic`'s own trigger set).
2. AND **two distinct** selected (offline) electrons, each with
   dR(offline electron, trigger object) < 0.1 to **some** `TrigObj` with
   `id == 11` and `filterBits & 16 != 0` (bit 16, `2e`).
3. AND the **higher-pT matched trigger object's own `TrigObj_pt` >= 23 GeV**.
   No further online-pT floor is imposed on the second matched object beyond
   what bit 16 plus the path firing already imply (~12 GeV).

**Can the bits distinguish the 23 GeV leg from the 12 GeV leg? NO — stated
explicitly.** Bit 16's filter pattern `hltEle*Ele*CaloIdLTrackIdLIsoVL*Filter`
is wildcarded on both legs and matches the dielectron filter of *both*
identically. There is no separate "this is the 23 GeV leg" bit.
**Approximation used: mirror the DoubleMuon solution exactly** — require two
distinct offline-electron-to-bit-16 matches and require the leading matched
online pT to clear 23 GeV. This carries the same known limitation the muon spec
states for its own 17 GeV leg: it does not certify a one-to-one correspondence
between the two matched online objects and the path's two legs.

Note that both path legs (23 and 12 GeV) sit **below** our offline electron cut
of 25 GeV, so no offline electron that passes our selection can be below either
leg's threshold. Step 3 measures whether any residual turn-on remains.

## 4. MuonEG acceptance definition

1. `HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL_DZ` **OR**
   `HLT_Mu8_TrkIsoVVL_Ele23_CaloIdL_TrackIdL_IsoVL_DZ` fired.
2. AND **>= 1** selected (offline) electron matched (dR < 0.1) to a `TrigObj`
   with `id == 11` and `filterBits & 32 != 0` (bit 32, `1e-1mu`).
3. AND — **PROPOSED, and the place where NanoAOD is insufficient** — the muon
   leg is accepted **on the path decision alone**, with no trigger-object
   matching requirement on the muon.

**Why no muon matching for MuonEG.** The brief asks for "one matched muon AND
one matched electron". The electron half works very well. The muon half cannot
be done with these files:

* **VERIFIED FROM SOURCE**: the *default* muon formula contains a cross-trigger
  bit, `32*filter('hltMu*TrkIsoVVL*Ele*CaloIdLTrackIdLIsoVL*Filter*')` =
  `1mu-1e`. The **2016 override replaces the whole formula and does not include
  it.** So no muon bit identifies the MuonEG muon leg in these files.
* The only candidate left is bit 1 (`TrkIsoVVL`), whose 2016 pattern
  `*RelTrkIso*Filtered0p4` is wildcarded and is the **DoubleMuon dimuon** leg
  filter.
* **VERIFIED BY RUNNING** (`measure_per_file.py` bit census, MuonEG triggered
  events): of selected muons in MuonEG-fired events, only **7.7%** carry bit 1;
  **72.2%** carry bit 8 (`IsoTkMu`, a *single-muon* filter); and **16.1%** have
  no matched trigger muon of any kind. Requiring bit 1 would therefore throw
  away roughly 92% of genuine MuonEG events. The matching-efficiency number in
  Step 3 (37.7% over the sampled files) is incidental overlap with other muon
  paths, not a leg match.

**Options considered, and the one proposed:**

| option | consequence |
|---|---|
| require bit 1 on a muon | **rejected**: loses ~92% of events; the bit does not tag this leg |
| require a match to **any** trigger muon (any bit) | loses ~16% of events for no stated physics reason |
| **require only the matched electron (bit 32) + the DZ path decision** | **PROPOSED**. Keeps the leg that *is* identifiable, and is honest about the one that is not |

4. **Leg-threshold handling when bits cannot distinguish the two paths.** The
   two DZ paths have swapped thresholds (Mu23+Ele12 and Mu8+Ele23) and bit 32
   is identical for both. **PROPOSED rule**: accept if **at least one** of the
   two paths fired *and* the matched-electron online pT clears **that** path's
   own electron-leg threshold — i.e. accept when
   (`Mu23_Ele12_DZ` fired AND matched-electron online pT >= 12) OR
   (`Mu8_Ele23_DZ` fired AND matched-electron online pT >= 23).
   Since our offline electron cut is already 25 GeV, both conditions are
   expected to be satisfied almost always; the rule exists so the acceptance is
   stated exactly rather than left implicit. **UNVERIFIED** how often the
   stricter branch bites — Step 3's matched-online-pT histogram is the input,
   and it is reported there.

## 5. SingleElectron acceptance definition

1. `HLT_Ele27_WPTight_Gsf` fired.
2. AND **>= 1** selected (offline) electron matched (dR < 0.1) to a `TrigObj`
   with `id == 11` and `filterBits & 2 != 0` (bit 2, `1e (WPTight)`).
3. AND the matched electron's **pT >= T_SE GeV**, where **T_SE is a
   PLACEHOLDER** to be fixed by the group after Step 2.

Bit 2's pattern `hltEle*WPTight*TrackIsoFilter*` is wildcarded on the
threshold, so it would equally tag `HLT_Ele32_eta2p1_WPTight_Gsf`'s own object
(a different path, present in the files but not in this study's trigger set).
The event-level `HLT_Ele27_WPTight_Gsf` check plus the pT requirement in (3)
are the safeguard — the same structure, and the same residual caveat, as the
muon spec's `IsoMu24` vs `IsoMu27` discussion.

Whether the pT requirement in (3) is applied to the **offline** pT or the
**online** (`TrigObj_pt`) pT is itself a choice. **PROPOSED: offline pT**, so
that the requirement is a statement about the physics object the histograms are
built from, consistent with how the delivered final states are defined. Step 2
measures efficiency against offline pT accordingly.

## 6. Matching criterion: dR < 0.1

Adopted unchanged from the settled muon side. The muon spec's note that the
generic `nanoAOD-tools` default is 0.4 (a catch-all shared with jets, not a
lepton recommendation) applies here too; electrons, like muons, are
well-measured and a tighter cone is standard.

## 7. Priority order and the closure test

**Priority (DEFAULT, documented as a choice, not a derivation):**

> DoubleMuon > SingleMuon > **DoubleEG > MuonEG > SingleElectron**

The three electron datasets sit **below** SingleMuon, so **no delivered muon
file changes**.

Note, as instructed: the existing generic `VETO_ORDER` in
`datasets_records.py` is **different** — DoubleMuon > DoubleEG > MuonEG >
SingleMuon > SingleElectron. The **union of accepted events does not depend on
the order**; only the dataset *label* an event is attributed to does. The one
exception is the known ~4-per-million copy differences between independently
produced datasets. Keeping the electron datasets below SingleMuon is therefore
a bookkeeping choice that protects the existing delivery, not a physics change.

### 5-dataset closure test design

**Goal**: every collision accepted by at least one of the five datasets is
counted exactly once.

**Run to use.** The brief suggests run 280016. **VERIFIED BY RUNNING**
(`find_common_run.py`, 6 files sampled per record, `evidence/common_run_check.json`):
280016 was seen in DoubleMuon, SingleMuon, DoubleEG and SingleElectron but
**was not observed in the sampled MuonEG files**. Because only 6 files per
record were scanned, this is a lower bound — 280016 is **not proven absent**
from MuonEG, merely not observed. 37 runs were common to all five in the
sample; **run 281707 is recommended**, being present in all five.

**Procedure** (to be implemented later, not now):

1. Fix one run (281707). For each of the five datasets, read every file and
   keep events of that run passing the golden JSON.
2. For each event, form the key `(run, luminosityBlock, event)`.
3. For each dataset, evaluate its own acceptance from Sections 3-5 (and the
   muon spec for the two muon datasets): path fired **and** the matching
   requirement satisfied.
4. **Union**: the set of keys accepted by at least one dataset.
5. **Attribution**: assign each key to the highest-priority dataset that
   accepts it, per the order above.
6. **Checks**:
   a. every key in the union is attributed to exactly one dataset
      (count of attributed == size of union, no key attributed twice);
   b. summing the per-dataset attributed counts reproduces the union size;
   c. for every ordered pair, the count of keys accepted by both is reported,
      so the overlap structure is visible rather than assumed;
   d. the attribution is re-run under the **generic** `VETO_ORDER` and the
      union size must be **identical** (only the per-dataset labels change) —
      this is the direct test of the claim in the paragraph above;
   e. any key present in a dataset's *file* but accepted by none is counted
      and reported, so "lost" events are visible.
7. **Expected residual**: the ~4-per-million copy differences between
   independently produced datasets. Report the observed number rather than
   asserting it.

## 8. What cannot be established, and the consequence

1. **The MuonEG muon leg cannot be trigger-matched** from these files
   (Section 4). No 2016 muon bit tags it; bit 1 tags only 7.7% of the muons in
   MuonEG events. **Consequence**: the proposed MuonEG acceptance matches the
   electron only and takes the muon leg from the path decision. This is a
   weaker requirement than the muon-side datasets enjoy, and it is the single
   largest honest gap in this specification.
2. **Per-leg identity within DoubleEG** (Section 3): not resolvable from
   `filterBits`; the leading-matched-online-pT >= 23 approximation is used,
   exactly as the muon spec does for its 17 GeV leg.
3. **Which of the two MuonEG paths fired an event is known, but which offline
   object filled which leg is not.** The Section 4(4) rule handles this by
   requiring consistency with at least one fired path, not by assigning legs.
4. **Bit 2 does not distinguish `Ele27_WPTight_Gsf` from
   `Ele32_eta2p1_WPTight_Gsf`** (Section 5); the event-level path check plus the
   pT requirement are the safeguard.
5. **The Step 2 turn-on measured with the brief's own probe definition is a
   convolution of trigger efficiency and prompt purity** — see
   `DECISIONS_FOR_GROUP.md` and the Step 2 results. A prompt-enriched probe
   variant is reported alongside so the two can be separated; neither changes
   the delivered electron definition.

**No STOP condition was reached.** DoubleEG and SingleElectron have clean,
bit-level acceptance definitions. MuonEG has a clean electron leg and a stated,
measured insufficiency on the muon leg, with a proposed fallback. All three are
ready for the group's decision.
