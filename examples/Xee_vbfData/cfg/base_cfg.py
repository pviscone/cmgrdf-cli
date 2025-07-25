from CMGRDF.cms.eras import lumis as lumi

P = "root://eoscms.cern.ch//eos/cms/store/cmst3/group/xee"

era_paths_Data = {"2024": (P, "data/allnanoColl/VBF/v0/{name}/Run{era}{subera}/*.root", "")}
era_paths_MC = {"2024": (P, "", "")}

lumi["2024"] = 109.4

PFs = []
PMCs = []
