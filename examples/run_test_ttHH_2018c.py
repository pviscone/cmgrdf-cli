from CMGRDF import *
from CMGRDF.data import Source
from CMGRDF.cache import SimpleCache
import ROOT

P=localOrEOS("TREES_TTHH_2018C_150622","/data/shared","/eos/cms/store/cmst3/group/tthlep")+"/{name}.root"
if P.startswith("/eos") and not os.path.isdir("/eos"): P = "root://eoscms.cern.ch/"+P

def mkMC(name, parts=0):
    if parts == 0:
        return MCSample(name, P, xsec="xsec")
    else:
        return MCSample(name, Source(name,[P.format(name=(f"{name}_part{i}")) for i in range(1,parts+1)]), xsec="xsec")

mcSamples = dict(
        DY = MCGroup("DY", [mkMC("DYJetsToLL_M10to50_LO"), mkMC("DYJetsToLL_M50",2)]),
        WJ = MCGroup("WJ", [mkMC(f"W{i}JetsToLNu_LO") for i in (1,2,3,4)]),
        Ttch  = MCGroup("Ttch", [mkMC("T_tch"), mkMC("TBar_tch")]),
        Tsch  = MCGroup("Tsch", [mkMC("T_sch_lep")]),
        TW    = MCGroup("TW", [mkMC("T_tWch_noFullyHad"), mkMC("TBar_tWch_noFullyHad")]),
        TT0l = mkMC("TTHad_pow"),
        TT1l = mkMC("TTSemi_pow",2),
        TT2l = mkMC("TTLep_pow",2),
)
dataSamples = [
        DataSample("EGamma", P.format(name="EGamma_Run2018C")),
        DataSample("SingleMuon", Source("SingleMuon", [P.format(name=f"SingleMuon_Run2018C_part{i}") for i in (1,2)])),
]

## Common stuff
ROOT.gInterpreter.Declare("""
ROOT::RVec<int> cleanByIndex(const ROOT::RVec<int> & Jet_sel, const ROOT::RVec<int> & Lep_forClean, const ROOT::RVec<int> & Lep_jetIdx)
{
    auto nJets = Jet_sel.size();
    ROOT::RVec<int> mask(nJets, 1);
    for (unsigned i = 0, n = Lep_jetIdx.size(); i < n; ++i) {
            if (Lep_forClean[i]) {
                    if (Lep_jetIdx[i] >= 0 && Lep_jetIdx[i] < nJets) {
                            mask[Lep_jetIdx[i]] = 0;
                    }
            }
    }
    return mask;
}
""")
commonSteps = [
        AddWeight("prescaleFromSkim","prescaleFromSkim", onData=True, onDataDriven=True),
        Define("Jet_sel","Jet_pt > 25 && abs(Jet_eta) < 2.4 && Jet_jetId > 1"),
        Define("LepGood_forJetCleaning", "LepGood_pt > 15"),
        Define("Jet_noLep","cleanByIndex(Jet_sel,LepGood_forJetCleaning,LepGood_jetIdx)"),
        [ Define(f"JetGood_{v}",f"Jet_{v}[Jet_noLep]") for v in ("pt","eta","phi","mass","btagDeepFlavB") ],
        #[ Define(f"JetGood_{v}",f"Jet_{v}[Jet_noLep]", onData=False, onDataDriven=False) for v in ("hadronFlavour","genJetIdx") ],
        Define("nJet25","Sum(Jet_noLep)"),
        Define("nJet30","Sum(JetGood_pt > 30)"),
        Define("nJet40","Sum(JetGood_pt > 40)"),
        Define("HTJet25","Sum(JetGood_pt)"),
        Define("nBJetLoose25","Sum(JetGood_btagDeepFlavB >= deepFlavB_WPLoose(year))"),
        Define("nBJetMedium25","Sum(JetGood_btagDeepFlavB >= deepFlavB_WPMedium(year))"),
]

TruthMatchedLeptons = Insert(Cut("mcTrue","LepGood_mcMatchId[iLepFO_Recl[0]] != 0 && LepGood_mcMatchId[iLepFO_Recl[1]] != 0"), after="dilep")
FakeMatchedLeptons = Insert(Cut("mcTrue","||".join(f"(LepGood_mcMatchId[iLepFO_Recl[{i}]] == 0 && LepGood_mcPromptGamma[iLepFO_Recl[{i}]] == 0)" for i in (0,1))), after="dilep")
## Zll
procs_Zll = [
        Process("DY", mcSamples["DY"], label="DY", fillColor=ROOT.kAzure+10, signal=True),
        Process("TT2l", mcSamples["TT2l"], label="t#bar{t}(2l)", fillColor=ROOT.kViolet-4),
        Process("TW", mcSamples["TW"], label="tW", fillColor=ROOT.kViolet+1),
        Process("WJ", mcSamples["WJ"], label="W+jets", fillColor=ROOT.kOrange+1),
        Process("TT01l", [mcSamples["TT0l"],mcSamples["TT1l"]], label="t#bar{t}(01l)", fillColor=ROOT.kMagenta-4),
        Process("T01l", [mcSamples["Ttch"],mcSamples["Tsch"]], label="t(01l)", fillColor=ROOT.kViolet-7),
        Data(dataSamples)
]
cuts_Zll = Flow("Zll",
        commonSteps,
        Cut("trigger", "HLT_IsoMu24 || HLT_Ele32_WPTight_Gsf"),
        Cut("2lsfos", "nLepGood >= 2 && LepGood_pdgId[0] == -LepGood_pdgId[1]"),
        Cut("ptX15", "LepGood_pt[0] > (abs(LepGood_pdgId[0])==11?35:25) && LepGood_pt[1] > 15"),
        Define("mll", "mass_2(LepGood_pt[0],LepGood_eta[0],LepGood_phi[0],LepGood_mass[0],LepGood_pt[1],LepGood_eta[1],LepGood_phi[1],LepGood_mass[1])"),
        Cut("mll12", "mll > 12")
)
cuts_Zee = cuts_Zll.clone("Zee").append(Cut("ee", "abs(LepGood_pdgId[0]) == 11"))
cuts_Zmm = cuts_Zll.clone("Zmm").append(Cut("mm", "abs(LepGood_pdgId[0]) == 13"))
plots_Zll = [ 
        Plot("l1pt", "LepGood_pt[0]", (100,20,120), xTitle="p_{T}(l1)"),
        Plot("l2pt", "LepGood_pt[1]", (100,00,100), xTitle="p_{T}(l2)"),
        Plot("mll", "mll", (120,0,120), xTitle="m(ll)", legend="TL"),
        Plot("nJet", "nJet25", (14,0.5,14.5), xTitle="Number of jets (p_{T} > 25)", logy=True, moreY=10),
        Plot("nJet40", "nJet40", (10,0.5,10.5), xTitle="Number of jets (p_{T} > 40)", logy=True, moreY=10),
        Plot("nBLoose", "nBJetLoose25", (8,0.5,8.5), xTitle="Number of loose b-jets (p_{T} > 25)", logy=True, moreY=10),
        Plot("nBMedium", "nBJetMedium25", (6,0.5,6.5), xTitle="Number of medium b-jets (p_{T} > 25)", logy=True, moreY=10),
        Plot("met", "MET_pt", (120,0,120), xTitle="p_{T}^{miss} (GeV)"),
]


lumi = 6.90
cache = SimpleCache("cmgrdf_cache_ttHH.dir")
ROOT.EnableImplicitMT(16)
maker = PlotMaker(cache = cache)
maker.book(procs_Zll,lumi,cuts_Zll,plots_Zll)
maker.book(procs_Zll,lumi,cuts_Zee,plots_Zll)
maker.book(procs_Zll,lumi,cuts_Zmm,plots_Zll)
result_plots = maker.runAll()
printer = PlotSetPrinter(topRightText="L = %(lumi).1f fb^{-1} (13 TeV)", showRatio=True)
printer.printSet(result_plots, "plots/004/{flow}")