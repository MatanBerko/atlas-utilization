include("Sherpa_i/Base_Fragment.py")
include("Sherpa_i/NNPDF30NNLO.py")

evgenConfig.description = "Interference terms for QCD-electroweak same-sign llvvjj+0,1j@LO."
evgenConfig.keywords = ["SM", "diboson", "2lepton", "VBS"]
evgenConfig.contact  = ["atlas-generators-sherpa@cern.ch", "chris.g@cern.ch"]
evgenConfig.nEventsPerJob = 500

genSeq.Sherpa_i.RunCard="""
(run){
  ACTIVE[25]=1;
  MASS[25]=126.0;
  WIDTH[25]=0.00418;
  MASSIVE[11]=1;
  MASSIVE[13]=1;
  MASSIVE[15]=1;
  PARTICLE_CONTAINER 991[m:-1] leptons 11 -11 13 -13 15 -15;

  %scales, tags for scale variations
  FSF:=1.; RSF:=1.; QSF:=1.;
  SCALES STRICT_METS{FSF*MU_F2}{RSF*MU_R2}{QSF*MU_Q2};
  CORE_SCALE=VAR{Abs2(p[2]+p[3]+p[4]+p[5])};
  % simplified setup as long as only 2->6 taken into account:
  %SCALES=VAR{FSF*Abs2(p[2]+p[3]+p[4]+p[5])}{RSF*Abs2(p[2]+p[3]+p[4]+p[5])}{QSF*Abs2(p[2]+p[3]+p[4]+p[5])};

  %tags for process setup
  NJET:=1; QCUT:=20.;

  EXCLUSIVE_CLUSTER_MODE=1
  SOFT_SPIN_CORRELATIONS=1

  ME_QED_CLUSTERING_THRESHOLD=5;

  % improve colour-flow treatment
  CSS_CSMODE=1

  % improve integration performance
  PSI_ITMIN=25000;
  CDXS_VSOPT=5;
  INTEGRATION_ERROR 0.05;
}(run)


(processes){
  Process 93 93 -> 11 11 -12 -12 93 93 93{NJET};
  Order (1,5) {6}
  Order (2,5) {7}
  CKKW sqr(QCUT/E_CMS);
  End process;

  Process 93 93 -> 13 13 -14 -14 93 93 93{NJET};
  Order (1,5) {6}
  Order (2,5) {7}
  CKKW sqr(QCUT/E_CMS);
  End process;

  Process 93 93 -> 15 15 -16 -16 93 93 93{NJET};
  Order (1,5) {6}
  Order (2,5) {7}
  CKKW sqr(QCUT/E_CMS);
  End process;

  Process 93 93 -> 11 13 -12 -14 93 93 93{NJET};
  Order (1,5) {6}
  Order (2,5) {7}
  CKKW sqr(QCUT/E_CMS);
  End process;

  Process 93 93 -> 11 15 -12 -16 93 93 93{NJET};
  Order (1,5) {6}
  Order (2,5) {7}
  CKKW sqr(QCUT/E_CMS);
  End process;

  Process 93 93 -> 13 15 -14 -16 93 93 93{NJET};
  Order (1,5) {6}
  Order (2,5) {7}
  CKKW sqr(QCUT/E_CMS);
  End process;

  Process 93 93 -> -11 -11 12 12 93 93 93{NJET};
  Order (1,5) {6}
  Order (2,5) {7}
  CKKW sqr(QCUT/E_CMS);
  End process;

  Process 93 93 -> -13 -13 14 14 93 93 93{NJET};
  Order (1,5) {6}
  Order (2,5) {7}
  CKKW sqr(QCUT/E_CMS);
  End process;

  Process 93 93 -> -15 -15 16 16 93 93 93{NJET};
  Order (1,5) {6}
  Order (2,5) {7}
  CKKW sqr(QCUT/E_CMS);
  End process;

  Process 93 93 -> -11 -13 12 14 93 93 93{NJET};
  Order (1,5) {6}
  Order (2,5) {7}
  CKKW sqr(QCUT/E_CMS);
  End process;

  Process 93 93 -> -11 -15 12 16 93 93 93{NJET};
  Order (1,5) {6}
  Order (2,5) {7}
  CKKW sqr(QCUT/E_CMS);
  End process;

  Process 93 93 -> -13 -15 14 16 93 93 93{NJET};
  Order (1,5) {6}
  Order (2,5) {7}
  CKKW sqr(QCUT/E_CMS);
  End process;
}(processes)

(selector){
  Mass 11 -11 0.1 E_CMS;
  PT 991 5.0 E_CMS;
  NJetFinder 2 15. 0. 0.4 -1;
}(selector)
"""

genSeq.Sherpa_i.Parameters += [ "EW_SCHEME=3", "GF=1.166397e-5" ]
genSeq.Sherpa_i.NCores = 16


