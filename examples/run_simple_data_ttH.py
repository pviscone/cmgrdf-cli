from CMGRDF import *
import ROOT

P=localOrEOS("2018","/scratch/gpetrucc/NanoTrees_TTH_v6","/eos/cms/store/cmst3/group/tthlep/peruzzi/NanoTrees_TTH_090120_v6pre")
PD=localOrEOS("2018","/scratch/gpetrucc/NanoTrees_TTH_v6","/eos/cms/store/cmst3/group/tthlep/peruzzi/NanoTrees_TTH_090120_v6_triggerFix")
data_dilep = [
    Process("DY", [MCSample("DYJetsToLL_M50",P+"/{name}.root", xsec="xsec"),
                   MCSample("DYJetsToLL_M10to50_LO",P+"/{name}.root", xsec="xsec")], label="DY", fillColor=ROOT.kAzure+10, signal=True),
    Process("WZ", [MCSample("WZTo3LNu_pow",P+"/{name}.root", xsec="xsec")], label="WZ", fillColor=ROOT.kMagenta+1),
    Process("WW", [MCSample("WWTo2L2Nu",P+"/{name}.root", xsec="xsec")], label="WW", fillColor=ROOT.kViolet+1),
    Process("TT", [MCSample("TTJets_DiLepton",P+"/{name}.root", xsec="xsec")], label="t#bar{t}", fillColor=ROOT.kOrange+3),
    Data([DataSample("DoubleMuon_Run2018%s_25Oct2019"%era,PD+"/{name}.root") for era in "ABCD"]),
]
cuts_dilep = Flow("dilep",
        AddWeight("prescaleFromSkim","prescaleFromSkim", onData=True, onDataDriven=True),
        Cut("trigger", "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8"),
        Cut("2l", "nLepGood >= 2"),
        Cut("pt2515", "LepGood_pt[0] > 25 && LepGood_pt[1] > 15"),
        Cut("dimuons", "LepGood_pdgId[0]*LepGood_pdgId[1] == -13*13"),
        )
cuts_trilep = cuts_dilep.clone("trilep").append(
        Cut("3l", "nLepGood >= 3"),
)
plots_dilep = [ 
        Plot("mZ1", "mZ1", (120,0,120), xTitle="m(ll)", legend="TL"),
        Plot("nJet30", "Sum(Jet_pt > 30)", (14,0.5,14.5), xTitle="Number of jets (p_{T} > 30)", logy=True, moreY=10),
        Plot("met", "MET_pt", (120,0,120), xTitle="p_{T}^{miss} (GeV)"),
]
plots_trilep = plots_dilep + [ 
        Plot("lep3pt", "LepGood_pt[2]", (50,0,80), xTitle="p_{T}(l3) (GeV)", legend="TR"),
]

lumi = 59.

ROOT.EnableImplicitMT(8)
maker = PlotMaker()
maker.book(data_dilep,lumi,cuts_dilep,plots_dilep)
maker.book(data_dilep,lumi,cuts_trilep,plots_trilep)
result_plots = maker.runAll()
printer = PlotSetPrinter(topRightText="L = %.0f fb^{-1} (13 TeV)"%lumi, showRatio=True)
printer.printSet(result_plots, "plots/001/{flow}/cmgrdf")