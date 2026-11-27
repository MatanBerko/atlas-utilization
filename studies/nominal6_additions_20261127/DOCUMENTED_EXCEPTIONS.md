# Documented differences between the CMS MC set and the ATLAS "Nominal-6" background list

This text is meant for the README of the CMS MC delivery. It explains, for a reader who has not followed our work,
every place where the CMS Monte Carlo (CMS Open Data, 2016 post-VFP, UL16 NanoAODv9) deliberately differs from the
ATLAS nominal background list ("Nominal-6", 246 ATLAS DSIDs, ATLAS Open Data release 2024r-pp). All decisions are
Matan's. Sources:
- `studies/cms_mc_weights_v3/sources/v8_decisions_2026-11-27.json` (27 Nov 2026, items N/C);
- `v5_decisions_2026-11-03.json`, `v6_decisions_2026-11-07.json` and `v7_decisions_2026-11-14.json` (earlier items);
- the comparison itself, `studies/nominal6_correspondence_20261124/REPORT.md`.

ATLAS numbers are DSIDs, and CMS numbers are CERN Open Data NanoAOD record ids. "Prompt lepton" means an electron or
muon from a W/Z/H/τ decay. The analysis uses lepton-triggered data only, so a process without a prompt lepton can
enter only through a jet faking a lepton.

The four items that *are* being added (N1–N4: electroweak VV+2 jets, QCD same-sign WW, Higgs Dalitz, qq→ZH H→4ℓ)
are not exceptions and are not listed here, except for the caveats on them in the last section.

## ATLAS processes that are documented, not added (decision of 27 Nov 2026)

**N5 – VBF H→ZZ→ℓℓbb (ATLAS 450576).** CMS has no exclusive VBF H→ZZ→ℓℓbb sample. The only candidate, VBF H→ZZ→2ℓ2X
(68833), also contains the decays H→ZZ→2ℓ2ν and H→ZZ→4ℓ, which are already in our set as 68741 and 68847. Adding it
would double count those, so ℓℓbb in VBF is missing from the CMS MC. It is a very small contribution: ATLAS gives
2.0 × 10⁻³ pb.

**N6 – gg→ZH with H→ττ or H→μμ (ATLAS 600686, 345098).** No such CMS sample was found. The CMS ZH→ττ (74684) and
ZH→μμ (74682) samples are quark-initiated (qq→ZH) only, so the gluon-initiated part is missing. ATLAS gives
7.7 × 10⁻³ pb.

**N7 – Standard-Model three-top production (ATLAS 304014).** CMS samples exist: tttJ 67771 and tttW 68067. They are
not added because the process is negligible: about 18 events before any selection in 16.4 fb⁻¹, against an estimated
~320 cluster files to process.

**N8 – VH with H→invisible and a leptonic W/Z, and gg→ZH with H→ZZ→4ν (ATLAS 346605, 346606, 346607, 345596).**
CMS has these only with a hadronically decaying W/Z (e.g. 71359, 70515), which gives no prompt lepton. A CMS sample
with a leptonic W/Z was not found, so the process is missing.

**N9 – the Z→νν and Z→qq part of tZq (ATLAS 410560).** ATLAS 410560 includes every Z decay with a leptonic top, plus
Z→ℓℓ with a hadronic top. Our CMS tZq sample (68325, tZq_ll) has Z→ℓℓ only. No CMS sample with Z→νν/qq was found.
The difference is the part of tZq in which the only prompt lepton comes from the top.

**N10 – inclusive-decay VBF and VH Higgs samples (ATLAS 346317, 346310, 346311, 346312).** ATLAS lists these
"all decays" samples *on top of* its exclusive-decay Higgs samples, which is a double count inside the ATLAS list.
The only near CMS equivalent, VH→non-bb (69389), would double count every VH sample we have (VH→ττ, μμ, WW, ZZ, Zγ),
so it is not added. Whether ATLAS intends this double count is an open question to the ATLAS side.

**N11 – V+γ (ATLAS 700398–700404, Sherpa 2.2.11, pT(γ) > 7 GeV).** CMS samples exist (69575, 73904, 73900) but are not
added. They overlap the photon radiation already present in our W+jets (69715/17/19) and Drell–Yan (35631, 35669)
samples. Neither pipeline has a sample-level (generator-level) photon overlap removal that would make the two
additive. On the ATLAS side, V+γ is used next to V+jets in the same way, so ATLAS double counts this region.

**N12 – V+γγ, electroweak ℓνγjj and ℓℓγjj, and γγγ (ATLAS 700195–700201, 700709, 700710, 700007).** Some of these have
no CMS sample (V+γγ, γγγ). For the rest (42145, 42137), the CMS portal cross sections look wrong by orders of
magnitude (66,680 pb and 145 pb, against ATLAS 1.8 pb and 0.3 pb). The same photon overlap as for N11 also applies.

**N13 – hadronic W/Z at high pT and hadronic V+γ (ATLAS 700843, 700849, 700855, 700352, 700353, 700507).** These have
no prompt lepton. They enter lepton-triggered events only through a fake lepton, a region dominated by QCD multijet,
which is absent on both sides (see below). The CMS samples (WJetsToQQ 69751/53/55/57, ZJetsToQQ 74912/14/16/18,
WGToJJ 69559) would cost about 3,710 cluster files.

**N14 – WZ→qqνν, ZZ→qqνν / bbνν, ZZ→4ν (ATLAS 700491, 700495, 700496, 700605).** These have no prompt lepton. CMS has
only ZZ→2ν2q (75571); WZ→qqνν and ZZ→4ν were not found.

**N15 – the fully hadronic part of tW (ATLAS 601352, 601355: tW with inclusive decays).** Our CMS tW samples (64895
top, 64839 antitop) are "NoFullyHadronicDecays" and normalised as such. The difference between them and the ATLAS
inclusive samples is the fully hadronic decay, which has no prompt lepton. The CMS inclusive tW samples (64881, 64825)
would double count our samples, so they are not added.

## CMS samples kept although ATLAS has no exact counterpart (decision of 27 Nov 2026)

**C1 – t-channel single top with hadronic top decays.** Our CMS t-channel samples (64759 top, 64659 antitop; 4-flavour
POWHEG+MadSpin) contain every top decay. The ATLAS ones (410658, 410659) contain the leptonic top decay only. The CMS
set therefore also contains hadronic-top t-channel events, which reach lepton final states only through fake
leptons. The normalisation follows ATLAS's source: 136.02 / 80.95 pb (Hathor NLO, decision D5).

**C2 – tribosons with hadronic decays.** Our CMS tribosons (72701 WWW, 72711 WWZ, 72761 WZZ, 75600 ZZZ) contain every
W/Z decay. The ATLAS ones (364242–364249, 364336–364339, Sherpa) are lepton-filtered. The CMS set therefore also
contains triboson events with fewer prompt leptons.

**C3 – ggF and VBF H→ZZ→2ℓ2ν (CMS 37616, 68741).** ATLAS has no exclusive sample for this decay in its nominal list.
The CMS samples are kept.

**C4 – VH with H→WW and all W/Z decays (CMS 41873, 41877, 41914, 40095).** ATLAS splits this process into other
slices (341456, 341458, 341460, 345325, 345433, 345445, 346524). The CMS samples cover the same physics with inclusive
decays (40095, gg→ZH, has Z→ℓℓ only) and are kept.

## Earlier exceptions (decided 31 Oct – 14 Nov 2026, already in the delivered README)

**E1 – diboson normalisation.** CMS normalises its dibosons to NNLO: WZ and ZZ as generator × NNLO/NLO k-factor
(arXiv:1604.08576, arXiv:1405.2219), and WW as 118.7 pb × BR (arXiv:1408.5243). These totals include the
loop-induced gg→VV. ATLAS uses its Sherpa generator values with kFactor 1 and has no separate gg→VV samples.
CMS / ATLAS for the same process is 0.92–1.24:
- WZ→ℓνqq 0.92;
- WZ→ℓννν 1.22;
- WW→ℓνqq 1.09;
- WZ→3ℓν 1.24;
- ZZ→4ℓ 1.19;
- WW→2ℓ2ν 1.05.

**E2 – electroweak V+2 jets not included (CMS 35999, 35987, 35993; ATLAS 700358–700364).** The CMS EW Z+2j and W+2j
samples were dropped because they double count with the diboson samples.

**E3 – tt̄Z without the ATLAS k-factor.** ATLAS applies kFactor 1.11 (tt̄Z→νν/qq, 410156/410157) and 1.12 (tt̄+ℓℓ,
410218–410220). CMS keeps the generator NLO values (k = 1) for 68185, 68187 and 68206. The difference is about 11 %, on
a background below 0.1 % of the total.

**tWℓℓ at LO only (CMS 64873).** It is normalised to the generator LO value, 0.01105 pb. This is the only value
available: there is no NLO sample or published total for this phase space.

**gg→ZH, H→ZZ→4ℓ (CMS 40062): filter efficiency estimated.** The sample is 4-lepton filtered and its filter
efficiency is not published. The normalisation is 0.1227 pb (YR4) × BR(H→ZZ) 0.02619 × BR(Z→ℓℓ) 0.10099 × ε, with
ε = 1 − (1 − 0.10099)² = 0.19178. This is an ESTIMATE: the probability that at least one of the two other Z bosons
decays to leptons.

**Photons not included.** No γ+jets, V+γ or tt̄γ samples are in the CMS set, and the CMS selection does not use
photons. On the ATLAS side, reconstructed photons are used in the object overlap removal (a jet within ΔR < 0.4 of a
photon is removed); the CMS selection has no such step. This pipeline difference is open (item P1).

**QCD multijet absent on both sides.** Not in the CMS MC (decision of 14 Nov 2026). ATLAS lists Pythia8 dijet slices
JZ0–JZ12 (364700–364712) and expects them to contribute essentially nothing after its lepton selection. A one-file
CMS probe (ESTIMATE) found QCD negligible in two-lepton final states. In single-lepton + jets final states, however,
it was at the scale of the data excess over the MC.

**D11 – Z→νν+jets only for HT > 100 GeV (CMS 74894–74906).** The HT-binned LO ZJetsToNuNu samples start at
HT = 100 GeV, so Z→νν with HT < 100 GeV is not covered.

**D13 – Higgs decays and modes not included.** The following are not included:
- tH (tHq, tHW; ATLAS 346188, 346414, 346486, 346511). The CMS samples 65649/65721 are generated at a non-SM coupling
  point and would need per-event reweighting (UNVERIFIED).
- Higgs decays to eτ/μτ as named in ATLAS (345124, 345125, 346194, 346195, 345213–345216, 345218, 345219). Whether
  these are lepton-flavour-violating or a ττ subset is unknown from the metadata.
- H→ee (ATLAS 345876–345878; CMS 69343): BR ≈ 5 × 10⁻⁹.
- Higgs decays without a prompt lepton: H→bb/cc with Z→νν, H→invisible with a hadronic V, and H→γγ (photons).

## Caveats on the four added items (for the README once they are produced)

**N1 – no separate EW–QCD interference sample.** ATLAS's interference pieces 700591–700594 are about 6 % of its
EW VV+2j total. Diagrams with triboson-like topologies (V→jj) are inside the EW VV+2j samples on both sides, which is
a partial overlap with the triboson samples.

The CMS EW samples are generated with an m(jj) > 100 GeV cut (cards, `REPORT.md` section 3). This removes most of
that region, but not all of it. The Higgs boson is part of the electroweak model on both sides, so s-channel Higgs
diagrams (e.g. VBF H→WW) are expected inside the EW VV+2j samples. This is read from the cards only and its size was
not measured:
- CMS: the `sm-ckm_no_b_mass` model, with no `/ h` exclusion in the process cards;
- ATLAS: `ACTIVE[25]=1` in 700588–700590.

This would overlap our VBF/VH Higgs samples.

**N3 – overlap with H→Zγ.** See `REPORT.md` section 2: it must be settled before N3 is produced.
