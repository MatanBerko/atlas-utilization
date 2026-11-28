# Hand-check sheet: registry v6 (28 Nov 2026)

There are **7 values**, all `"matan_hand_check": "PENDING"` in `studies/cms_mc_weights_v3/cms_mc_normalisation_v6.json`.
Check each one on the page given and tick it.

When all are confirmed, a separate commit sets them to "VERIFIED BY MATAN"; the MC build must not run before then.

## Portal values (5)

To check each one:
1. Open the MiniAOD record.
2. In the dataset's "Cross section" box, look at the field **Total value** (API field
   `metadata.cross_section.total_value`).
3. Confirm the number, and that the filter and matching efficiencies are shown as 1.

| ✓ | NanoAOD record | MiniAOD record (open this) | dataset | value in v6 [pb] | portal shows |
|---|---|---|---|---:|---|
| ☐ | 75561 | [75560](https://opendata.cern.ch/record/75560) | ZZJJTo4L_EWKnotop | 0.0009928 | 9.928e-04 |
| ☐ | 72648 | [72647](https://opendata.cern.ch/record/72647) | WWJJToLNuLNu_EWK_noTop | 0.09219 | 9.219e-02 |
| ☐ | 71636 | [71635](https://opendata.cern.ch/record/71635) | WpWpJJ_EWKnotop | 0.02694 | 2.694e-02 |
| ☐ | 71640 | [71639](https://opendata.cern.ch/record/71639) | WpWpJJ_QCDnotop | 0.02037 | 2.037e-02 |
| ☐ | 72720 | [72719](https://opendata.cern.ch/record/72719) | WZ2JetsTo3LNu_MJJ-100toInf_EWKnotop (the WZjj replacement; **PROPOSAL**) | 0.01370 | 1.370e-02 |

## Constructed values (2)

Both use the same construction: σ(production) × BR(H→ZZ) × (2B − B²) × ε(4-lepton filter).
- B = BR(Z→ℓℓ), ℓ = e, μ, τ = 0.033632 + 0.033662 + 0.033696 = **0.10099**. This is the PDG value in v5 (40062 factor
  "BR(Z -> ll), l = e, mu, tau"), from <https://pdglive.lbl.gov/Particle.action?node=S044>, Z decay modes.
- 2B − B² = 0.20198 − 0.0101990 = **0.1917810199**.
- BR(H→ZZ) = **0.02619**: YR4 BR page, <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR>, table
  "H → WW, H → ZZ, Total Width", row 125.00. This is the v5 40062 factor "BR(H -> ZZ)".

**☐ 74314 ZH_HToZZ_4LFilter**
- σ(qq→ZH) = **0.7612 pb**: YR4 13 TeV page, <https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV>,
  ZH table, row 125.00. It is 0.8839 (total) − 0.1227 (gg→ZH). This is the v5 74292 factor
  "sigma(ZH, all but gg->ZH)".
- ε = **0.1509**: McM request HIG-RunIISummer20UL16wmLHEGEN-00239,
  <https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-00239>, field
  `generator_parameters[-1].match_efficiency` = 0.150882730885. The decision uses 0.1509 (difference 1.1e-4 relative).
  The portal record [74313](https://opendata.cern.ch/record/74313) shows it rounded as "matching efficiency 0.2".
- Arithmetic: 0.7612 × 0.02619 = 0.019935828; × 0.1917810199 = 0.003823313; × 0.1509 = **5.769380e-4 pb**.
- For comparison only: the portal total_value is 0.7935 pb (production only, NOT used); ATLAS 346645 is 2.089e-4 pb.

**☐ 40062 GluGluToZH_HToZZTo4L (changed value)**
- σ(gg→ZH) = **0.1227 pb**: YR4 13 TeV page, ZH table, row 125.00, column σ(gg→ZH). This is the v5 40062 factor
  "sigma(gg->ZH)".
- ε = **0.1505**: McM request HIG-RunIISummer20UL16wmLHEGEN-00294,
  <https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get/HIG-RunIISummer20UL16wmLHEGEN-00294>, field
  `generator_parameters[-1].filter_efficiency` = 0.1505.
- Arithmetic: 0.1227 × 0.02619 = 0.003213513; × 0.1917810199 = 0.000616291; × 0.1505 = **9.275177e-5 pb**.
- Old (v5, delivered 14 Nov): 6.22392e-5 pb = 0.1227 × 0.02619 × 0.10099 × 0.19178 (ESTIMATE).
- **New / old = 1.4902.**

## Reading behind the constructed values (INTERPRETATION, decided 28 Nov)

JHUGen `DecayMode1=8 DecayMode2=9` generates H → ZZ with at least one Z → ℓℓ, a fraction 2B − B² of H → ZZ. The McM
efficiency is the `FilterNLept=4` efficiency on top of that. This is supported by the 74314 file-0 decay mix:

| | ℓℓℓℓ | ℓℓqq | ℓℓνν |
|---|---:|---:|---:|
| predicted | 0.357 | 0.499 | 0.143 |
| file 0 (27 Nov) | 0.367 | 0.489 | 0.143 |

No CMS document states it.
