from plots import Hist


plots= {
    "main":[
        Hist("GenEleLead_pt", "Max(GenEle_pt)",),
        Hist("GenEleSubLead_pt", "Min(GenEle_pt)",),
        Hist("GenEleLead_eta", "GenEle_eta[0]",),
        Hist("GenEleSubLead_eta", "GenEle_eta[1]",),
        Hist("GenZd_invMass", "GenZd_invMass",),
        Hist("GenZd_invPt", "GenZd_invPt",),
        Hist("GenZd_mass", "GenZd_mass",),
    ]
}