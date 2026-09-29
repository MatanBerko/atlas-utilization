"""
Investigate the single Step 4 closure-test overlap: (run=280016, lumi=24,
event=42925881) is in BOTH DoubleMuon's inclusive/accepted set AND
SingleMuon's exclusive set (i.e. NOT vetoed by DoubleMuon's acceptance,
when evaluated on SingleMuon's own copy of the event) -- even though
DoubleMuon's OWN copy of the SAME event accepts it. Root-cause this single
event exactly: same muon/trigobj values in both files' copies? Same
matched_acceptance_mask verdict when applied identically?
"""
import sys
sys.path.insert(0, "/storage/agrp/berkom/atlas-utilization/work/matching_validation_pinned/repo")

import awkward as ak
import numpy as np
import uproot

from studies.m0m1j0_cms import selection
from studies.cms_datasets.cluster.run_dataset_on_file import (
    TRIGGER_PATHS_BY_DATASET, TRIGOBJ_BIT_TRKISOVVL,
    DOUBLEMUON_MATCHED_MIN_MUONS, DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV,
    matched_acceptance_mask, trigobj_best_match_pt, MATCH_DR_MAX,
)

TARGET_RUN, TARGET_LUMI, TARGET_EVENT = 280016, 24, 42925881

DM_URLS = [
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v2/2430000/05DD095C-F6C3-9A4F-9FB3-348A5A6403D5.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v2/2430000/78FA0801-28AF-3A45-A36A-AB7CC9A5506E.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v2/2430000/A3CE8422-11FF-5D4C-922D-B592FDD76682.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v2/2430000/ED3359B9-BF1E-044C-8418-ACDDE2B11FF0.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v2/2430000/EF0619CE-F699-5942-BA8B-206D2D434A33.root",
]
SM_URLS = [
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/130000/0A4230E2-0C75-604D-890F-A4CE5E5C164E.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/130000/1D280BA6-2EBB-A544-91EB-E821F3CF0B06.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/70000/08BEF135-37C0-F145-88E9-63F7A10D3BC7.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/70000/5BF83F4E-336D-1641-9576-53FC198765B5.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/70000/95AF7A2E-F973-5642-96C6-B37EA7C96FF7.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/70000/E801FC2F-0877-9F4C-978D-FE9C94B92CAF.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/70000/16CB6056-D4D5-2046-9D30-82D8985F831F.root",
    "root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/70000/20CCC9D4-0AD5-9E42-B642-DE86F25153ED.root",
]

BRANCHES = [
    "run", "luminosityBlock", "event",
    "nMuon", "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass", "Muon_mediumId", "Muon_pfRelIso04_all",
    "nTrigObj", "TrigObj_pt", "TrigObj_eta", "TrigObj_phi", "TrigObj_id", "TrigObj_filterBits",
]


def find_event(urls, run, lumi, event):
    for url in urls:
        t = uproot.open(url)["Events"]
        ev = t.arrays(BRANCHES, library="ak")
        mask = (ak.to_numpy(ev.run) == run) & (ak.to_numpy(ev.luminosityBlock) == lumi) & (ak.to_numpy(ev.event) == event)
        if mask.sum() > 0:
            print(f"  FOUND in {url.rsplit('/',1)[-1]}, index {np.where(mask)[0]}")
            return ev[mask], url
    return None, None


def make_trigobj(events):
    return ak.zip({
        "pt": events.TrigObj_pt, "eta": events.TrigObj_eta, "phi": events.TrigObj_phi,
        "id": events.TrigObj_id, "filterBits": events.TrigObj_filterBits,
    })


print(f"=== Locating event ({TARGET_RUN},{TARGET_LUMI},{TARGET_EVENT}) in DoubleMuon files ===")
dm_ev, dm_url = find_event(DM_URLS, TARGET_RUN, TARGET_LUMI, TARGET_EVENT)
print(f"=== Locating event ({TARGET_RUN},{TARGET_LUMI},{TARGET_EVENT}) in SingleMuon files ===")
sm_ev, sm_url = find_event(SM_URLS, TARGET_RUN, TARGET_LUMI, TARGET_EVENT)

for label, ev in [("DoubleMuon copy", dm_ev), ("SingleMuon copy", sm_ev)]:
    print(f"\n--- {label} ---")
    print("Muon_pt:", ak.to_list(ev.Muon_pt[0]))
    print("Muon_eta:", ak.to_list(ev.Muon_eta[0]))
    print("Muon_phi:", ak.to_list(ev.Muon_phi[0]))
    print("Muon_mediumId:", ak.to_list(ev.Muon_mediumId[0]))
    print("Muon_pfRelIso04_all:", ak.to_list(ev.Muon_pfRelIso04_all[0]))
    print("nTrigObj:", ev.nTrigObj[0])
    trig_id = ak.to_list(ev.TrigObj_id[0])
    trig_bits = ak.to_list(ev.TrigObj_filterBits[0])
    trig_pt = ak.to_list(ev.TrigObj_pt[0])
    trig_eta = ak.to_list(ev.TrigObj_eta[0])
    trig_phi = ak.to_list(ev.TrigObj_phi[0])
    for i in range(len(trig_id)):
        if trig_id[i] == 13 and (trig_bits[i] & TRIGOBJ_BIT_TRKISOVVL):
            print(f"  TrigObj[{i}]: id=13(muon) filterBits={trig_bits[i]} pt={trig_pt[i]:.3f} eta={trig_eta[i]:.4f} phi={trig_phi[i]:.4f} (has bit1/TrkIsoVVL)")

    muons = selection.select_muons(ev)
    print("selected muon pt:", ak.to_list(muons.pt[0]))
    print("selected muon eta:", ak.to_list(muons.eta[0]))
    print("selected muon phi:", ak.to_list(muons.phi[0]))
    trigobj = make_trigobj(ev)
    best_pts = trigobj_best_match_pt(muons, trigobj, TRIGOBJ_BIT_TRKISOVVL, MATCH_DR_MAX)
    print("best_match_pt per selected muon (bit1, dR<0.1):", ak.to_list(best_pts[0]))
    accept = matched_acceptance_mask(muons, trigobj, TRIGOBJ_BIT_TRKISOVVL,
                                       DOUBLEMUON_MATCHED_MIN_MUONS, DOUBLEMUON_MATCHED_LEADING_PT_MIN_GEV)
    print("matched_acceptance_mask result:", ak.to_list(accept) if not isinstance(accept, np.ndarray) else accept.tolist())
