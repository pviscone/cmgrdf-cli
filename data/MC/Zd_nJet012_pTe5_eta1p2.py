from data.MC import cms10

MCDict={
    "HAHM_13p6TeV_M5" : {
        "groups" : [
            {
            "name": "HAHM_13p6TeV_M5",
            "samples": {
                "HAHM_13p6TeV_M5":
                    {
                    "xsec": 1.952,
                    "path": "signalSamples/HAHM_DarkPhoton_13p6TeV_Nov2024/NANOAOD_noskim_allpairs_allnanoColl/CRAB_UserFiles/crab_{name}/250124_183927/0000/DoubleElectronNANO_Run3_{era}_mc_2025Jan24_1.root"
                    },
                },
            "cut":"1",
            },
        ],
        "signal": True,
        "label":"ZdM5",
        "color": cms10[0],
    },
    "HAHM_13p6TeV_M3p1" : {
        "groups" : [
            {
            "name": "HAHM_13p6TeV_M3p1",
            "samples": {
                "HAHM_13p6TeV_M3p1":
                    {
                    "xsec":2.679,
                    "path": "signalSamples/HAHM_DarkPhoton_13p6TeV_Nov2024/NANOAOD_noskim_allpairs_allnanoColl/CRAB_UserFiles/crab_{name}/250124_203010/0000/DoubleElectronNANO_Run3_{era}_mc_2025Jan24_1.root"
                    },
                },
            "cut":"1",
            },
        ],
        "label":"ZdM3p1",
        "color": cms10[1],
        "signal": True,
    },
    "HAHM_13p6TeV_M1" : {
        "groups" : [
            {
            "name": "HAHM_13p6TeV_M1",
            "samples": {
                "HAHM_13p6TeV_M1":
                    {
                    "xsec":3.396,
                    "path": "signalSamples/HAHM_DarkPhoton_13p6TeV_Nov2024/NANOAOD_noskim_allpairs_allnanoColl/CRAB_UserFiles/crab_{name}/250124_183942/0000/DoubleElectronNANO_Run3_{era}_mc_2025Jan24_1.root"
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

