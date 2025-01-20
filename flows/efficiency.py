from CMGRDF import Flow, Define, Cut, AddWeightUncertainty
from flows.SFs.electronSS import electronSmearing
from flows.SFs.electronID import electronID

from CMGRDF.collectionUtils import DefineSkimmedCollection


def flow(pair="PFPF"):
    #!TODO FIx PFlowPt: Electron collection have PF-lowPt duplicates
    if pair == "PFPF":
        cutpair = DefineSkimmedCollection(f"{pair}MatchedDiEle", "MatchedDiEle", mask = "Take(Electron_isPF, MatchedDiEle_l1idx) && Take(Electron_isPF, MatchedDiEle_l2idx)")
    elif pair == "lowPtlowPt":
        cutpair = DefineSkimmedCollection(f"{pair}MatchedDiEle", "MatchedDiEle", mask = "Take(Electron_isLowPt, MatchedDiEle_l1idx) && Take(Electron_isLowPt, MatchedDiEle_l2idx)")
    elif pair == "PFlowPt":
        cutpair = DefineSkimmedCollection(f"{pair}MatchedDiEle", "MatchedDiEle", mask = "(Take(Electron_isLowPt, MatchedDiEle_l1idx) && Take(Electron_isPF, MatchedDiEle_l2idx)) || (Take(Electron_isPF, MatchedDiEle_l1idx) && Take(Electron_isLowPt, MatchedDiEle_l2idx))")



    return Flow(
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
        DefineSkimmedCollection("MatchedDiEle", "DiElectron", mask="match_mask(DiElectron_eta, DiElectron_phi, GenZd_eta[0], GenZd_phi[0])"),
        Cut("1MatchedDiEle", "nMatchedDiEle>0", plot="1MatchedDiEle"),

        #! --------------------------- pair type cut ---------------------------- #
        cutpair,
        Cut(f"1DiEle{pair}", f"n{pair}MatchedDiEle>0", plot=f"1{pair}MatchedDiEle"),
        ],
    )
