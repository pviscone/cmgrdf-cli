from CMGRDF import *
from CMGRDF.cms.eras import *
from CMGRDF.cms.MuonRoccoR import MuRocCorrMC2018
from CMGRDF.cms.MuonSFs import MuonSFs
import ROOT

P=localOrEOS("TREES_TTHH_2018C_150622","/data/shared","/eos/cms/store/cmst3/group/tthlep")+"/{name}.root"
if P.startswith("/eos") and not os.path.isdir("/eos"): P = "root://eoscms.cern.ch/"+P
print(f"Reading from {P}");

def mkMC(name, parts=0, normUncertainties=[]):
    uncertainties = normUncertainties[:] + [lumiUncerty2018]
    if parts == 0:
        return MCSample(name, P, xsec="xsec", normUncertainties=uncertainties)
    else:
        return MCSample(name, Source(name,[P.format(name=(f"{name}_part{i}")) for i in range(1,parts+1)]), xsec="xsec", normUncertainties=uncertainties)

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
    ROOT::RVec<int> mask(Jet_sel);
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
        AddWeight("prescaleFromSkim", onData=True, onDataDriven=True),
        Define("Muon_good", "Muon_mediumPromptId && Muon_pfIsoId > 1"), # >1 is PFIsoLoose
        Define("Muon_forJetCleaning", "Muon_good && Muon_pt > 15"),
        Define("Electron_good", "Electron_mvaFall17V2Iso_WP90"),
        Define("Electron_forJetCleaning", "Electron_good && Electron_pt > 20"),
        Define("Jet_sel","Jet_pt > 25 && abs(Jet_eta) < 2.4 && Jet_jetId > 1"),
        Define("Jet_noMu","cleanByIndex(Jet_sel,Muon_forJetCleaning,Muon_jetIdx)"),
        Define("Jet_noLep","cleanByIndex(Jet_noMu,Electron_forJetCleaning,Electron_jetIdx)"),
        [ Define(f"JetGood_{v}",f"Jet_{v}[Jet_noLep]") for v in ("pt","eta","phi","mass","btagDeepFlavB") ],
        [ Define(f"JetGood_{v}",f"Jet_{v}[Jet_noLep]", onData=False, onDataDriven=False) for v in ("hadronFlavour","genJetIdx") ],
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
        Process("Top", [mcSamples["TT2l"],mcSamples["TW"],mcSamples["TT0l"],mcSamples["TT1l"],mcSamples["Ttch"],mcSamples["Tsch"]], label="Top", fillColor=ROOT.kViolet-4, normUncertainty=1.1),
        Process("WJ", mcSamples["WJ"], label="W+jets", fillColor=ROOT.kOrange+1, normUncertainty=1.3),
        Data(dataSamples)
]
cuts_Zmm = Flow("Zmm",
        commonSteps,
        Cut("trigger", "HLT_IsoMu24"),
        Cut("2lsfos", "nMuon >= 2 && Muon_pdgId[0] == -Muon_pdgId[1]"),
        Cut("pt2515", "Muon_pt[0] > 25 && Muon_pt[1] > 15"),
        Cut("idiso",  "Muon_good[0] && Muon_good[1]"),
        Define("mll", "mass_2(Muon_pt[0],Muon_eta[0],Muon_phi[0],Muon_mass[0],Muon_pt[1],Muon_eta[1],Muon_phi[1],Muon_mass[1])"),
        Cut("mll12", "mll > 12")
)
cuts_Zee = Flow("Zee",
        commonSteps,
        Cut("trigger", "HLT_Ele32_WPTight_Gsf"),
        Cut("2lsfos", "nElectron >= 2 && Electron_pdgId[0] == -Electron_pdgId[1]"),
        Cut("pt2515", "Electron_pt[0] > 25 && Electron_pt[1] > 15"),
        Cut("idiso",  "Electron_good[0] && Electron_good[1]"),
        Define("mll", "mass_2(Electron_pt[0],Electron_eta[0],Electron_phi[0],Electron_mass[0],Electron_pt[1],Electron_eta[1],Electron_phi[1],Electron_mass[1])"),
        Cut("mll12", "mll > 12")
)
plots_Zll = [ 
        Plot("mll", "mll", (120,60,120), xTitle="m(ll)", legend="TL", includeOverflows=False),
        Plot("nJet", "nJet25", (12,-0.5,11.5), xTitle="Number of jets (p_{T} > 25)", logy=True, moreY=10),
        Plot("nJet40", "nJet40", (8,-0.5,7.5), xTitle="Number of jets (p_{T} > 40)", logy=True, moreY=10),
        Plot("nBLoose", "nBJetLoose25", (6,-0.5,5.5), xTitle="Number of loose b-jets (p_{T} > 25)", logy=True, moreY=10),
        Plot("nBMedium", "nBJetMedium25", (6,-0.5,5.5), xTitle="Number of medium b-jets (p_{T} > 25)", logy=True, moreY=10),
        Plot("met", "MET_pt", (120,0,120), xTitle="p_{T}^{miss} (GeV)"),
]
plots_Zmm = plots_Zll + [ 
        Plot("l1pt", "Muon_pt[0]", (100,20,120), xTitle="p_{T}(l1)"),
        Plot("l2pt", "Muon_pt[1]", (100,00,100), xTitle="p_{T}(l2)"),
        Plot("l1eta", "Muon_eta[0]", (50,-2.5,2.5), xTitle="#eta_{T}(l1)"),
        Plot("l2eta", "Muon_eta[1]", (50,-2.5,2.5), xTitle="#eta_{T}(l2)"),
]
plots_Zmm_corr = plots_Zmm + [ 
        Plot("l1sf", "Muon_SF_MediumPromptId_LooseIso[0]", (40,0.95,1.05), xTitle="SF(l1)", mcOnly=True),
        Plot("l2sf", "Muon_SF_MediumPromptId_LooseIso[1]", (40,0.95,1.05), xTitle="SF(l2)", mcOnly=True),
]
plots_Zee = plots_Zll + [ 
        Plot("l1pt", "Electron_pt[0]", (100,20,120), xTitle="p_{T}(l1)"),
        Plot("l2pt", "Electron_pt[1]", (100,00,100), xTitle="p_{T}(l2)"),
        Plot("l1eta", "Electron_eta[0]", (50,-2.5,2.5), xTitle="#eta_{T}(l1)"),
        Plot("l2eta", "Electron_eta[1]", (50,-2.5,2.5), xTitle="#eta_{T}(l2)"),
]
muIDsf = [ 
        MuonSFs[("MediumPromptId_LooseIso","2018")], # these puts them as variables
        AddWeight("MuonIDIsoSF", "Muon_SF_MediumPromptId_LooseIso[0]*Muon_SF_MediumPromptId_LooseIso[1]")
]
cuts_corr_Zmm = cuts_Zmm.clone("Zmm_corr").prepend(MuRocCorrMC2018).append(muIDsf)

lumi = 6.90
cache = SimpleCache()
ROOT.EnableImplicitMT(16)
maker = Processor(cache = cache)
#maker.book(procs_Zll,lumi,cuts_Zee,plots_Zee)
maker.book(procs_Zll,lumi,cuts_Zmm,plots_Zmm, withUncertainties=True)
maker.book(procs_Zll,lumi,cuts_Zmm, Yield("all"), withUncertainties=True)
maker.book(procs_Zll,lumi,cuts_corr_Zmm,plots_Zmm_corr, withUncertainties=True)
maker.book(procs_Zll,lumi,cuts_corr_Zmm, Yield("all"), withUncertainties=True)
result_plots = maker.runPlots()
printer = PlotSetPrinter(topRightText="L = %(lumi).1f fb^{-1} (13 TeV)", showRatio=True, maxRatioRange=(0.7,1.399), fixRatioRange=True)
printer.printSet(result_plots, "plots/004sf/{flow}")

yields = maker.runYields()
for flow in cuts_Zmm, cuts_corr_Zmm:
    print(f"\nYields for {flow.name}:")
    for proc in procs_Zll:
        y = yields.getByKey(MultiKey(flow=flow.name, process=proc.name, name="all"))[-1]
        ysyst = y.systAsymm()
        print("   %-10s: %10.2f +- %8.1f (stat) %+9.1f/%+9.1f (syst)" % (proc.name, y.central, y.stat, ysyst[0], ysyst[1]))
