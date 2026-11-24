evgenConfig.description = "Sherpa Z/gamma* -> tautau + 0,1,2j@NLO + 3,4,5j@LO & 10<mZ<40 GeV with light-jet filter taking input from existing unfiltered input file."
evgenConfig.keywords = ["SM", "Z", "tau", "jets", "NLO" ]
evgenConfig.contact  = [ "atlas-generators-sherpa@cern.ch", "matthew.gignac@cern.ch" ]
evgenConfig.nEventsPerJob = 50000
evgenConfig.inputFilesPerJob = 8 

if runArgs.trfSubstepName == 'generate' :
   print("ERROR: These JO require an input file.  Please use the --afterburn option")
 
if runArgs.trfSubstepName == 'afterburn':
   evgenConfig.generators += ["Sherpa"]
 
   ## Loop removal should not be necessary anymore with HEPMC_TREE_LIKE=1 below
   if hasattr(testSeq, "FixHepMC"):
      fixSeq.FixHepMC.LoopsByBarcode = False
 
   ## Disable TestHepMC for the time being, cf.  
   ## https://its.cern.ch/jira/browse/ATLMCPROD-1862
   if hasattr(testSeq, "TestHepMC"):
      testSeq.remove(TestHepMC())

   include("GeneratorFilters/FindJets.py")
   CreateJets(prefiltSeq, 0.4)
   include("GeneratorFilters/BHadronFilter.py")
   HeavyFlavorBHadronFilter.BottomEtaMax = 2.9
   HeavyFlavorBHadronFilter.BottomPtMin = 5*GeV
   HeavyFlavorBHadronFilter.RequireTruthJet = True
   HeavyFlavorBHadronFilter.JetPtMin = 10*GeV
   HeavyFlavorBHadronFilter.JetEtaMax = 2.9
   HeavyFlavorBHadronFilter.TruthContainerName = "AntiKt4TruthJets"
   HeavyFlavorBHadronFilter.DeltaRFromTruth = 0.4
   filtSeq += HeavyFlavorBHadronFilter

   include("GeneratorFilters/CHadronPt4Eta3_Filter.py")
   filtSeq += HeavyFlavorCHadronPt4Eta3_Filter
   filtSeq.Expression = "(not HeavyFlavorBHadronFilter) and (not HeavyFlavorCHadronPt4Eta3_Filter)"

   postSeq.CountHepMC.CorrectRunNumber = True

