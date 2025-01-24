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

        #! ----------------------- Overlap cleaning ---------------------#
        Define("_DiElectronOverlapMask","!Take(Electron_isPFoverlap,DiElectron_l1idx) && !Take(Electron_isPFoverlap,DiElectron_l2idx)"),
        DefineSkimmedCollection("DiElectron", "DiElectron", mask="_DiElectronOverlapMask", redefine = True),

        #! -------------------------- Matching ------------------------- #
        Cut("nDiEle", "nDiElectron>0"),

        Define("Electron_dRgen1", "dR(Electron_eta, GenEle_eta[0], Electron_phi, GenEle_phi[0])"),
        Define("Electron_dRgen2", "dR(Electron_eta, GenEle_eta[1], Electron_phi, GenEle_phi[1])"),
        Define("Electron_dPtgen1", "abs(Electron_pt-GenEle_pt[0])/Electron_pt"),
        Define("Electron_dPtgen2", "abs(Electron_pt-GenEle_pt[1])/Electron_pt"),
        Define("Electron_dVtxgen1", "deltaVtx(Electron_vx, Electron_vy, Electron_vz, GenEle_vx[0], GenEle_vy[0], GenEle_vz[0])"),
        Define("Electron_dVtxgen2", "deltaVtx(Electron_vx, Electron_vy, Electron_vz, GenEle_vx[1], GenEle_vy[1], GenEle_vz[1])"),
        Define("DiElectron_dVtx", "deltaVtx(DiElectron_sv_x, DiElectron_sv_y, DiElectron_sv_z, GenEle_vx[0], GenEle_vy[0], GenEle_vz[0])"),
        Define("DiElectron_matchInfo", "SOS_matching(DiElectron_l1idx, DiElectron_l2idx, DiElectron_dVtx, Electron_dRgen1, Electron_dRgen2, Electron_dPtgen1, Electron_dPtgen2)"),

        #! MATCHING AFTER OVERLAP REMOVAL
        DefineSkimmedCollection("MatchedDiEle", "DiElectron", mask="DiElectron_matchInfo.match"),
        Cut("1MatchedDiEle", "nMatchedDiEle>0", plot="GenMatching"),

        #! --------------------------- pair type cut ---------------------------- #
        cutpair,
        Cut(f"1DiEle{pair}", f"n{pair}MatchedDiEle>0", plot=f"{pair}"),
        ],
    )
