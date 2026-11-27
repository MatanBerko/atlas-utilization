#--------------------------------------------------------------
# Pythia8 showering
#--------------------------------------------------------------
include('MC15JobOptions/Pythia8_AZNLO_CTEQ6L1_EvtGen_Common.py')
include('MC15JobOptions/Pythia8_Powheg.py')

#--------------------------------------------------------------
# Pythia8 main31 matching
#--------------------------------------------------------------
if "UserHooks" in genSeq.Pythia8.__slots__.keys():
	genSeq.Pythia8.Commands  += ['Powheg:NFinal = 3']

else:
	genSeq.Pythia8.UserModes += [ 'Main31:NFinal = 3' ]
#--------------------------------------------------------------
# H->ZZ->4l decay
#--------------------------------------------------------------
genSeq.Pythia8.Commands += [ '25:onMode = off', # decay of Higgs
                             '25:onIfMatch = 23 23',
                             '23:onMode = off',
                             '23:mMin = 2.0',
                             '23:onIfAny = 11 13 15']

#--------------------------------------------------------------
# EVGEN configuration
#--------------------------------------------------------------
evgenConfig.description = "POWHEG+MiNLO+Pythia8 H+Z+jet production: Z->all, H->ZZ->4l with shower weights"
evgenConfig.keywords    = [ "SM", "Higgs", "SMHiggs", "mH125" , "ZHiggs" ]
evgenConfig.contact     = [ 'bianca.ciungu@cern.ch' ]
evgenConfig.inputfilecheck = "TXT"
evgenConfig.process = "qq->ZH, H->4l, Z->all"
evgenConfig.minevents   = 100
