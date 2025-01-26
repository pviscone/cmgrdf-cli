from flows import Tree
from CMGRDF import Define, Cut

from CMGRDF.collectionUtils import DefineSkimmedCollection, DefineP4

main_flow = [
        #! ---------------------- Gen definition ---------------------- #
        DefineSkimmedCollection("GenZd", "GenPart", mask="GenPart_pdgId==32 && (GenPart_statusFlags & (1<<13)) && (GenPart_statusFlags & 1<<8)"),
        DefineSkimmedCollection("GenEle", "GenPart", mask="abs(GenPart_pdgId)==11 && (GenPart_statusFlags & 1<<13) && (GenPart_statusFlags & 1<<8)"),
        DefineP4("GenEle"),
        DefineP4("Electron"),

        #! ------------------------ SanityChecks ----------------------- #
        Cut("1GenZd", "nGenZd==1"),
        Cut("2GenEle", "nGenEle==2"),
        Cut("SameGenVtx", "deltaVtx(GenEle_vx[0],GenEle_vy[0],GenEle_vz[0], GenEle_vx[1],GenEle_vy[1],GenEle_vz[1])<0.001"),

        #! --------------------------- GenZd reco ---------------------- #
        Define("GenZd_invMass","(GenEle_p4[0]+GenEle_p4[1]).mass()"),
        Define("GenZd_invPt","(GenEle_p4[0]+GenEle_p4[1]).pt()"),
        Cut("noCut", "1",  plot="NoCut"),

        #! -------------------------- Matching ------------------------- #
        Cut("nDiEle", "nDiElectron>0"),
        Define("Electron_matchMask1", "match_mask(Electron_eta, Electron_phi, GenEle_eta[0], GenEle_phi[0])"),
        Define("Electron_matchMask2", "match_mask(Electron_eta, Electron_phi, GenEle_eta[1], GenEle_phi[1])"),
        DefineSkimmedCollection("MatchedDiEle", "DiElectron",
            mask="""
            !Take(Electron_isPFoverlap,DiElectron_l1idx) && !Take(Electron_isPFoverlap,DiElectron_l2idx) &&
            (
                (Take(Electron_matchMask1,DiElectron_l1idx) && Take(Electron_matchMask2,DiElectron_l2idx)) ||
                (Take(Electron_matchMask2,DiElectron_l1idx) && Take(Electron_matchMask1,DiElectron_l2idx))
            )"""),
        Cut("1MatchedDiEle", "nMatchedDiEle>0", plot="GenMatching"),
    ]

flow = Tree()
flow.add("matching", main_flow)
flow.add("PFPF",
    DefineSkimmedCollection("PairTypeMatchedDiEle", "MatchedDiEle",
        mask = "Take(Electron_isPF, MatchedDiEle_l1idx) && Take(Electron_isPF, MatchedDiEle_l2idx)"),
    parent="matching"
)
flow.add("lowPtlowPt",
    DefineSkimmedCollection("PairTypeMatchedDiEle", "MatchedDiEle",
        mask = "Take(Electron_isLowPt, MatchedDiEle_l1idx) && Take(Electron_isLowPt, MatchedDiEle_l2idx) "),
    parent="matching"
)
flow.add("PFlowPt",
    DefineSkimmedCollection("PairTypeMatchedDiEle", "MatchedDiEle",
        mask = "(Take(Electron_isLowPt, MatchedDiEle_l1idx) && Take(Electron_isPF, MatchedDiEle_l2idx)) || (Take(Electron_isPF, MatchedDiEle_l1idx) && Take(Electron_isLowPt, MatchedDiEle_l2idx))"),
    parent="matching"
)
flow.add_to_all("1PairType",Cut("1DiElePairType", "nPairTypeMatchedDiEle>0", plot="pairtype"))
