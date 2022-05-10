from flow import Process, MCSample, DataSample, Data, Flow, Cut, ReDefine
from plots import Plot, PlotMaker, PlotSetPrinter
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.IgnoreCommandLineOptions = True

P="/scratch/gpetrucc/NanoTrees_SOS_070220_v6_skim_2lep_met125/{era}/{name}.root"
PF="/scratch/gpetrucc/NanoTrees_SOS_070220_v6_skim_2lep_met125/{era}/recleaner/{name}_Friend.root"
PFMC="/scratch/gpetrucc/NanoTrees_SOS_070220_v6_skim_2lep_met125/{era}/jetmetUncertainties/{name}_Friend.root"
data = [
    Process("TT", [MCSample("TTJets_DiLepton",P, friends=[PF,PFMC], xsec="xsec", eras=[2017,2018])], label="t#bar{t} (2l)", fillColor=ROOT.kBlue-7),
    Data([DataSample("MET_Run2017F_25Oct2019", P, friends=[PF], eras=[2017]),
          DataSample("MET_Run2018D_25Oct2019", P, friends=[PF], eras=[2018])]),
]
cuts = Flow("SR",
        ReDefine("MET_pt", "MET_pt_jer", eras=[2018], onData=False, onDataDriven=False),
        ReDefine("MET_pt", "METFixEE2017_pt_jer", eras=[2017], onData=False, onDataDriven=False),
        ReDefine("MET_pt", "METFixEE2017_pt", eras=[2017], onMC=False),
        Cut("dilep", "nLepFO_Recl >= 2"),
        Cut("dilepTight", "nLepTight_Recl >= 2"),
        )
plots = [ 
        Plot("nLepTight", "nLepTight_Recl", (6,0.5,5.5), xTitle="Number of tight leptons"),
        Plot("nJet40", "nJet40_Recl", (8,0.5,7.5), xTitle="Number of jets (p_{T} > 40)", logy=True, moreY=10),
        Plot("htJet40j", "htJet40j_Recl", (40,0,1200), xTitle="H_{T}\, jet p_{T} > 40 (GeV)", logy=True, moreY=10),
        Plot("met", "MET_pt", (40,0,400), xTitle="p_{T}^{miss} (GeV)", logy=True, moreY=10),
        #Plot("metFix", "METFixEE2017_pt", (40,0,400), xTitle="p_{T}^{miss} - 2017 FIX (GeV)", logy=True, moreY=10, eras=[2017]) # eras not yet supported here
]

lumi = {2017:41.5, 2018:59.7}

ROOT.EnableImplicitMT(8)
results = PlotMaker().book(data, lumi, cuts, plots, eras=[2017,2018]).runAll()
PlotSetPrinter().printSet(results, "plots/001/friends/cmgrdf/{era}")