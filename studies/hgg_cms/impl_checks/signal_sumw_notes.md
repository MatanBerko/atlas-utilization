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
