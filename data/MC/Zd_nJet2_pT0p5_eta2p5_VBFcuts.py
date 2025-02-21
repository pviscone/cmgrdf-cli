from data.MC import cms10

MCDict={
    "HAHM_13p6TeV_M5_VBF" : {
        "groups" : [
            {
            "name": "HAHM_13p6TeV_M5_VBF",
            "samples": {
                "HAHM_13p6TeV_M5_VBF":
                    {
                    "xsec": 0.004203,
                    "path": "signalSamples/HAHM_DarkPhoton_13p6TeV_Nov2024/NANOAOD_noselection_addGEN_VBFflags/CRAB_UserFiles/crab_{name}/250207_160043/0000/DoubleElectronNANO_Run3_{era}_mc_2025Feb07_1.root"
                    },
                },
            "cut":"1",
            },
        ],
        "signal": True,
        "label":"ZdM5",
        "color": cms10[0],
    },
    "HAHM_13p6TeV_M3p1_VBF" : {
        "groups" : [
            {
            "name": "HAHM_13p6TeV_M3p1_VBF",
            "samples": {
                "HAHM_13p6TeV_M3p1_VBF":
                    {
                    "xsec":0.006555,
                    "path": "signalSamples/HAHM_DarkPhoton_13p6TeV_Nov2024/NANOAOD_noselection_addGEN_VBFflags/CRAB_UserFiles/crab_{name}/250207_160051/0000/DoubleElectronNANO_Run3_{era}_mc_2025Feb07_1.root"
                    },
                },
            "cut":"1",
            },
        ],
        "label":"ZdM3p1",
        "color": cms10[1],
        "signal": True,
    },
    "HAHM_13p6TeV_M1_VBF" : {
        "groups" : [
            {
            "name": "HAHM_13p6TeV_M1_VBF",
            "samples": {
                "HAHM_13p6TeV_M1_VBF":
                    {
                    "xsec":0.009728,
                    "path": "signalSamples/HAHM_DarkPhoton_13p6TeV_Nov2024/NANOAOD_noselection_addGEN_VBFflags/CRAB_UserFiles/crab_{name}/250207_160102/0000/DoubleElectronNANO_Run3_{era}_mc_2025Feb07_1.root"
                    },
                },
            "cut":"1",
            },
        ],
        "label":"ZdM1",
        "signal": True,
        "color": cms10[2],
    }
}

