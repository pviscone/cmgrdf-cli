from CMGRDF import Flow, Define, Cut
from CMGRDF.collectionUtils import DefineP4

flow = Flow(
    "example",
    [
    Define("diele_trigger_mask", "Take(Electron_isTriggering, DiElectron_l1idx) * Take(Electron_isTriggering, DiElectron_l2idx)"),
    Define("diele_mass_triggered", "DiElectron_mass[diele_trigger_mask]"),
    Define("diele_PFPF_mask", "Take(Electron_isPF, DiElectron_l1idx) * Take(Electron_isPF, DiElectron_l2idx)"),
    Define("diele_LPPF_mask", "(Take(Electron_isPF, DiElectron_l1idx) * Take(Electron_isLowPt, DiElectron_l2idx)) + (Take(Electron_isLowPt, DiElectron_l1idx) * Take(Electron_isPF, DiElectron_l2idx))"),
    Define("diele_PFPF_mass", "DiElectron_mass[diele_PFPF_mask * diele_trigger_mask]"),
    Define("diele_LPPF_mass", "DiElectron_mass[diele_LPPF_mask * diele_trigger_mask]"),
    ],
)
