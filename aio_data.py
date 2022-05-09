from flow import Process, MCSample, DataSample, Data, Flow, AddWeight, Cut
from plots import Plot, PlotMaker, PlotSetPrinter
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.IgnoreCommandLineOptions = True

P="/scratch/gpetrucc/NanoTrees_TTH_v6/2018/"
mca_dilep = [
    Process("DY", [MCSample("DYJetsToLL_M50",P+"/{name}.root", xsec="xsec"),
                   MCSample("DYJetsToLL_M10to50_LO",P+"/{name}.root", xsec="xsec")], label="DY", fillColor=ROOT.kAzure+10, signal=True),
    Process("WW", [MCSample("WWTo2L2Nu",P+"/{name}.root", xsec="xsec")], label="WW", fillColor=ROOT.kViolet+1),
    Process("TT", [MCSample("TTJets_DiLepton",P+"/{name}.root", xsec="xsec")], label="t#bar{t}", fillColor=ROOT.kOrange+3),
    Data([DataSample("DoubleMuon_Run2018%s_25Oct2019"%era,P+"/{name}.root") for era in "ABCD"]),
]
cuts_dilep = Flow("dilep",
        AddWeight("prescaleFromSkim","prescaleFromSkim",data=True),
        Cut("trigger", "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8"),
        Cut("2l", "nLepGood >= 2"),
        Cut("pt2515", "LepGood_pt[0] > 25 && LepGood_pt[1] > 15"),
        Cut("dimuons", "LepGood_pdgId[0]*LepGood_pdgId[1] == -13*13"),
        )
plots_dilep = [ 
        Plot("mZ1", "mZ1", (120,0,120), xTitle="m(ll)", legend="TL"),
        Plot("nJet", "nJet", (18,2.5,20.5), xTitle="Number of jets"),
        Plot("nJet30", "Sum(Jet_pt > 30)", (14,0.5,14.5), xTitle="Number of jets (p_{T} > 30)", logy=True, moreY=10),
]

lumi_dilep = 59.

ROOT.EnableImplicitMT(8)
result_plots_dilep = PlotMaker().book(mca_dilep,lumi_dilep,cuts_dilep,plots_dilep).runAll()
printer_dilep = PlotSetPrinter(topRightText="L = 138 fb^{-1} (13 TeV)", showRatio=True)
printer_dilep.printSet(result_plots_dilep, "plots/001/{flow}/cmgrdf")