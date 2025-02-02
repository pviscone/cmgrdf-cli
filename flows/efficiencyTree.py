from flows import Tree
from CMGRDF import Define, Cut

from CMGRDF.collectionUtils import DefineSkimmedCollection, DefineP4, DefineFromCollection

hlt_or="""HLT_DoubleEle4_eta1p22_mMax6 ||
HLT_DoubleEle4p5_eta1p22_mMax6 ||
HLT_DoubleEle5_eta1p22_mMax6   ||
HLT_DoubleEle5p5_eta1p22_mMax6 ||
HLT_DoubleEle6_eta1p22_mMax6   ||
HLT_DoubleEle7_eta1p22_mMax6   ||
HLT_DoubleEle7p5_eta1p22_mMax6 ||
HLT_DoubleEle8_eta1p22_mMax6   ||
HLT_DoubleEle8p5_eta1p22_mMax6 ||
HLT_DoubleEle9_eta1p22_mMax6   ||
HLT_DoubleEle9p5_eta1p22_mMax6 ||
HLT_DoubleEle10_eta1p22_mMax6"""

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
                DiElectron_fitted_mass>0 &&
                DiElectron_lep_deltaR > 0.05
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
            Define("GenZd_invMass","(GenEle_p4[0]+GenEle_p4[1]).mass()"),
            Define("GenZd_invPt","(GenEle_p4[0]+GenEle_p4[1]).pt()"),
            Define("GenZd_dR","ROOT::VecOps::DeltaR(GenEle_eta[0],GenEle_eta[1],GenEle_phi[0],GenEle_phi[1])"),
            Cut("noCut", "1",  plot="NoCut")
        ]

    tree = Tree()
    tree.add("base", main_flow)
    tree.add("HLTOR_All", Cut("HLT_All", hlt_or, plot="HLT_All"), parent="base")
    tree.add("NotHLTOR_All", Cut("NotHLT_All", f"!({hlt_or})"), parent="base")

    tree.add("matching", [
        Cut("nDiEle", "nDiElectron>0"),
        #! --------------------- Pair type collections -------------------#
        DefineSkimmedCollection("PFPFMatchedDiEle", "MatchedDiEle",mask = "MatchedDiEle_isPFPF"),
        DefineSkimmedCollection("PFLPMatchedDiEle", "MatchedDiEle",mask = "MatchedDiEle_isPFLP"),
        DefineSkimmedCollection("LPLPMatchedDiEle", "MatchedDiEle",mask = "MatchedDiEle_isLPLP"),
        DefineFromCollection("SelectedDiEle", "MatchedDiEle", index="ROOT::VecOps::ArgMin(ROOT::VecOps::pow(MatchedDiEle_fitted_mass-GenZd_invMass,2)/MatchedDiEle_fitted_massErr)"),
        Cut("1MatchedDiEle", "nMatchedDiEle>0", plot="GenMatch")
    ], parent="base")

    tree.add("PFPF",[
        Cut("PFPFgeq1", "nPFPFDiEle>0"),
        Cut("PFPFmatchgeq1", "nPFPFMatchedDiEle>0"),
        Cut("SelPFPF", "SelectedDiEle_isPFPF", plot="SelPFPF")
    ], parent="matching")

    tree.add("PFLP",[
        Cut("PFLPgeq1", "nPFLPDiEle>0"),
        Cut("PFLPmatchgeq1", "nPFLPMatchedDiEle>0"),
        Cut("SelPFLP", "SelectedDiEle_isPFLP", plot="SelPFLP")
    ], parent="matching")

    tree.add("LPLP",[
        Cut("LPLPgeq1", "nLPLPDiEle>0"),
        Cut("LPLPmatchgeq1", "nLPLPMatchedDiEle>0"),
        Cut("SelLPLP", "SelectedDiEle_isLPLP", plot="SelLPLP")
    ], parent="matching")

    tree.add("{leaf}_postSelectionCuts",
        [
        Cut("dZ", "SelectedDiEle_lep_deltaVz<1", plot="dZ"),
        Cut("QF", "SelectedDiEle_sv_prob>1.e-5 && SelectedDiEle_sv_chi2<998.", plot="QF"),
        Cut("HLT", hlt_or, plot="HLT"),
        Cut("TrgObjMatch", "Electron_isTriggering[SelectedDiEle_l1idx] && Electron_isTriggering[SelectedDiEle_l2idx]", plot="TrgObjMatch")
        ], parent=["PFPF", "PFLP", "LPLP"]
    )

    return tree


