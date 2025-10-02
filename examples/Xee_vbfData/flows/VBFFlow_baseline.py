from cmgrdf_cli.flows import Tree
from collections import OrderedDict

from CMGRDF import Define, Cut

from CMGRDF.collectionUtils import DefineSkimmedCollection

hlt_vbf = "HLT_VBF_DiPFJet125_45_Mjj1050 || HLT_VBF_DiPFJet125_45_Mjj1200"
hlt_vbf_gamma = "HLT_VBF_DiPFJet50_Mjj650_Photon22 || HLT_VBF_DiPFJet50_Mjj750_Photon22"
hlt_vbf_ele = "HLT_VBF_DiPFJet50_Mjj600_Ele22_eta2p1_WPTight_Gsf || HLT_VBF_DiPFJet50_Mjj650_Ele22_eta2p1_WPTight_Gsf"

blind_cut = DefineSkimmedCollection("DiElectron", mask="DiElectron_fitted_mass>2.6 && DiElectron_fitted_mass<4.2")


def flow(hlt = "full", cat = ["PFPF_ID", "PFLP", "LPLP"],):
    hlt_paths = OrderedDict()
    hlt_emu = OrderedDict()
    hlt_emu_mc = OrderedDict()
    if hlt == "full":
        hlt_paths["HLT_VBF_ALL"] = f"{hlt_vbf} || {hlt_vbf_gamma} || {hlt_vbf_ele}"
        hlt_emu["HLT_VBF_ALL"] = f"""
                inclusiveVBFemu(Jet_pt, Jet_eta, Jet_phi, Jet_mass) ||
                VBFgammaEmu(Jet_pt, Jet_eta, Jet_phi, Jet_mass) ||
                VBFeleEmu(Jet_pt, Jet_eta, Jet_phi, Jet_mass)"""
        hlt_emu_mc["HLT_VBF_ALL"] = hlt_emu["HLT_VBF_ALL"]
    elif hlt == "egamma":
        hlt_paths["HLT_VBF_Inclusive"] = f"{hlt_vbf}"
        hlt_emu["HLT_VBF_Inclusive"] = f"inclusiveVBFemu(Jet_pt, Jet_eta, Jet_phi, Jet_mass)"
        hlt_emu_mc["HLT_VBF_Inclusive"] = f"inclusiveVBFemu(Jet_pt, Jet_eta, Jet_phi, Jet_mass)"
        hlt_paths["HLT_VBF_EGamma"] = f"({hlt_vbf_gamma} || {hlt_vbf_ele}) && !({hlt_vbf})"
        hlt_emu["HLT_VBF_EGamma"] = "VBFgammaEmu(Jet_pt, Jet_eta, Jet_phi, Jet_mass) || VBFeleEmu(Jet_pt, Jet_eta, Jet_phi, Jet_mass)"
        hlt_emu_mc["HLT_VBF_EGamma"] = f"(VBFgammaEmu(Jet_pt, Jet_eta, Jet_phi, Jet_mass) || VBFeleEmu(Jet_pt, Jet_eta, Jet_phi, Jet_mass)) && !(inclusiveVBFemu(Jet_pt, Jet_eta, Jet_phi, Jet_mass))"
    elif hlt == "splitted":
        hlt_paths["HLT_VBF_Inclusive"] = f"{hlt_vbf}"
        hlt_emu["HLT_VBF_Inclusive"] = "inclusiveVBFemu(Jet_pt, Jet_eta, Jet_phi, Jet_mass)"
        hlt_emu_mc["HLT_VBF_Inclusive"] = hlt_emu["HLT_VBF_Inclusive"]
        hlt_paths["HLT_VBF_Ele"] = f"{hlt_vbf_ele} && !({hlt_vbf})"
        hlt_emu["HLT_VBF_Ele"] = "VBFeleEmu(Jet_pt, Jet_eta, Jet_phi, Jet_mass)"
        hlt_emu_mc["HLT_VBF_Ele"] = f'VBFeleEmu(Jet_pt, Jet_eta, Jet_phi, Jet_mass) && !(inclusiveVBFemu(Jet_pt, Jet_eta, Jet_phi, Jet_mass))'
        hlt_paths["HLT_VBF_Photon"] = f"{hlt_vbf_gamma} && !({hlt_vbf} || {hlt_vbf_ele})"
        hlt_emu["HLT_VBF_Photon"] = "VBFgammaEmu(Jet_pt, Jet_eta, Jet_phi, Jet_mass)"
        hlt_emu_mc["HLT_VBF_Photon"] = f'VBFgammaEmu(Jet_pt, Jet_eta, Jet_phi, Jet_mass) && !(inclusiveVBFemu(Jet_pt, Jet_eta, Jet_phi, Jet_mass) || VBFeleEmu(Jet_pt, Jet_eta, Jet_phi, Jet_mass))'


    tree = Tree()
    for hlt, path in hlt_paths.items():
        tree.add(hlt, [
            #! ------------------------ SanityChecks ----------------------- #
            blind_cut,
            Cut(hlt, path, plot=hlt, onMC=False, onDataDriven=False),

            DefineSkimmedCollection("Jet", mask="Jet_jetId & 0x2"), # Jet tight ID
            Cut("nJet>=2", "nJet>=2"),
            Cut("HLT_EMU_data", f"{hlt_emu[hlt]}", onMC=False, onDataDriven=False),
            Cut("HLT_EMU_mc", f"{hlt_emu_mc[hlt]}", plot=f"{hlt}_emu", onData=False),
        ])


    tree.add_to_all("{leaf}_main",[

            #! --------------------- DiEle categorization -------------------#
            DefineSkimmedCollection("DiElectron_l1", "Electron", indices="DiElectron_l1idx",
                    members=["charge", "isPF", "isLowPt", "pt", "eta", "phi","convVeto", "isPFoverlap","PFEleMvaID_Winter22NoIsoV1wp90"]),
            DefineSkimmedCollection("DiElectron_l2", "Electron", indices="DiElectron_l2idx",
                    members=["charge", "isPF", "isLowPt", "pt", "eta", "phi","convVeto", "isPFoverlap","PFEleMvaID_Winter22NoIsoV1wp90"]),

            DefineSkimmedCollection("DiElectron", mask="""
                            !DiElectron_l1_isPFoverlap &&
                            !DiElectron_l2_isPFoverlap &&
                            DiElectron_l1_convVeto &&
                            DiElectron_l2_convVeto &&
                            (DiElectron_l1_charge * DiElectron_l2_charge == -1) &&
                            DiElectron_fitted_mass>0
                            """),
            Define("DiElectron_isPFPF", "DiElectron_l1_isPF && DiElectron_l2_isPF"),
            Define("DiElectron_isPFLP","""
                (DiElectron_l1_isLowPt && DiElectron_l2_isPF) ||
                (DiElectron_l2_isLowPt && DiElectron_l1_isPF)"""
            ),
            Define("DiElectron_isLPLP", "DiElectron_l1_isLowPt && DiElectron_l2_isLowPt"),
            Define("DiElectron_type", "DiElectron_isPFPF + 2*DiElectron_isPFLP + 3*DiElectron_isLPLP"),
            Cut("nDiEle", "nDiElectron>0", plot="DiElectrons"),
            DefineSkimmedCollection("DiElectron", mask="DiElectron_lep_deltaVz<1"),
            Cut("dZCut", "nDiElectron>0", plot="dZCut"),
            DefineSkimmedCollection("DiElectron", mask="DiElectron_sv_prob>1.e-5 && DiElectron_sv_chi2<998."),
            Cut("QFCut", "nDiElectron>0", plot="QFCut"),
        ]
    )


    for typ in cat:

        if typ=="PFPF_ID":
            EleID=[
                DefineSkimmedCollection("DiElectron", mask=f"DiElectron_l1_pt>5 && DiElectron_l2_pt>5"),
                Cut(f"PFpt>5", "nDiElectron>0", plot="ptCut"),
                DefineSkimmedCollection("DiElectron",
                    mask="DiElectron_l1_PFEleMvaID_Winter22NoIsoV1wp90 && DiElectron_l2_PFEleMvaID_Winter22NoIsoV1wp90"),
                Cut("EleId", "nDiElectron>0", plot="IDcut")
            ]
            pair_type = "PFPF"
        else:
            pair_type = typ
            EleID=[]

        tree.add("{leaf-2}_"+typ,[
            DefineSkimmedCollection("DiElectron", mask=f"DiElectron_is{pair_type}"),
            Cut(f"{typ}Cut", "nDiElectron>0", plot=f"{typ}Cut"),
            *EleID
        ], parent=[f"{h}_main" for h in hlt_paths.keys()]
    )

    return tree


