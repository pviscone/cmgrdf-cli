from CMGRDF.cms.eras import lumis as lumi

P = "root://eoscms.cern.ch//eos/cms/store/cmst3/group/xee/example"

era_paths_Data = {"2023": (P + "/Data", "{name}_Run{era}{subera}_data_13X.root", "")}
era_paths_MC = {"2023": (P + "/MC","{name}_Run{era}_mc_13X.root", "")}

lumi["2023"] = 10

PFs = []
PMCs = []
