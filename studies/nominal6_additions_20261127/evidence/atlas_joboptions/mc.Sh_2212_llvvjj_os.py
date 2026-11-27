include("Sherpa_i/Base_Fragment.py")
include("Sherpa_i/NNPDF30NNLO.py")

evgenConfig.description = "Electroweak opposite-sign llvvjj+0,1j@LO including triboson-like diagrams."
evgenConfig.keywords = ["SM", "diboson", "triboson", "2lepton", "VBS"]
evgenConfig.contact  = ["atlas-generators-sherpa@cern.ch", "chris.g@cern.ch"]
evgenConfig.nEventsPerJob = 50

genSeq.Sherpa_i.RunCard="""
(run){
  ACTIVE[25]=1;
  MASS[25]=126.0;
  WIDTH[25]=0.00418;
  MASSIVE[5]=1; 
  PARTICLE_CONTAINER 901 lminus 11  13  15;
  PARTICLE_CONTAINER 902 lplus -11 -13 -15;

  %scales, tags for scale variations
  FSCF:=1.0; RSCF:=1.0; QSCF:=1.0;
  SCALES=STRICT_METS{FSCF*MU_F2}{RSCF*MU_R2}{QSCF*MU_Q2};
  CORE_SCALE=VAR{Abs2(p[2]+p[3]+p[4]+p[5])};
  % simplified setup as long as only 2->6 taken into account:
  % SCALES=VAR{FSCF*Abs2(p[2]+p[3]+p[4]+p[5])}{RSCF*Abs2(p[2]+p[3]+p[4]+p[5])}{QSCF*Abs2(p[2]+p[3]+p[4]+p[5])};

  %tags for process setup
  NJET:=1; QCUT:=20.;

  EXCLUSIVE_CLUSTER_MODE=1;
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
  Process 93 93 -> 901 91 902 91 93 93 93{NJET};
  Order (*,6); CKKW sqr(QCUT/E_CMS);
  End process;
}(processes)

(selector){
  Mass 11 -11 0.25 E_CMS
  Mass 13 -13 0.4614 E_CMS
  Mass 15 -15 3.804 E_CMS
  "PT" 90 5.0,E_CMS:5.0,E_CMS [PT_UP]
  NJetFinder 2 15. 0. 0.4 -1;
}(selector)
"""

genSeq.Sherpa_i.Parameters += [ "EW_SCHEME=3", "GF=1.166397e-5" ]
genSeq.Sherpa_i.NCores = 16

