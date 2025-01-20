from CMGRDF import Flow, Define, Cut, AddWeightUncertainty
from flows.SFs.electronSS import electronSmearing
from flows.SFs.electronID import electronID

from CMGRDF.collectionUtils import DefineSkimmedCollection

flow = Flow(
    "efficiency",
    [
    #! ---------------------- Gen definition ---------------------- #
    DefineSkimmedCollection("GenZd", "GenPart", mask="GenPart_pdgId==32 && (GenPart_statusFlags & (1<<13)) "),
    DefineSkimmedCollection("GenEle", "GenPart", mask="abs(GenPart_pdgId)==11 && (GenPart_statusFlags & 1<<13) && (GenPart_statusFlags & 1<<8)"),

    #! ------------------------ SanityChecks ----------------------- #
    Cut("1GenZd", "nGenZd==1"),
    Cut("2GenEle", "nGenEle==2", plot="NoCut"),

    #! -------------------------- Matching ------------------------- #
    Cut("nDiEle", "nDiElectron>0"),
    DefineSkimmedCollection("MatchedDiEle", "DiElectron", mask="match_mask(DiElectron_pt, DiElectron_eta, DiElectron_phi, GenZd_pt[0], GenZd_eta[0], GenZd_phi[0])"),
    Cut("1MatchedDiEle", "nMatchedDiEle==1", plot="1MatchedDiEle"),

    #! --------------------------- PFPF ---------------------------- #
    DefineSkimmedCollection("PFPFMatchedDiEle", "MatchedDiEle", mask = "Take(Electron_isPF, MatchedDiEle_l1idx) && Take(Electron_isPF, MatchedDiEle_l2idx)"),
    Cut("1DiElePFPF", "nPFPFMatchedDiEle>0", plot="1PFPFMatchedDiEle"),
    ],
)
