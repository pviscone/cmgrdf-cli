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
        # top + X
        TTW = mkMC("TTWToLNu"),
        TTZ = mkMC("TTZToLLNuNu"),
        TWZ = mkMC("TWLL"),
        TZQ = mkMC("TZQToLL"),
        # ttH
        TTHBB = mkMC("TTHTobb_M125_pow"), # ttH, H -> bb 
        TTHNoBB = mkMC("TTHToNonbb_M125_pow"), # ttH, any other than H -> bb
        TTHTT = mkMC("TTHToTauTau_M125_pow"), # ttH, H -> tau tau
        TTHGG = mkMC("TTHToGG_M125_fxfx"), # ttH, H -> gamma gamma
        # ttHH
        TTHH4B = mkMC("TTHHTo4b"), # ttHH, HH -> 4b 
        TTHHNo4B = mkMC("TTHHToNon4b"), # ttHH, any other than HH -> 4b
        # dibosons (leptonic decays)
        WW2l = mkMC("WWTo2L2Nu"), 
        WZ3l = mkMC("WZTo3LNu"),
        ZZ4l = mkMC("ZZTo4L"),
        # diphoton samples
        GGAll = mkMC("DiPhoton"), # inclusive
        GG1B  = mkMC("DiPhoton1B"), # + 1 b quark
        GG2B  = mkMC("DiPhoton2B"), # + 2 b quarks
        TTG   = mkMC("TTGJets"), # ttbar + 1 photon + jets
        TTGG  = mkMC("TTGG"),    # ttbar + 2 photons
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
        Plot("nJet", "nJet25", (12,-0.5,11.5), xTitle="Number of jets (p_{T} > 25)", logy=True, moreY=10),
        Plot("nJet40", "nJet40", (8,-0.5,7.5), xTitle="Number of jets (p_{T} > 40)", logy=True, moreY=10),
        Plot("nBLoose", "nBJetLoose25", (6,-0.5,5.5), xTitle="Number of loose b-jets (p_{T} > 25)", logy=True, moreY=10),
        Plot("nBMedium", "nBJetMedium25", (6,-0.5,5.5), xTitle="Number of medium b-jets (p_{T} > 25)", logy=True, moreY=10),
        Plot("met", "MET_pt", (120,0,120), xTitle="p_{T}^{miss} (GeV)"),
]

ROOT.gInterpreter.Declare("""
#include "Math/GenVector/LorentzVector.h"
#include "Math/GenVector/PtEtaPhiM4D.h"

/// Example of finding the pair of same-flavour opposite-sign leptons with mass closest to the Z0 mass
ROOT::RVec<int> findZll(const ROOT::RVec<float> & Lep_pt, const ROOT::RVec<float> & Lep_eta, const ROOT::RVec<float> & Lep_phi, const ROOT::RVec<float> & Lep_mass, const ROOT::RVec<int> & Lep_pdgId)
{
    typedef ROOT::Math::LorentzVector<ROOT::Math::PtEtaPhiM4D<double> > PtEtaPhiMVector;
    unsigned nLep = Lep_pt.size();
    ROOT::RVec<int> sel(2, -1);
    float bestMass = -1;
    const float mZ = 91.187;
    for (unsigned i = 0; i < nLep-1; ++i) {
        PtEtaPhiMVector p4i(Lep_pt[i], Lep_eta[i], Lep_phi[i], Lep_mass[i]);
        for (unsigned j = i+1; j < nLep; ++j) {
                if (Lep_pdgId[i] == -Lep_pdgId[j]) {
                        PtEtaPhiMVector p4j(Lep_pt[j], Lep_eta[j], Lep_phi[j], Lep_mass[j]);
                        float mll = (p4i + p4j).M();
                        if (bestMass < 0 || std::abs(mll - mZ) < std::abs(bestMass - mZ)) {
                                bestMass = mll;
                                sel[0] = i; 
                                sel[1] = j;
                        } 
                }
        }
    }
    return sel;
}

/// Example of finding the minimum dilepton invariant mass among the top N leptons
float minMll(const ROOT::RVec<float> & Lep_pt, const ROOT::RVec<float> & Lep_eta, const ROOT::RVec<float> & Lep_phi, const ROOT::RVec<float> & Lep_mass, int nmax=999)
{
    typedef ROOT::Math::LorentzVector<ROOT::Math::PtEtaPhiM4D<double> > PtEtaPhiMVector;
    unsigned nLep = std::min<unsigned>(Lep_pt.size(), nmax);
    float minMass = 9e9; // initialize to a large value
    for (unsigned i = 0; i < nLep-1; ++i) {
        PtEtaPhiMVector p4i(Lep_pt[i], Lep_eta[i], Lep_phi[i], Lep_mass[i]);
        for (unsigned j = i+1; j < nLep; ++j) {
            PtEtaPhiMVector p4j(Lep_pt[j], Lep_eta[j], Lep_phi[j], Lep_mass[j]);
            float mll = (p4i + p4j).M();
            minMass = std::min(mll,minMass);
        }
    }
    return minMass;
}
""")

cuts_3l_tight = Flow("3l_tight",
        commonSteps,
        Cut("trigger", "HLT_IsoMu24 || HLT_Ele32_WPTight_Gsf"),
        ## Now we define a tighter lepton selection, 
        Define("LepGood_tightSel", "LepGood_pt > 10 && "+ 
                         "(abs(LepGood_pdgId) == 11 && LepGood_mvaFall17V2noIso_WP90 || "+ # MVA ID 90% efficiency WP for electrons (LepGood has instead the loose WP)
                         " abs(LepGood_pdgId) == 13 && LepGood_mediumId) &&" +             # Medium ID for muons (LepGood has no cut by mistake, should have had looseId)
                         "abs(LepGood_dxy) < 0.05 && abs(LepGood_dz) < 0.1 && "+           # cuts on the impact parameter, in cm (LepGood has no cut)
                         "LepGood_sip3d < 6 && "                                           # cut on the 3D impact parameter significance (LepGood has no cut)
                        "LepGood_miniPFRelIso_all < 0.15"),                                # tighter cut on isolation (LepGood has a cut at 0.4)
        ## And now define nLepTight and LepTight_<var> copying from LepGood applying the selection
        Define("nLepTight","Sum(LepGood_tightSel)"),
        [ Define(f"LepTight_{x}", f"LepGood_{x}[LepGood_tightSel]") for x in ("pt", "eta", "phi", "mass", "charge", "pdgId", "dxy", "dz", "sip3d","miniPFRelIso_all","jetIdx") ],
        ## Now we can define a selection with 3 leptons
        Cut("3l", "nLepTight >= 3"),
        Cut("ptX1515", "LepTight_pt[0] > (abs(LepTight_pdgId[0])==11?35:25) && LepTight_pt[1] > 15 && LepTight_pt[2] > 15"),
        ## Veto events with leptons at low invariant mass (m(ll) < 12 GeV), which are not well predicted by the simulations we use
        Define("minMllTight","minMll(LepTight_pt,LepTight_eta,LepTight_phi,LepTight_mass)"),
        Cut("minMll12","minMllTight > 12"), 
        ## Select a Z from the leptons
        Define("lepZ", "findZll(LepTight_pt,LepTight_eta,LepTight_phi,LepTight_mass,LepTight_pdgId)"),
        Cut("hasZ","lepZ[0] >= 0"), # if no Z is found, findZll returns {-1,-1} and the code below would fail
        Define("mZll", "mass_2(LepTight_pt[lepZ[0]],LepTight_eta[lepZ[0]],LepTight_phi[lepZ[0]],LepTight_mass[lepZ[0]],LepTight_pt[lepZ[1]],LepTight_eta[lepZ[1]],LepTight_phi[lepZ[1]],LepTight_mass[lepZ[1]])"),        
        Cut("Zpeak", "mZll > 60 && mZll < 120")
)
procs_3l_tight = [
        Process("WZ", mcSamples["WZ3l"], label="WZ", fillColor=ROOT.kRed+0),
        Process("ZZ", mcSamples["ZZ4l"], label="ZZ", fillColor=ROOT.kRed+2),
        Process("TopZ", [mcSamples["TTZ"],mcSamples["TZQ"],mcSamples["TWZ"]], label="t+Z", fillColor=ROOT.kGreen+1),
        Process("DY", mcSamples["DY"], label="DY", fillColor=ROOT.kAzure+10),
        Process("WW", mcSamples["WW2l"], label="WW", fillColor=ROOT.kAzure+2),
        Process("TT", [mcSamples["TT2l"],mcSamples["TW"],mcSamples["TTW"]], label="t#bar{t}+tW", fillColor=ROOT.kViolet-4),
        Data(dataSamples)
]
plots_3l_tight = [ 
        Plot("l1pt", "LepTight_pt[0]", (30,20,240), xTitle="p_{T}(l1)"),
        Plot("l2pt", "LepTight_pt[1]", (30,00,150), xTitle="p_{T}(l2)"),
        Plot("l3pt", "LepTight_pt[2]", (30,00,90), xTitle="p_{T}(l3)"),
        Plot("minMll", "minMllTight", (30,0,120), xTitle="min m(ll)", legend="TL"),
        Plot("mZll", "mZll", (40,60,120), xTitle="m(ll)", legend="TL"),
        Plot("met", "MET_pt", (40,0,200), xTitle="p_{T}^{miss} (GeV)"),
        Plot("nLep", "nLepTight", (3,2.5,5.5), xTitle="Number of tight leptons", logy=True, moreY=10),
        Plot("nJet", "nJet25", (12,-0.5,11.5), xTitle="Number of jets (p_{T} > 25)", logy=True, moreY=10),
        Plot("nJet40", "nJet40", (9,-0.5,8.5), xTitle="Number of jets (p_{T} > 40)", logy=True, moreY=10),
        Plot("nBMedium", "nBJetMedium25", (6,-0.5,5.5), xTitle="Number of medium b-jets (p_{T} > 25)", logy=True, moreY=10),
        Plot("WorstIso","std::max(LepTight_miniPFRelIso_all[0],std::max(LepTight_miniPFRelIso_all[1],LepTight_miniPFRelIso_all[2]))", (20,0,0.4), xTitle="Worst lepton isolation"),
        Plot("WorstIso3","std::max(LepTight_sip3d[0],std::max(LepTight_sip3d[1],LepTight_sip3d[2]))", (20,0,8), xTitle="Worst lepton sip3d"),
]

lumi = 6.90
cache = SimpleCache("cmgrdf_cache_ttHH.dir")
ROOT.EnableImplicitMT(16)
maker = PlotMaker(cache = cache)
maker.book(procs_Zll,lumi,cuts_Zll,plots_Zll)
maker.book(procs_Zll,lumi,cuts_Zee,plots_Zll)
maker.book(procs_Zll,lumi,cuts_Zmm,plots_Zll)
maker.book(procs_3l_tight,lumi,cuts_3l_tight,plots_3l_tight)
result_plots = maker.runAll()
printer = PlotSetPrinter(topRightText="L = %(lumi).1f fb^{-1} (13 TeV)", showRatio=True)
printer.printSet(result_plots, "plots/004/{flow}")

## Example of non-stacked comparisons
procs_ttbb = [
        Process("TT", [mcSamples["TT0l"],mcSamples["TT1l"],mcSamples["TT2l"]], label="t#bar{t}", fillColor=ROOT.kGray+1),
        Process("TTHbb", mcSamples["TTHBB"], label="t#bar{t}H(bb)", fillColor=ROOT.kViolet+1, signal=True),
        Process("TTHH4b", mcSamples["TTHH4B"], label="t#bar{t}HH(4b)", fillColor=ROOT.kRed+1, signal=True),
]
cuts_ttbb = Flow("ttbb",
        commonSteps,
        Cut("trigger", "HLT_IsoMu24 || HLT_Ele32_WPTight_Gsf"),
        Cut("1l", "nLepGood >= 1 && LepGood_pt[0] > (abs(LepGood_pdgId[0])==11?35:25)"),
        Cut("3j", "nJet25 >= 3"),
        Cut("1b", "nBJetMedium25 >= 1"),
)
plots_ttbb = [ 
        Plot("l1pt", "LepGood_pt[0]", (50,0,250), xTitle="p_{T}(l1)", logy=True, moreY=10),
        Plot("nJet", "nJet25", (12,3.5,15.5), xTitle="Number of jets (p_{T} > 25)", logy=True, moreY=10),
        Plot("nJet40", "nJet40", (10,-0.5,9.5), xTitle="Number of jets (p_{T} > 40)", logy=True, moreY=10),
        Plot("nBMedium", "nBJetMedium25", (8,-0.5,7.5), xTitle="Number of medium b-jets (p_{T} > 25)", logy=True, moreY=100),
        Plot("met", "MET_pt", (5,0,200), xTitle="p_{T}^{miss} (GeV)", logy=True, moreY=10),
]
result_plots = PlotMaker(cache = cache).book(procs_ttbb,lumi,cuts_ttbb,plots_ttbb).runAll()
## Now we normalize all signals to the sum of the backgrounds (this could go into plots.py)
for (key,plots) in result_plots:
    total = plots.totals["background"].Integral()
    for (proc,hist) in plots.histos:
        if proc.isSignal and hist.Integral() > 0:
            hist.Scale(total/hist.Integral())
## And we print with the option of not stacking the signals
printer2 = PlotSetPrinter(topRightText="L = %(lumi).1f fb^{-1} (13 TeV)", noStackSignals=True)
printer2.printSet(result_plots, "plots/004/{flow}")