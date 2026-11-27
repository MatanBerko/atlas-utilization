#--------------------------------------------------------------
# POWHEG+MiNLO+Pythia8 W+H125+jet->WincH Zgam production
#--------------------------------------------------------------
evgenConfig.inputfilecheck = 'TXT'
#runArgs.inputGeneratorFile = '/afs/cern.ch/work/c/cbecot/private/HGam/TestJobOptions/HGamMCValidation/tmpLHEfiles_forChecks/mc15_13TeV.345040.PowhegPythia8EvtGen_NNPDF30_AZNLO_WmH125J_Wincl_MINLO.evgen.TXT.e5590_tid10226854_00/TXT.10226854._000741.tar.gz.1'

 
#--------------------------------------------------------------
# Pythia8 showering
#--------------------------------------------------------------
include('MC15JobOptions/Pythia8_AZNLO_CTEQ6L1_EvtGen_Common.py')

#--------------------------------------------------------------
# Pythia8 main31 matching
#-------------------------------------------------------------- 
genSeq.Pythia8.UserModes += [ 'Main31:NFinal = 3']

#--------------------------------------------------------------
# H->ZZ->4l decay
#--------------------------------------------------------------
genSeq.Pythia8.Commands += [ '25:onMode = off', # decay of Higgs
                             '25:onIfMatch = 22 23',
                             '23:onMode = off',
                             '23:onIfAny = 11 13 15']
 
#--------------------------------------------------------------
# EVGEN configuration
#--------------------------------------------------------------
evgenConfig.description = "POWHEG+MiNLO+Pythia8 H+Wm+jet->Zgam+all production"
evgenConfig.keywords    = [ "SM", "Higgs", "SMHiggs", "mH125"  ]
evgenConfig.contact     = [ 'cyril.becot@cern.ch' ]
evgenConfig.process = "qq->WmH, H->Zgam, W->all"
evgenConfig.minevents   = 500
 
