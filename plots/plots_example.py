from plots import Hist

plots=[
    Hist("diele_mass_all"       , "DiElectron_mass",),
    Hist("diele_mass_triggered" , "diele_mass_triggered",),
    Hist("diele_mass_PFPF"      , "diele_PFPF_mass",),
    Hist("diele_mass_LPPF"      , "diele_LPPF_mass",),
    Hist("Electron_pt"          , "Electron_pt",),
    Hist("Wp90Ele_pt"           , "Wp90Ele_pt",),
]

plots={
    "main":[
    Hist("diele_mass_all"       , "DiElectron_mass",),
    Hist("diele_mass_triggered" , "diele_mass_triggered",),
    Hist("diele_mass_PFPF"      , "diele_PFPF_mass",),
    Hist("diele_mass_LPPF"      , "diele_LPPF_mass",),
    Hist("Electron_pt"          , "Electron_pt",),
    Hist("Wp90Ele_pt"           , "Wp90Ele_pt",),
    ],
    "nWp90Ele1":[
    Hist("Wp90Ele_pt"           , "Wp90Ele_pt",),
    ]
}