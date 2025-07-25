from cmgrdf_cli.data import cms10

all_processes={
    "HAHM_13p6TeV_M3p1_VBF" : {
        "groups" : [
            {
            "name": "HAHM_13p6TeV_M3p1_VBF",
            "samples": {
                "HAHM_13p6TeV_M3p1_VBF":
                    {
                    "xsec":0.006555,
                    "path": "signalSamples/HAHM_DarkPhoton_13p6TeV_Nov2024/NANOAOD_noselection_addGEN_VBFflags/CRAB_UserFiles/crab_{name}/250207_160051/0000/DoubleElectronNANO_Run3_2023_mc_2025Feb07_1.root"
                    },
                },
            "cut":"1",
            },
        ],
        "label":"ZdM3p1 (2023)",
        "color": cms10[0],
        "signal": True,
    }
}