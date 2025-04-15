from flows import Tree
from CMGRDF import Define, Cut

from CMGRDF.collectionUtils import DefineSkimmedCollection, DefineP4, DefineFromCollection

hlt = "HLT_DoubleEle6p5_eta1p22_mMax6"
l1  = "L1_DoubleEG11_er1p2_dR_Max0p6"

def flow(dR_genMatch = 0.1):
    main_flow = [
            #! ---------------------- Gen definition ---------------------- #
            DefineSkimmedCollection("GenZd", "GenPart", mask="GenPart_pdgId==32 && (GenPart_statusFlags & (1<<13)) && (GenPart_statusFlags & 1<<8)"),
            DefineSkimmedCollection("GenEle", "GenPart", mask="abs(GenPart_pdgId)==11 && (GenPart_statusFlags & 1<<13) && (GenPart_statusFlags & 1<<8)"),
            DefineP4("GenEle"),
            DefineP4("Electron"),
            Define("nLHEJets", "LHEPart_pdgId[abs(LHEPart_pdgId)!=11 && LHEPart_status==1].size()"),

            #! ------------------------ SanityChecks ----------------------- #
            Cut("1GenZd", "nGenZd==1"),
            Cut("2GenEle", "nGenEle==2"),
            Cut("SameGenVtx", "deltaVtx(GenEle_vx[0],GenEle_vy[0],GenEle_vz[0], GenEle_vx[1],GenEle_vy[1],GenEle_vz[1])<0.001"),

            #! --------------------- DiEle categorization -------------------#
            Define("_DiEle_mask","""
                !Take(Electron_isPFoverlap,DiElectron_l1idx) &&
                !Take(Electron_isPFoverlap,DiElectron_l2idx) &&
                Take(Electron_convVeto,DiElectron_l1idx) &&
                Take(Electron_convVeto,DiElectron_l2idx) &&
                (Take(Electron_charge,DiElectron_l1idx) * Take(Electron_charge,DiElectron_l2idx)) == -1 &&
                DiElectron_fitted_mass>0
                """),
            DefineSkimmedCollection("DiElectron", "DiElectron", mask="_DiEle_mask", redefine=True),
            Define("DiElectron_isPFPF", "Take(Electron_isPF, DiElectron_l1idx) && Take(Electron_isPF, DiElectron_l2idx)"),
            Define("DiElectron_isPFLP","""
                (Take(Electron_isLowPt, DiElectron_l1idx) && Take(Electron_isPF, DiElectron_l2idx)) ||
                (Take(Electron_isPF, DiElectron_l1idx) && Take(Electron_isLowPt, DiElectron_l2idx))"""
            ),
            Define("DiElectron_isLPLP", "Take(Electron_isLowPt, DiElectron_l1idx) && Take(Electron_isLowPt, DiElectron_l2idx)"),
            Define("DiElectron_type", "DiElectron_isPFPF + 2*DiElectron_isPFLP + 3*DiElectron_isLPLP"),
            Define("nPFPFDiEle", "Sum(DiElectron_isPFPF)"),
            Define("nPFLPDiEle", "Sum(DiElectron_isPFLP)"),
            Define("nLPLPDiEle", "Sum(DiElectron_isLPLP)"),

            #! ------------------------- GenMatching -------------------------#
            DefineSkimmedCollection("MatchedDiEle", "DiElectron",
                mask=f"""
                    (match_mask(DiElectron_l1_postfit_eta, DiElectron_l1_postfit_phi, GenEle_eta[0], GenEle_phi[0], {dR_genMatch}) &&
                    match_mask(DiElectron_l2_postfit_eta, DiElectron_l2_postfit_phi, GenEle_eta[1], GenEle_phi[1], {dR_genMatch})) ||
                    (match_mask(DiElectron_l1_postfit_eta, DiElectron_l1_postfit_phi, GenEle_eta[1], GenEle_phi[1], {dR_genMatch}) &&
                    match_mask(DiElectron_l2_postfit_eta, DiElectron_l2_postfit_phi, GenEle_eta[0], GenEle_phi[0], {dR_genMatch}))
                """
            ),

            #! --------------------------- GenZd reco ---------------------- #
            Define("GenZd_p4","(GenEle_p4[0]+GenEle_p4[1])"),
            Define("GenZd_dR","ROOT::VecOps::DeltaR(GenEle_eta[0],GenEle_eta[1],GenEle_phi[0],GenEle_phi[1])"),
            Cut("noCut", "1",  plot="NoCut")
        ]

    tree = Tree()
    tree.add("base", main_flow)
    tree.add("HLT", Cut("HLT", hlt, plot="HLT_6p5"), parent="base")
    tree.add("HLT_L1", Cut("HLT_L1", l1, plot="L1EG11"), parent="HLT")

    tree.add("{leaf}_RECO",[
        Cut("nDiEle", "nDiElectron>0"),
        Cut("1MatchedDiEle", "nMatchedDiEle>0"),
        #! --------------------- Pair type collections -------------------#
        DefineSkimmedCollection("PFPFMatchedDiEle", "MatchedDiEle",mask = "MatchedDiEle_isPFPF"),
        DefineSkimmedCollection("PFLPMatchedDiEle", "MatchedDiEle",mask = "MatchedDiEle_isPFLP"),
        DefineSkimmedCollection("LPLPMatchedDiEle", "MatchedDiEle",mask = "MatchedDiEle_isLPLP"),
        DefineFromCollection("SelectedDiEle", "MatchedDiEle", index="ROOT::VecOps::ArgMin(ROOT::VecOps::pow(MatchedDiEle_fitted_mass-GenZd_p4.mass(),2)/MatchedDiEle_fitted_massErr)", plot = "GenMatch"),
    ], parent=["HLT_L1", "HLT", "base"])


    for typ in ["PFPF", "PFLP", "LPLP"]:
        tree.add(typ+"_{leaf}",[
        Cut(f"{typ}geq1", f"n{typ}DiEle>0"),
        Cut(f"{typ}matchgeq1", f"n{typ}MatchedDiEle>0"),
        Cut(f"Sel{typ}", f"SelectedDiEle_is{typ}", plot=f"Sel{typ}"),
        Cut("dZ", "SelectedDiEle_lep_deltaVz<1", plot="dZ"),
        Cut("QF", "SelectedDiEle_sv_prob>1.e-5 && SelectedDiEle_sv_chi2<998.", plot="QF"),
        Cut("TrgObjMatch", "Electron_isTriggering[SelectedDiEle_l1idx] && Electron_isTriggering[SelectedDiEle_l2idx]", plot="TrgObjMatch")
        ], parent=["HLT_L1_RECO", "HLT_RECO", "base_RECO"]
        )

    return tree


