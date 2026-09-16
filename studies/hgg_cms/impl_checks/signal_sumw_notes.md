# ZH cross-section check (implementation task 6)

**Question:** does CMS Open Data record 74132 (`ZH_HToGG_ZToAll_M125_TuneCP5_13TeV-powheg-pythia8`,
listed in `signal_sumw.json` under the `"ZH"` entry) include the gluon-fusion-initiated
ZH (`gg->ZH`) production mechanism, or only the quark-initiated (`qq->ZH`) one?

## Evidence

1. Record landing page (`https://opendata.cern.ch/record/74132`): dataset name
   `ZH_HToGG_ZToAll_M125_TuneCP5_13TeV-powheg-pythia8`; generators listed as
   `pythia8 POWHEG V2` (POWHEG for the hard process/LHE step, Pythia8 for
   showering/hadronization). The page's own text does not state whether
   `gg->ZH` is included.

2. The page links to the CMS McM (Monte Carlo Management) generator fragment
   for this request, `HIG-RunIISummer20UL16wmLHEGEN-01135`
   (`https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get_fragment/HIG-RunIISummer20UL16wmLHEGEN-01135`).
   That fragment names the exact POWHEG gridpack used to generate the LHE
   events:

   ```
   /cvmfs/cms.cern.ch/phys_generator/gridpacks/2017/13TeV/powheg/V2/HZJ_HanythingJ_NNPDF31_13TeV_M125/v1/HZJ_HanythingJ_NNPDF31_13TeV_M125.tgz
   ```

   The process name embedded in that path, `HZJ_HanythingJ`, is POWHEG's
   **quark-initiated** `H+Z(+jet)` NLO process ("HZJ" = the POWHEG-BOX-V2
   `HZJ` process, i.e. `qq(qg)->ZH(+jet)` at NLO+PS). POWHEG ships a
   **separate, distinctly-named** process for the loop-induced gluon-fusion
   channel (commonly packaged/referred to as `ggHZ`/`ggZH` in POWHEG and in
   CMS gridpack naming conventions); no such gridpack, and no reference to a
   `ggHZ`/`ggZH`-named process, appears anywhere in this record's generator
   configuration.

## Conclusion

**Record 74132 contains ONLY the quark-initiated `qq(qg)->ZH` process. It does
NOT include `gg->ZH`.** This is a POWHEG `HZJ`-gridpack sample, not a
combined qq+gg sample, and there is no companion `gg->ZH` record among the
six signal records used by this task's configs (`signal_sumw.json`) to add
that missing piece.

## Cross-section to use

`signal_sumw.json` currently records `cross_section_pb: 0.8839` for the `ZH`
entry. That number is the LHC Higgs Cross Section Working Group (LHCHXSWG)
**Yellow Report 4 (YR4) TOTAL ZH cross section at sqrt(s)=13 TeV, mH=125 GeV**
-- i.e. `qq/qg->ZH` **plus** `gg->ZH` combined -- per the YR4 13 TeV recommended
cross-sections page
(`https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV`,
"gg->ZH Cross Section" table), which gives, for MH=125.0 GeV at 13 TeV:

| component            | sigma [pb] |
|-----------------------|-----------:|
| qq/qg -> ZH (all but gg->ZH) | 0.7612 |
| gg -> ZH                     | 0.1227 |
| **Total (qq+gg)**            | **0.8839** |

Since this record's sample physically contains only the `qq/qg->ZH` process,
using the recorded total (0.8839 pb) to normalize an expected yield computed
from THIS record alone would **overstate** the expected ZH signal by
approximately the `gg->ZH` fraction (0.1227 / 0.8839 ~= 13.9%), because there
is no simulated sample here for the `gg->ZH` component to be added back in.

**Recommendation (for any yield estimate that uses only record 74132):
use the qq/qg->ZH-only YR4 cross section, 0.7612 pb**
(same source/table as above), not the recorded 0.8839 pb total. Any part of
this task that computes a "preview expected yield" for ZH specifically
(none of the pre-set Part D acceptance criteria require this -- Part D's
single-file preview yield is computed for ggH only) should use 0.7612 pb,
and this discrepancy should be called out explicitly if a ZH yield number is
ever produced downstream (e.g. task 7 or later analysis stages), since
`signal_sumw.json` was not modified by this task (see task rules: "don't
edit signal_sumw.json's recorded values") and still shows 0.8839 pb.

## Addendum (implementation task 6, Part 1): ttH file count instability -- 15 vs 16 files

**Question**: the full cluster run's ttH job (record 67611) processed and
selected on exactly 15 files ("Processing files: 15/15", all OK), matching
the frozen file list fetched for this task and committed at
`studies/hgg_cms/impl_checks/mapping_check/cms_hgg_signal_file_lists.json`
-- but this task's earlier `signal_sumw.json` (task 5) recorded `n_files:
16` for the same record. Which file is in the 16-file count but not the
15-file list the full run actually used, if determinable?

**Finding**: the portal's own file listing for record 67611 is not stable
even within this one day. Re-querying
`https://opendata.cern.ch/api/records/67611` directly (16 Sep 2026,
AFTER the full run finished) returned **16** files again -- the same 15
files in `cms_hgg_signal_file_lists.json` (index groups `2520000`,
`2530000`, `2550000`, `260000`, `270000` -- 3+3+1+5+3=15) **plus one
additional file**, in a group (`80000`) that was entirely absent from the
15-file list fetched earlier the same day (the fetch behind this task's
frozen list, and independently, the full run's own ttH job's own fetch,
both of which saw only 15):

```
root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/
ttHJetToGG_M125_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8/NANOAODSIM/
106X_mcRun2_asymptotic_v17-v2/80000/3E9B663B-5DAD-6941-BD10-2BFF90046E79.root
(1,094,709,190 bytes, ~1.02 GiB)
```

This is very likely (not proven -- the ORIGINAL task-5 fetch behind
`signal_sumw.json`'s `n_files: 16` was not itself saved file-by-file,
only as a count) the file that was missing when the full run's ttH job
and this task's frozen list were both fetched, and has since reappeared.
**UNVERIFIED**: whether it was ever actually unavailable (e.g. a
temporarily-offline EOS replica) or the listing API itself is simply
flaky/inconsistent across queries; this project has no visibility into
CERN Open Data's own infrastructure to distinguish those.

**Consequence for this task's analysis**: none that requires action. The
full run's ttH normalization uses that run's OWN `genEventSumw`, summed
over EXACTLY the 15 files its own job actually processed successfully (see
`merge_outputs.py`'s per-record `genEventSumw_over_processed_files`,
sourced from the pipeline's own `aggregate_sumw_for_processed_files`) --
never `signal_sumw.json`'s stale 16-file total, and never a number that
assumes a fixed, time-invariant file list. This is exactly why that rule
exists. What this addendum adds is a plausible, concrete identification of
*which* file the 15-vs-16 discrepancy is, for the record -- not a change
to how ttH is normalized.

**Broader implication, flagged explicitly**: this is stronger evidence
than `mapping_check/README.md`'s already-flagged risk (which was about
*file ORDER* stability across independent fetches). Here the file *SET
ITSELF* changed size within one day for at least one record. This does not
retroactively invalidate the full run (each job's own fetch + this task's
frozen list + the merge's identity check all agree with each other, 15
files, self-consistently), but it means a LATER re-fetch of any record's
file list (e.g. for the Z->ee run, record 35669) should not be assumed to
exactly match a list frozen at a different time, and any such mismatch
should be checked against portal availability before assuming an error in
this project's own code.

## UNVERIFIED / caveats

- I did not download or inspect the sample's actual LHE-level generator
  block or `GenXsecAnalyzer` output from the NanoAOD files themselves (that
  would require reading full files, which is out of this task's remote-read
  budget); this conclusion rests entirely on the McM generator-fragment
  metadata (a small, already-public metadata page), which is the standard
  way CMS records which physical process a gridpack encodes.
- I have not independently re-derived the 0.7612/0.1227/0.8839 pb numbers
  from a NNLO+NLO-EW calculation -- they are quoted as-is from the LHCHXSWG
  YR4 twiki table, which is the standard citation CMS analyses use for this
  process.
- "HZJ" as POWHEG's qq-initiated ZH(+jet) process name, and the existence of
  a separate POWHEG process for `gg->ZH`, are standard/well-documented facts
  about the POWHEG-BOX-V2 generator suite; I have not personally inspected
  the POWHEG-BOX-V2 source code in this task to confirm the naming, only the
  gridpack path CMS's own McM system recorded for this specific request.
