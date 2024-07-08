from CMGRDF.utils import NormUncertainty

## Eras for Run2 (UL)
run2eras = ["2016", "2016APV", "2017", "2018"]
run3eras = ["2022", "2022EE"]

lumis = {
    "2016APV": 19.50,
    "2016": 16.81,
    "2017": 41.48,
    "2018": 59.83,
    "2022": (4.943 + 2.922),
    "2022EE":  (5.672 + 17.610 + 3.055),
}


suberas_perera={
    "2022"    : "C,D".split(","),
    "2022EE"  : "E,F,G".split(","),
    "2018"    : "A,B,C,D".split(","),
    "2016"    : "F,G,H".split(","),
    "2017"    : "B,C,D,E,F".split(","),
    "2016APV" : "B,C,D,E,F".split(","),
}



# https://twiki.cern.ch/twiki/bin/view/CMS/LumiRecommendationsRun2 (Rev2)
lumiUncertainties = [
    NormUncertainty("CMS_lumi_run2_Correlated", 1.006, eras=["2016", "2016pre", "2016post"]),
    NormUncertainty("CMS_lumi_run2_Correlated", 1.009, eras=["2017"]),
    NormUncertainty("CMS_lumi_run2_Correlated", 1.020, eras=["2018"]),
    NormUncertainty("CMS_lumi_run2_Correlated1718", 1.006, eras=["2017"]),
    NormUncertainty("CMS_lumi_run2_Correlated1718", 1.002, eras=["2018"]),
    NormUncertainty("CMS_lumi_2016", 1.010, eras=["2016", "2016pre", "2016post"]),
    NormUncertainty("CMS_lumi_2017", 1.020, eras=["2017"]),
    NormUncertainty("CMS_lumi_2018", 1.015, eras=["2018"]),
]
lumiUncerty2016 = NormUncertainty("CMS_lumi", 1.012)
lumiUncerty2017 = NormUncertainty("CMS_lumi", 1.023)
lumiUncerty2018 = NormUncertainty("CMS_lumi", 1.025)


