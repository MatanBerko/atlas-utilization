#--------------------------------------------------------------
# Pythia8 showering
#--------------------------------------------------------------
include('MC15JobOptions/Pythia8_AZNLO_CTEQ6L1_EvtGen_Common.py')


#--------------------------------------------------------------
# EVGEN configuration
#--------------------------------------------------------------
evgenConfig.process     = "qq->WmH, H->gam*gam, W->all"
evgenConfig.description = "POWHEG+MiNLO+PYTHIA8+EVTGEN, H+Wm+jet production: H->gam*gam, gam*->ll, W->all"
evgenConfig.keywords    = [ "SM", "Higgs", "SMHiggs", "mH125", "2lepton","photon" ]
evgenConfig.contact     = [ 'amorley@cern.ch' ]
evgenConfig.inputfilecheck = 'TXT' 
evgenConfig.minevents = 500

#--------------------------------------------------------------
# Pythia8 Powheg update
#--------------------------------------------------------------
genSeq.Pythia8.Commands += [ 'Powheg:NFinal = 3' ]

#--------------------------------------------------------------
# Higgs at Pythia8
#--------------------------------------------------------------
genSeq.Pythia8.Commands += [ '25:onMode = off', # decay of Higgs
                             '25:onIfMatch = 22 22',
                             'TimeShower:mMaxGamma  90',         #Increase maximum allowed gamma* mass -n.b no interferece between gamma * and Z)
                             'TimeShower:nGammaToQuark = 0',     #Turn off gamma* to quarks
                             'TimeShower:nGammaToLepton = 2']    #Turn off gamma* to taus
                             
#Repeat time showers in Pythia8 to improve efficiency
from Pythia8_i.Pythia8_iConf import HllgamRepeatTimeShower
hllgamRepeatTimeShower = HllgamRepeatTimeShower( name = "HllgamRepeatTimeShower" ) 
ToolSvc += hllgamRepeatTimeShower
genSeq.Pythia8.CustomInterface = hllgamRepeatTimeShower
