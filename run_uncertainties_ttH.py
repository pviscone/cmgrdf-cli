import sys
from flow import AddWeightUncertainty, Process, MCSample, DataSample, Data, Flow, AddWeight, Cut, Define, Append

from plots import Plot, PlotMaker, PlotSetPrinter
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gInterpreter.ProcessLine('#include "functions.cc"')

P="/scratch/gpetrucc/NanoTrees_TTH_v6/2018/"
DYuncs = Append(AddWeightUncertainty("DYxsec",1.2),
                AddWeightUncertainty("DYnj","std::pow(1.05,nJet)","std::pow(0.95,nJet)")) 
TTuncs = Append(AddWeightUncertainty("TTxsec",1.3))

data = [
    Process("TT", [MCSample("TTJets_DiLepton",P+"/{name}.root", xsec="xsec", hooks=[TTuncs])], label="t#bar{t}", fillColor=ROOT.kOrange+3, signal=True),
    Process("DY", [MCSample("DYJetsToLL_M50",P+"/{name}.root", xsec="xsec", hooks=[DYuncs]),
                   MCSample("DYJetsToLL_M10to50_LO",P+"/{name}.root", xsec="xsec", hooks=[DYuncs])], label="DY", fillColor=ROOT.kAzure+10),
    Data([DataSample("DoubleMuon_Run2018%s_25Oct2019"%era,P+"/{name}.root") for era in "ABCD"]),
]
cuts = Flow("dilep",
        AddWeight("prescaleFromSkim","prescaleFromSkim", onData=True, onDataDriven=True),
        #DefinePerSample("year","2018"), # already in NTuple
        Cut("trigger", "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8"),
        Cut("2l", "nLepGood >= 2"),
        Cut("pt2515", "LepGood_pt[0] > 25 && LepGood_pt[1] > 15"),
        Cut("dimuons", "LepGood_pdgId[0]*LepGood_pdgId[1] == -13*13"),
        Define("Jet_good", "Jet_pt > 30 && abs(Jet_eta) < 2.4"),
        Define("Jet_bMedium", "Jet_good && Jet_btagDeepFlavB >= deepFlavB_WPMedium(year)"),
        Define("mll", "mass_2(LepGood_pt[0],LepGood_eta[0],LepGood_phi[0],LepGood_mass[0],"+
                              "LepGood_pt[1],LepGood_eta[1],LepGood_phi[1],LepGood_mass[1])"),
        Define("nJet30","Sum(Jet_good)"),
        Define("nBJet30","Sum(Jet_bMedium)"),
        Cut("minMll", "mll > 12"),
        Cut("2j", "nJet30 >= 2"),
        #Cut("1b", "nBJet30 >= 1"),
        )

plots = [ 
        Plot("mll", "mll", (120,12,132), xTitle="m(ll)", legend="TL"),
        Plot("nJet30", "nJet30", (6,1.5,7.5), xTitle="Number of jets (p_{T} > 30)", logy=True, moreY=10),
        Plot("nBJet30", "nBJet30", (5,-0.5,4.5), xTitle="Number of b-jets (p_{T} > 30)", logy=True, moreY=10),
        Plot("met", "MET_pt", (75,0,150), xTitle="p_{T}^{miss} (GeV)", logy=True, moreY=10),
]

lumi = 59.

ROOT.EnableImplicitMT(8)
maker = PlotMaker()
#verbosity = ROOT.Experimental.RLogScopedVerbosity(ROOT.Detail.RDF.RDFLogChannel(), ROOT.Experimental.ELogLevel.kInfo)
maker.book(data,lumi,cuts,plots,withUncertainties=True)
#sys.exit()
result_plots = maker.runAll()
printer = PlotSetPrinter(topRightText="L = %.0f fb^{-1} (13 TeV)"%lumi, showRatio=True)
printer.printSet(result_plots, "plots/002/dilep-uncertainties/cmgrdf")