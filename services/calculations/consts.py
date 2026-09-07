"""
Centralized constants for particle physics calculations.
"""
KNOWN_MASSES = {
    "Muons": 0.105,
    "Photons": 0.0,
    "Electrons": 0.000511,
    "Jets": 0.0,
    "BJets": 0.0,
    "Taus": 1.77686,
}

# ATLAS PHYSLITE / AnalysisElectronsAuxDyn — relative isolation uses cone energy / pT
ELECTRON_REL_ISOLATION_FIELD = "ptvarcone30_Nonprompt_All_MaxWeightTTVALooseCone_pt1000"

# CMS NanoAOD photon ID fields (services/parsing/schemas.py "cms-nanoaod" schema).
# PHOTON_CUTBASED_FIELD: Photon_cutBased is a Fall17V2 cut-based ID ordinal —
# confirmed directly from the branch's own title on real UL2016 NanoAODv9 files
# (record 30521/30554): "cut-based ID bitmap, Fall17V2, (0:fail, 1:loose,
# 2:medium, 3:tight)". Only {0,1,2,3} ever appear — there is no separate
# "veto" tier for photons (unlike electron ID); loose = cutBased >= 1.
PHOTON_CUTBASED_FIELD = "cutBased"
# PHOTON_ELECTRON_VETO_FIELD: Photon_electronVeto, a plain boolean — True means
# the photon candidate passed the pixel-seed/conversion-safe electron veto,
# i.e. is not an electron misreconstructed as a photon.
PHOTON_ELECTRON_VETO_FIELD = "electronVeto"

LETTER_PARTICLE_MAPPING = {
    "e": "Electrons",
    "j": "Jets",
    "g": "Photons",
    "m": "Muons",
    "t": "Taus",
    "b": "BJets",
}
