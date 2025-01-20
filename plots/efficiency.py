from plots import Hist


plots= {
    "1MatchedDiEle":[
        Hist("leadEle_pt", "Electron_pt[MatchedDiEle_l1idx[0]]",),
    ],

    "1PFPFdiele": [
        Hist("leadEle_pt", "Electron_pt[PFPFMatchedDiEle_l1idx[0]]",),
    ],
    "main":[
        Hist("GenEleLead_pt", "Max(GenEle_pt)",),
        Hist("GenEleSubLead_pt", "Min(GenEle_pt)",),
    ]
}