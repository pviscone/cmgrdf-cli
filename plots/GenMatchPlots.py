#! To run with:
# - flows/DoubleEleFlow_baseline_GenMatch.py
from plots import Hist, Hist2D

plots= {
    "main":[
        Hist("GenEleLead_pt", "Max(GenEle_pt)",),
        Hist("GenEleSubLead_pt", "Min(GenEle_pt)",),
        Hist("GenEleLead_eta", "GenEle_eta[ROOT::VecOps::ArgMax(GenEle_pt)]",),
        Hist("GenEleSubLead_eta", "GenEle_eta[ROOT::VecOps::ArgMin(GenEle_pt)]",),
        Hist("GenZd_invMass", "GenZd_invMass",),
        Hist("GenZd_mass", "GenZd_mass",),
        Hist("GenZd_dR", "GenZd_dR",),
        Hist("nJet15", "Jet_pt[Jet_pt>15].size()"),
        Hist("nJet30", "Jet_pt[Jet_pt>30].size()"),
        Hist("nMatchedDiEle", "nMatchedDiEle"),
        Hist("nDiElectron", "nDiElectron"),
        Hist("nPFPFDiEle", "nPFPFDiEle"),
        Hist("nPFLPDiEle", "nPFLPDiEle"),
        Hist("nLPLPDiEle", "nLPLPDiEle"),
        Hist("DiElectron_type", "DiElectron_type"),
        Hist("MatchedDiEle_type", "MatchedDiEle_type"),
        Hist("nLHEJets","nLHEJets"),
        Hist2D("GenZd_invPt:GenZd_dR", "GenZd_invPt", "GenZd_dR"),
        Hist2D("GenEleLead_pt:GenZd_dR", "Max(GenEle_pt)", "GenZd_dR"),
        Hist2D("GenEleSubLead_pt:GenZd_dR", "Min(GenEle_pt)", "GenZd_dR"),
        Hist2D("GenEleLead_pt:GenEleSubLead_pt", "Max(GenEle_pt)", "Min(GenEle_pt)"),

    ],
    "GenMatch":[
        Hist("SelectedDiEle_fitted_mass", "SelectedDiEle_fitted_mass"),
        Hist("SelectedDiEle_pt", "SelectedDiEle_pt"),
        Hist("SelectedDiEle_type", "SelectedDiEle_type"),
    ],
}