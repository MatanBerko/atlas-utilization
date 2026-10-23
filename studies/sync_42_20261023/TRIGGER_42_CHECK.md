# CMS trigger matching compared with upstream #42 (read-only, 23 Oct 2026)

**Nothing was changed.** Everything below comes from reading the code.

- Line numbers refer to `studies/cms_datasets/cluster/run_dataset_on_file.py` (`D:` = data
  branch `sync/data-upstream-42-20261023` @ `c0e734b`, `M:` = MC branch
  `sync/mc-upstream-42-20261023` @ `dc760da`) and to `studies/m0m1j0_cms/selection.py` (the
  same on both branches).
- The matching and acceptance functions are **byte-identical** on the two branches (checked
  with an AST comparison): `trigobj_best_match`, `matched_acceptance_mask`, `fired_mask`, the
  five `*_acceptance` functions, `evaluate_four/five_acceptances`,
  `remove_electrons_overlapping_muons`, `exclusive_mask_from_acceptances` and the labelling
  functions.

## Short answer

- CMS already does what #42 asks of ATLAS MC: the leptons it matches to trigger objects are
  the **selected** ones (after pT/η, ID, isolation and the electron–muon overlap removal). The
  event-level decision is taken **before** the ≤ 4 non-jet rule and before the final-state
  labels, and **MC uses exactly the same functions as data**.
- The differences from ATLAS after #42 are listed at the end. The main ones:
  - CMS uses dataset-specific dilepton and single-lepton triggers, with per-leg matching
    rules, where ATLAS uses one single-lepton requirement;
  - CMS matches by ΔR to trigger objects, ATLAS by trigger-match links;
  - CMS applies the selected-lepton matching to collision data too, whereas ATLAS data keeps an
    event-level check;
  - in CMS MuonEG the muon leg is not matched.

## How CMS trigger matching works (data branch and MC branch)

**Order of the steps, every dataset mode and MC:**

1. **Golden JSON** (data only) → **own HLT path(s) fired** (`apply_trigger_requirement`,
   D:1804, M:2270). For MC the "own paths" are the OR of every path any stored condition can
   need (M:2171–2180).
2. **Object selection** (D:1833–1835, M:2305–2307):
   - muons: pT > 25 GeV, |η| < 2.4, `mediumId`, `pfRelIso04_all` < 0.15 (`selection.py:146–172`);
   - electrons: pT > 25 GeV, |η| < 2.5, `cutBased` ≥ 3 (medium; the cut-based ID includes an
     isolation cut) (`selection.py:175–186`);
   - jets: cleaned against those leptons (ΔR ≥ 0.4). Jets are removed, leptons never are.
3. **Electron–muon overlap removal**: an electron within ΔR < 0.12 of a selected muon is
   removed (D:1946, M:2419). The comment there states it: *"From here on `electrons` IS the
   post-removal collection, so every later step -- trigger matching, … -- uses it
   automatically."*
4. **Acceptances (the trigger matching)** on those post-selection, post-overlap-removal
   leptons: `evaluate_five_acceptances` (D:1959 → D:1199; M:2432 → M:1523).
   - Matching (`trigobj_best_match`, D:785 / M:886): each selected lepton is paired with the
     highest-pT `TrigObj` of the right id (11 or 13) that has the leg's filter bit set and lies
     within ΔR < 0.1.
5. **Event decision:**
   - data: `keep = acceptances[dataset]["accepted"]`, plus the exclusive (de-duplication) flag
     against higher-priority datasets (D:1964–1966);
   - MC: `keep = mc_store_mask(...)`, the OR of all acceptances (M:2448 → M:1481). Each event's
     acceptance bits are stored, and the builder keeps the five delivered flags.
6. **Object record** built from the kept events (D:1991, M:2487).
7. **The ≤ 4 non-jet rule** (electrons + muons + b-jets ≤ 4; the delivered rare4 version):
   `nonjet4_keep_mask` (D:2225, M:2828), `rare4_keep_mask = nonjet4_keep_mask` (D:2313,
   M:2918). It rejects whole events; a kept event keeps all its objects, so the matched lepton
   is never dropped from a kept event.
8. **Final-state labels and masses** (exact labels), in `run_combination_funnel` (D:1531 /
   M:1855, grouping at D:1558 / M:1911).

**Per dataset (acceptance = path fired AND the matching condition):**

| mode | path(s) | matching condition on SELECTED leptons | code |
|---|---|---|---|
| DoubleMuon | Mu17_TrkIsoVVL_(Tk)Mu8_TrkIsoVVL_DZ | ≥ 2 selected muons matched to id 13 with bit 1 (TrkIsoVVL); the leading matched online pT ≥ 17 GeV | D:917 / M:1018 → `matched_acceptance_mask` D:677 / M:778 |
| SingleMuon | IsoMu24 | ≥ 1 selected muon matched to id 13 with bit 2 (Iso), online pT ≥ 24 GeV | D:931 / M:1032 |
| DoubleEG | Ele23_Ele12_…_DZ | ≥ 2 selected electrons matched to id 11 with bit 16; leading matched online pT ≥ 23 GeV; offline pT > 30 GeV for both matched electrons (default mode "both") | D:945 / M:1046 |
| MuonEG | Mu23_Ele12 or Mu8_Ele23 | ≥ 1 selected muon (**not matched**: the muon leg cannot be matched in 2016 NanoAOD) AND ≥ 1 selected electron matched to id 11 with bit 32, online pT ≥ the electron-leg threshold of a path that fired | D:1075 / M:1176 |
| SingleElectron | Ele27_WPTight_Gsf | ≥ 1 selected electron matched to id 11 with bit 2, online pT ≥ 27 GeV, and that electron's offline pT > 32 GeV | D:1150 / M:1312 |
| MC | OR of all of the above (+ the Ele27 candidate, bit 4, stored only) | the same five functions on the same objects, the same call (M:2432); no de-duplication | M:2437–2458, M:1481 |

## Answers

**(a) Are the matched leptons the SELECTED ones?** Yes, for every mode and for MC. The matching
functions receive `muons` / `electrons` after pT/η, ID and isolation (steps 2–3) and after the
electron–muon overlap removal (D:1946 before D:1959; M:2419 before M:2432). There is no
lepton-by-jet overlap removal in CMS (jets are cleaned against leptons, not the reverse), so no
later step removes a lepton. The exception is MuonEG's muon leg, which is required as a selected
muon but cannot be matched.

**(b) When is the event-level decision taken?** At step 5: after the object selection and the
overlap removal, **before** the ≤ 4 non-jet rule (step 7) and **before** the final-state
labelling (step 8). This is the same position as ATLAS after #42, where the selection runs after
`retain_objects_for_storage` and before `filter_events_by_non_jet_object_total`
(`orchestration/handlers/parsing_handler.py:326–341` at 29291ae).

**(c) Is MC treated the same as data?** Yes, for the matching itself: the same functions on the
same objects (M:2432; the functions are byte-identical to the data branch's). MC differs only in
what is done with the result:
- one MC job evaluates all five acceptances and stores the event if ANY passes (no
  de-duplication), recording which ones passed;
- the builder then keeps events with any of the five delivered flags;
- for data, one job per dataset keeps that dataset's acceptance and de-duplicates against
  higher-priority datasets.

## Comparison with ATLAS after #42

ATLAS after #42:
- **MC:** `attach_lepton_trigger_matches` marks each electron/muon that a single-lepton chain
  of the event's year links to. After the kinematic/isolation cuts, overlap removal and
  object retention, `apply_lepton_trigger_selection` keeps the event if **at least one
  surviving selected lepton** is marked.
- **Collision data:** `apply_trigger_selection`, an event-level check applied **before** the
  object selection. The event passes if any electron or muon chain matched any object.

| # | aspect | CMS (data and MC) | ATLAS after #42 | same? |
|---|---|---|---|---|
| 1 | matched lepton must survive the object selection (pT/η, ID, isolation, overlap removal) | yes, data and MC | MC: yes. Data: no (event-level, before selection) | MC: same. **Data: CMS is stricter** |
| 2 | event decision before the ≤ 4 non-jet cap and the labelling | yes | yes (MC and data) | same |
| 3 | MC handled like data | yes (identical functions) | no (#42: MC per selected lepton, data event-level) | **different** |
| 4 | triggers | dataset-specific: dilepton (DoubleMuon, DoubleEG, MuonEG) and single-lepton (SingleMuon, SingleElectron), 2016 only | single-lepton chains only, per year (2015–2018, MC year from the random run number) | **different** |
| 5 | how many leptons must be matched | DoubleMuon and DoubleEG: ≥ 2; SingleMuon and SingleElectron: ≥ 1; MuonEG: ≥ 1 electron | ≥ 1 electron or muon | **different** |
| 6 | MuonEG muon leg | not matched (2016 NanoAOD limitation), only required as selected | n/a (no dilepton chains) | **different** |
| 7 | matching method | ΔR < 0.1 to a `TrigObj` with the right id and leg filter bit; online-pT and (DoubleEG, SingleElectron) offline-pT thresholds | the chain's trigger-match links (offline object indices), no ΔR and no thresholds | **different** |
| 8 | which leptons may be removed by overlap removal before matching | electrons near muons (ΔR < 0.12); jets never remove leptons | the ATLAS overlap removal (#32/#38), which can also remove leptons | **different** (selection, not matching) |
| 9 | does a kept event keep its matched lepton | yes (rare4 rejects whole events; it never truncates) | yes (the non-jet cap rejects whole events) | same |

Nothing here was changed, and implementing anything from #42 for CMS is out of scope. If the
group wants CMS to follow #42 more literally (e.g. single-lepton-only matching, or data
checked at event level), that is a physics/convention choice for Matan and the group.
