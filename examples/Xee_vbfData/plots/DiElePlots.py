from plots import base_defaults
from cmgrdf_cli.plots import Hist, Hist2D

plots= {
    "DiElectrons":[
        Hist("nJet50", "Sum(Jet_pt>50)"),
        Hist("nDiElectron", "nDiElectron"),
        Hist("nPFPFDiEle", "Sum(DiElectron_isPFPF)"),
        Hist("nPFLPDiEle", "Sum(DiElectron_isPFLP)"),
        Hist("nLPLPDiEle", "Sum(DiElectron_isLPLP)"),
        Hist("DiElectron_type", "DiElectron_type"),
        Hist("DiElectron_fitted_mass", "DiElectron_fitted_mass"),
        Hist("DiElectron_fitted_normMass", "DiElectron_fitted_mass")
    ]
}
