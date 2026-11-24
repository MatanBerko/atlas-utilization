include('MC15JobOptions/MadGraphControl_tHjb_NLO.py')

genSeq.Pythia8.Commands += [
    '25:onMode = off', # switch OFF all Higgs decay channels
    '25:onIfMatch = 22 22' # H -> gamma gamma
]

evgenConfig.inputconfcheck = "tHjb"
