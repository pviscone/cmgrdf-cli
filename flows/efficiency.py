from CMGRDF import Flow, Define, Cut

from CMGRDF.collectionUtils import DefineSkimmedCollection, DefineP4


def flow(pair="PFPF"):
    if pair == "PFPF":
        cutpair = DefineSkimmedCollection(f"{pair}MatchedDiEle", "MatchedDiEle",
                mask = "Take(Electron_isPF, MatchedDiEle_l1idx) && Take(Electron_isPF, MatchedDiEle_l2idx)"
                )
    elif pair == "lowPtlowPt":
        cutpair = DefineSkimmedCollection(f"{pair}MatchedDiEle", "MatchedDiEle",
                mask = "Take(Electron_isLowPt, MatchedDiEle_l1idx) && Take(Electron_isLowPt, MatchedDiEle_l2idx) "
                )
    elif pair == "PFlowPt":
        cutpair = DefineSkimmedCollection(f"{pair}MatchedDiEle", "MatchedDiEle",
                mask = "(Take(Electron_isLowPt, MatchedDiEle_l1idx) && Take(Electron_isPF, MatchedDiEle_l2idx)) || (Take(Electron_isPF, MatchedDiEle_l1idx) && Take(Electron_isLowPt, MatchedDiEle_l2idx))"
                )

    return Flow(
        "efficiency",
        [
        #! ---------------------- Gen definition ---------------------- #
        DefineSkimmedCollection("GenZd", "GenPart", mask="GenPart_pdgId==32 && (GenPart_statusFlags & (1<<13)) && (GenPart_statusFlags & 1<<8)"),
        DefineSkimmedCollection("GenEle", "GenPart", mask="abs(GenPart_pdgId)==11 && (GenPart_statusFlags & 1<<13) && (GenPart_statusFlags & 1<<8)"),

        #! ------------------------ SanityChecks ----------------------- #
        Cut("1GenZd", "nGenZd==1"),
        Cut("2GenEle", "nGenEle==2"),

        #! --------------------------- GenZd reco ---------------------- #
        DefineP4("GenEle"),
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

        #! --------------------------- pair type cut ---------------------------- #
        cutpair,
        Cut(f"1DiEle{pair}", f"n{pair}MatchedDiEle>0", plot=f"{pair}"),
        ],
    )
