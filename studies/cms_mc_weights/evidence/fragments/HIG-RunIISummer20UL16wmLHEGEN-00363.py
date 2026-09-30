import FWCore.ParameterSet.Config as cms

externalLHEProducer = cms.EDProducer("ExternalLHEProducer",
    args = cms.vstring('/cvmfs/cms.cern.ch/phys_generator/gridpacks/2017/13TeV/mcfm/MCFM_mdata_MCFM_JHUGen_13TeV_ggZZtoELMU_BKG_NNPDF31/v5/MCFM_mdata_slc6_amd64_gcc630_CMSSW_9_3_0_MCFM_JHUGen_13TeV_ggZZtoELMU_BKG_NNPDF31.tgz'),
    nEvents = cms.untracked.uint32(5000),
    numberOfParameters = cms.uint32(1),
    outputFile = cms.string('cmsgrid_final.lhe'),
    scriptName = cms.FileInPath('GeneratorInterface/LHEInterface/data/run_generic_tarball_cvmfs.sh')
)

# Link to cards:
# https://raw.githubusercontent.com/cms-sw/genproductions/a8ea4bc76df07ee2fa16bd9a67b72e7b648dec64/bin/MCFM/cards/MCFM+JHUGen/MCFM_JHUGen_13TeV_ggZZtoELMU_BKG_NNPDF31.DAT
# https://raw.githubusercontent.com/cms-sw/genproductions/a8ea4bc76df07ee2fa16bd9a67b72e7b648dec64/bin/MCFM/ACmdataConfig.py
#    --coupling 0PM --bsisigbkg BKG

import FWCore.ParameterSet.Config as cms

from Configuration.Generator.Pythia8CommonSettings_cfi import *
from Configuration.Generator.MCTunes2017.PythiaCP5Settings_cfi import *
from Configuration.Generator.PSweightsPythia.PythiaPSweightsSettings_cfi import *

generator = cms.EDFilter("Pythia8HadronizerFilter",
    maxEventsToPrint = cms.untracked.int32(1),
    pythiaPylistVerbosity = cms.untracked.int32(1),
    filterEfficiency = cms.untracked.double(1.0),
    pythiaHepMCVerbosity = cms.untracked.bool(False),
    comEnergy = cms.double(13000.),
    PythiaParameters = cms.PSet(
        pythia8CommonSettingsBlock,
        pythia8CP5SettingsBlock,
        pythia8PSweightsSettingsBlock,
        processParameters = cms.vstring(
            'SpaceShower:pTmaxMatch = 1',
            'TimeShower:pTmaxMatch = 1',
            'SpaceShower:pTmaxFudge = 1',
            'TimeShower:pTmaxFudge = 1',
        ),
        parameterSets = cms.vstring('pythia8CommonSettings',
                                    'pythia8CP5Settings',
                                    'pythia8PSweightsSettings',
                                    'processParameters',
                                    )
    )
)



# Link to generator fragment:
# https://raw.githubusercontent.com/cms-sw/genproductions/20f59357146e08e48132cfd73d0fd72ca08b6b30/python/ThirteenTeV/Hadronizer/Hadronizer_TuneCP5_13TeV_pTmaxMatch_1_LHE_pythia8_cff.py
