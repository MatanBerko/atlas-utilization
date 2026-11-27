#--------------------------------------------------------------
# POWHEG+MiNLO+Pythia8 H+Z+jet-> Zgam + inc production
#--------------------------------------------------------------
evgenConfig.inputfilecheck = 'TXT'
#runArgs.inputGeneratorFile = '/afs/cern.ch/work/c/cbecot/private/HGam/TestJobOptions/HGamMCValidation/tmpLHEfiles_forChecks/mc15_13TeV.345038.PowhegPythia8EvtGen_NNPDF30_AZNLO_ZH125J_Zincl_MINLO.evgen.TXT.e5590/TXT.10226849._020718.tar.gz.1'
 
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
                             '23:onIfAny = 11 13 15' ]
 
#--------------------------------------------------------------
# EVGEN configuration
#--------------------------------------------------------------
evgenConfig.description = "POWHEG+MiNLO+Pythia8 H+Z+jet production: Z->all, H->Zgam"
evgenConfig.keywords    = [ "SM", "Higgs", "SMHiggs", "mH125" , "ZHiggs" ]
evgenConfig.contact     = [ 'cyril.becot@cern.ch' ]
evgenConfig.process = "qq->ZH, H->Zgam, Z->all"
evgenConfig.minevents   = 100
