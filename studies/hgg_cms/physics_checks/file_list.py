"""
Fixed, documented list of remote files read by the Phase 2.2 follow-up
physics checks (A, B, C). Every URL and the exact event range read from
it is recorded here once, so every check script reads the identical files
in the identical order -- reproducibility, and an explicit record of
exactly what was read against the task's file/event limits.

Limits (per task): up to 50,000 events from at most 5 files of the
postVFP ggH signal sample; up to 50,000 events from at most 5 DoubleEG
Run2016G/H data files. Actual usage below: 1 signal file (50,000 events),
2 data files (25,000 events each = 50,000 total) -- well within both
limits, chosen for simplicity and reproducibility over spreading across
more files.
"""

SIGNAL_FILES = [
    {
        "url": ("https://opendata.cern.ch/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/"
                "GluGluHToGG_M-125_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/"
                "106X_mcRun2_asymptotic_v17-v1/40000/3231834B-7A6E-4840-8627-C97FDCF67268.root"),
        "entry_start": 0,
        "entry_stop": 50_000,
        "record": 37350,
    },
]

DATA_FILES = [
    {
        "url": ("https://opendata.cern.ch/eos/opendata/cms/Run2016G/DoubleEG/NANOAOD/"
                "UL2016_MiniAODv2_NanoAODv9-v1/100000/11DA657F-5262-BD4A-AD1E-8E53BE62A601.root"),
        "entry_start": 0,
        "entry_stop": 25_000,
        "record": 30521,
        "era": "Run2016G",
    },
    {
        "url": ("https://opendata.cern.ch/eos/opendata/cms/Run2016H/DoubleEG/NANOAOD/"
                "UL2016_MiniAODv2_NanoAODv9-v1/100000/2AD46B56-E1CA-CD44-B30D-C57FE1C35D15.root"),
        "entry_start": 0,
        "entry_stop": 25_000,
        "record": 30554,
        "era": "Run2016H",
    },
]
