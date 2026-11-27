#--------------------------------------------------------------
# Powheg ggH_quark_mass_effects setup
#--------------------------------------------------------------
#include('PowhegControl/PowhegControl_ggF_H_Common.py')

evgenConfig.process     = "ggH H->Zy, Z->ll"
evgenConfig.description = "POWHEG+PYTHIA8+EVTGEN, ggH H->Zy, Z->ll mh=125 GeV CPS"
evgenConfig.keywords    = [ "SM", "Higgs", "SMHiggs", "Zgamma", "mH125" ]
evgenConfig.contact     = [ 'cyril.becot@cern.ch' ]
evgenConfig.minevents   = 2000
evgenConfig.inputfilecheck = 'TXT' #"mc15_13TeV.343981.PowhegPythia8EvtGen_NNLOPS_nnlo_30_ggH125_gamgam.evgen.TXT.e5564_tid10155507_00"

#--------------------------------------------------------------
# Pythia8 showering
# note: Main31 is set in Pythia8_AZNLO_CTEQ6L1_EvtGen_Common.py
#--------------------------------------------------------------
include('MC15JobOptions/Pythia8_AZNLO_CTEQ6L1_EvtGen_Common.py')

#--------------------------------------------------------------
# Pythia8 main31 update
#--------------------------------------------------------------
genSeq.Pythia8.UserModes += [ 'Main31:NFinal = 2' ]

#--------------------------------------------------------------
# Higgs at Pythia8
#--------------------------------------------------------------
genSeq.Pythia8.Commands += [ '25:onMode = off', # decay of Higgs
                             '25:onIfMatch = 22 23',
                             '23:onMode = off', #decay of Z
                             '23:mMin = 2.0',
                             '23:onIfMatch = 11 11',
                             '23:onIfMatch = 13 13',
                             '23:onIfMatch = 15 15' ] 
