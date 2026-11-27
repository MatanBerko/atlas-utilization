#--------------------------------------------------------------
# Pythia8 showering
#--------------------------------------------------------------
include('MC15JobOptions/Pythia8_AZNLO_CTEQ6L1_EvtGen_Common.py')

#--------------------------------------------------------------
# EVGEN configuration
#--------------------------------------------------------------
evgenConfig.process     = "VBF H,  H->Zgam, Z->ll"
evgenConfig.description = "POWHEG+PYTHIA8+EVTGEN, VBF H->Zllgam"
evgenConfig.keywords    = [  "SM", "Higgs", "SMHiggs", "VBF", "2lepton","photon", "mH125"  ]
evgenConfig.contact     = [ 'amorley@cern.ch' ]
evgenConfig.inputfilecheck = 'TXT' 

#--------------------------------------------------------------
# Pythia8 Powheg update
#--------------------------------------------------------------
genSeq.Pythia8.Commands += [ 'Powheg:NFinal = 3' ]

#--------------------------------------------------------------
# Higgs at Pythia8
#--------------------------------------------------------------
genSeq.Pythia8.Commands += [ '25:onMode = off', # decay of Higgs
                             '25:onIfMatch = 22 23',
                             '23:onMode = off',
                             '23:mMin = 2.0',
                             '23:onIfAny = 11 13 15' ]
