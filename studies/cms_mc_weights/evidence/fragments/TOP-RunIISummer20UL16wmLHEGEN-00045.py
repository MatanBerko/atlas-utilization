import FWCore.ParameterSet.Config as cms

externalLHEProducer = cms.EDProducer("ExternalLHEProducer",
    args = cms.vstring('/cvmfs/cms.cern.ch/phys_generator/gridpacks/UL/13TeV/powheg/V2/st_tW_5f_dr_ckm_13TeV/ST_wtch_DR_slc6_amd64_gcc630_CMSSW_9_3_0_my_ST_tW_DR_5f_ckm_antitop_13TeV_UL.tgz'),
    nEvents = cms.untracked.uint32(5000),
    numberOfParameters = cms.uint32(1),
    outputFile = cms.string('cmsgrid_final.lhe'),
    scriptName = cms.FileInPath('GeneratorInterface/LHEInterface/data/run_generic_tarball_cvmfs.sh')
)

#Link to datacards:
#https://github.com/cms-sw/genproductions/blob/master/bin/Powheg/production/2017/13TeV/st_tW_5f_dr_ckm_13TeV/ST_tW_DR_5f_ckm_antitop_13TeV_UL.input

from Configuration.Generator.Pythia8CommonSettings_cfi import *
from Configuration.Generator.MCTunes2017.PythiaCP5Settings_cfi import *
from Configuration.Generator.Pythia8PowhegEmissionVetoSettings_cfi import *
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
pythia8PowhegEmissionVetoSettingsBlock,
pythia8PSweightsSettingsBlock,
        processParameters = cms.vstring(
            'POWHEG:nFinal = 2',   ## Number of final state particles
                                   ## (BEFORE THE DECAYS) in the LHE
                                   ## other than emitted extra parton
          ),
parameterSets = cms.vstring('pythia8CommonSettings',
                            'pythia8PowhegEmissionVetoSettings',
							'pythia8CP5Settings',
                            'pythia8PSweightsSettings',
							'processParameters'
)
)
)
lheGenericFilter = cms.EDFilter("LHEGenericFilter",
    src = cms.InputTag("externalLHEProducer"),
    NumRequired = cms.int32(0),
    ParticleID = cms.vint32(11,13,15),
    AcceptLogic = cms.string("GT") # LT meaning < NumRequired, GT >, EQ =, NE !=
)  
ProductionFilterSequence = cms.Sequence(lheGenericFilter+generator)