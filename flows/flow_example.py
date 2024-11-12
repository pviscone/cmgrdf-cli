from CMGRDF import Flow, Define, Cut, AddWeight, AddWeightUncertainty
from CMGRDF.collectionUtils import DefineP4
from flows.SFs.electronSS import electronSmearing
from flows.SFs.electronID import electronID

from CMGRDF.collectionUtils import DefineSkimmedCollection

flow = Flow(
    "example",
    [
    #! Branch corrections and variations
    DefineSkimmedCollection("Wp90Ele", "Electron", mask="Electron_PFEleMvaID_Fall17NoIsoV2wp90==1", members=["pt", "eta", "phi", "r9"]),
    electronSmearing("Electron_smearing", "Wp90Ele_pt", "Wp90Ele_eta", "Wp90Ele_r9"),

    #! Object selection and definitions
    Define("diele_trigger_mask", "Take(Electron_isTriggering, DiElectron_l1idx) * Take(Electron_isTriggering, DiElectron_l2idx)"),
    Define("diele_mass_triggered", "DiElectron_mass[diele_trigger_mask]"),
    Define("diele_PFPF_mask", "Take(Electron_isPF, DiElectron_l1idx) * Take(Electron_isPF, DiElectron_l2idx)"),
    Define("diele_LPPF_mask", "(Take(Electron_isPF, DiElectron_l1idx) * Take(Electron_isLowPt, DiElectron_l2idx)) + (Take(Electron_isLowPt, DiElectron_l1idx) * Take(Electron_isPF, DiElectron_l2idx))"),
    Define("diele_PFPF_mass", "DiElectron_mass[diele_PFPF_mask * diele_trigger_mask]"),
    Define("diele_LPPF_mass", "DiElectron_mass[diele_LPPF_mask * diele_trigger_mask]"),


    #! Cut flow
    Cut("2wp90PFEle","nWp90Ele >= 2"),

    #! Event weights/syst
    electronID("electronIDSF_wp90noiso_", "wp90noiso", "Wp90Ele_eta", "Wp90Ele_pt", "Wp90Ele_phi"),
    AddWeightUncertainty("lumi", "1.016")
    ],
)
