import FWCore.ParameterSet.Config as cms

externalLHEProducer = cms.EDProducer("ExternalLHEProducer",
    args = cms.vstring('/cvmfs/cms.cern.ch/phys_generator/gridpacks/2017/13TeV/jhugen/V7011/ggZH_ZZ_NNPDF31_13TeV/ggZH_ZZ4l_NNPDF31_13TeV_M125/v1/ggZH_ZZ4l_NNPDF31_13TeV_M125.tgz'),
    nEvents = cms.untracked.uint32(5000),
    numberOfParameters = cms.uint32(1),
    outputFile = cms.string('cmsgrid_final.lhe'),
    scriptName = cms.FileInPath('GeneratorInterface/LHEInterface/data/run_generic_tarball_cvmfs.sh')
)

# Link to cards:
# https://raw.githubusercontent.com/cms-sw/genproductions/20ac197949817a9bc02aa346f3fe23d157371b74/bin/JHUGen/cards/2017/13TeV/ggZH_NNPDF31_13TeV/ggZH_NNPDF31_13TeV_M125.input
# https://raw.githubusercontent.com/cms-sw/genproductions/20ac197949817a9bc02aa346f3fe23d157371b74/bin/JHUGen/cards/decay/ZZ2l2any_withtaus_filter4l.input

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
            'SpaceShower:pTmaxFudge = .5',
            'TimeShower:pTmaxFudge = .5',
        ),
        parameterSets = cms.vstring('pythia8CommonSettings',
                                    'pythia8CP5Settings',
                                    'pythia8PSweightsSettings',
                                    'processParameters',
                                    )
    )
)



# Link to generator fragment:
# https://raw.githubusercontent.com/cms-sw/genproductions/20ac197949817a9bc02aa346f3fe23d157371b74/python/ThirteenTeV/Hadronizer/Hadronizer_TuneCP5_13TeV_pTmaxMatch_1_pTmaxFudge_half_LHE_pythia8_cff.py
