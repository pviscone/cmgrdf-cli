from CMGRDF import *
import ROOT
from CMGRDF.histoWithNuisances import PostFitSetup

from CMGRDF.stat import DatacardWriter

LOCAL = "/scratch/gpetrucc" if os.path.exists("/scratch/gpetrucc") else "/data/shared"
P = localOrEOS("TREES_TTHH_2018C_150622", LOCAL, "/eos/cms/store/cmst3/group/tthlep") + "/{name}.root"
if P.startswith("/eos") and not os.path.isdir("/eos"):
    P = "root://eoscms.cern.ch/" + P


def mkMC(name, parts=0):
    if parts == 0:
        return MCSample(name, P, xsec="xsec")
    else:
        return MCSample(name, Source(name, [P.format(name=(f"{name}_part{i}")) for i in range(1, parts + 1)]), xsec="xsec")


mcSamples = dict(
    DY=MCGroup("DY", [mkMC("DYJetsToLL_M10to50_LO"), mkMC("DYJetsToLL_M50", 2)]),
    WJ=MCGroup("WJ", [mkMC(f"W{i}JetsToLNu_LO") for i in (1, 2, 3, 4)]),
    Ttch=MCGroup("Ttch", [mkMC("T_tch"), mkMC("TBar_tch")]),
    Tsch=MCGroup("Tsch", [mkMC("T_sch_lep")]),
    TW=MCGroup("TW", [mkMC("T_tWch_noFullyHad"), mkMC("TBar_tWch_noFullyHad")]),
    TT0l=mkMC("TTHad_pow"),
    TT1l=mkMC("TTSemi_pow", 2),
    TT2l=mkMC("TTLep_pow", 2),
    # top + X
    TTW=mkMC("TTWToLNu"),
    TTZ=mkMC("TTZToLLNuNu"),
    TWZ=mkMC("TWLL"),
    TZQ=mkMC("TZQToLL"),
    # ttH
    TTHBB=mkMC("TTHTobb_M125_pow"),  # ttH, H -> bb
    TTHNoBB=mkMC("TTHToNonbb_M125_pow"),  # ttH, any other than H -> bb
    TTHTT=mkMC("TTHToTauTau_M125_pow"),  # ttH, H -> tau tau
    TTHGG=mkMC("TTHToGG_M125_fxfx"),  # ttH, H -> gamma gamma
    # ttHH
    TTHH4B=mkMC("TTHHTo4b"),  # ttHH, HH -> 4b
    TTHHNo4B=mkMC("TTHHToNon4b"),  # ttHH, any other than HH -> 4b
    # dibosons (leptonic decays)
    WW2l=mkMC("WWTo2L2Nu"),
    WZ3l=mkMC("WZTo3LNu"),
    ZZ4l=mkMC("ZZTo4L"),
    # diphoton samples
    GGAll=mkMC("DiPhoton"),  # inclusive
    GG1B=mkMC("DiPhoton1B"),  # + 1 b quark
    GG2B=mkMC("DiPhoton2B"),  # + 2 b quarks
    TTG=mkMC("TTGJets"),  # ttbar + 1 photon + jets
    TTGG=mkMC("TTGG"),    # ttbar + 2 photons
)
dataSamples = [
    DataSample("EGamma", P.format(name="EGamma_Run2018C")),
    DataSample("SingleMuon", Source("SingleMuon", [P.format(name=f"SingleMuon_Run2018C_part{i}") for i in (1, 2)])),
]

## Common stuff
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
int findWlv(const ROOT::RVec<float> & Lep_pt, const ROOT::RVec<int> & LepZ) {
    int ret = -1;
    for (unsigned int i = 0, n = Lep_pt.size(); i < n; ++i) {
        if (i == LepZ[0] || i == LepZ[1]) continue;
        ret = i;
        break;
    }
    return ret;
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

cuts_tight = Flow("tight",
                  AddWeight("prescaleFromSkim", "prescaleFromSkim", onData=True, onDataDriven=True),
                  Cut("onrigger", "HLT_IsoMu24 || HLT_Ele32_WPTight_Gsf"),
                  ## Now we define a tighter lepton selection,
                  Define("LepGood_tightSel", "LepGood_pt > 10 && " +
                         "(abs(LepGood_pdgId) == 11 && LepGood_mvaFall17V2noIso_WP90 || " +  # MVA ID 90% efficiency WP for electrons (LepGood has instead the loose WP)
                         " abs(LepGood_pdgId) == 13 && LepGood_mediumId) &&" +             # Medium ID for muons (LepGood has no cut by mistake, should have had looseId)
                         "abs(LepGood_dxy) < 0.05 && abs(LepGood_dz) < 0.1 && " +           # cuts on the impact parameter, in cm (LepGood has no cut)
                         "LepGood_sip3d < 6 && "                                           # cut on the 3D impact parameter significance (LepGood has no cut)
                         "LepGood_miniPFRelIso_all < 0.15"),                                # tighter cut on isolation (LepGood has a cut at 0.4)
                  ## And now define nLepTight and LepTight_<var> copying from LepGood applying the selection
                  Define("nLepTight", "Sum(LepGood_tightSel)"),
                  [Define(f"LepTight_{x}", f"LepGood_{x}[LepGood_tightSel]") for x in ("pt", "eta", "phi", "mass", "charge", "pdgId", "dxy", "dz", "sip3d", "miniPFRelIso_all", "jetIdx")],
                  ## Now we can define a selection with 3 leptons
                  Cut("3l", "nLepTight >= 3"),
                  Cut("ptX1515", "LepTight_pt[0] > (abs(LepTight_pdgId[0])==11?35:25) && LepTight_pt[1] > 15 && LepTight_pt[2] > 15"),
                  ## Veto events with leptons at low invariant mass (m(ll) < 12 GeV), which are not well predicted by the simulations we use
                  Define("minMllTight", "minMll(LepTight_pt,LepTight_eta,LepTight_phi,LepTight_mass)"),
                  Cut("minMll12", "minMllTight > 12"),
                  ## Select a Z from the leptons
                  Define("lepZ", "findZll(LepTight_pt,LepTight_eta,LepTight_phi,LepTight_mass,LepTight_pdgId)"),
                  Cut("hasZ", "lepZ[0] >= 0"),  # if no Z is found, findZll returns {-1,-1} and the code below would fail
                  Define("mZll", "mass_2(LepTight_pt[lepZ[0]],LepTight_eta[lepZ[0]],LepTight_phi[lepZ[0]],LepTight_mass[lepZ[0]],LepTight_pt[lepZ[1]],LepTight_eta[lepZ[1]],LepTight_phi[lepZ[1]],LepTight_mass[lepZ[1]])"),
                  Cut("Zpeak", "mZll > 60 && mZll < 120"),
                  # Reconstruct a W
                  Define("lepW", "findWlv(LepTight_pt,lepZ)"),
                  Define("mtWlv", "mt_2(LepTight_pt[lepW],LepTight_phi[lepW],MET_pt,MET_phi)"),
                  # Clean the jets
                  Define("Jet_sel", "Jet_pt > 30 && abs(Jet_eta) < 2.4 && Jet_jetId > 1"),
                  Define("LepGood_forJetCleaning", "LepGood_tightSel && LepGood_pt > 15"),
                  Define("Jet_noLep", "cleanByIndex(Jet_sel,LepGood_forJetCleaning,LepGood_jetIdx)"),
                  [Define(f"JetGood_{v}", f"Jet_{v}[Jet_noLep]") for v in ("pt", "eta", "phi", "mass", "btagDeepFlavB")],
                  Define("nJet30", "Sum(JetGood_pt > 30)"),
                  Define("nBJetMedium30", "Sum(JetGood_pt > 30 && JetGood_btagDeepFlavB >= 0.2783)"),
                  Cut("3jets", "nJet30 >= 3"),
                  Cut("1b", "nBJetMedium30 >= 1"),
                  )
leps = [("e", 11), ("m", 13)]
Zcuts = dict((l + l, Cut(f"Z{l}{l}", f"abs(LepTight_pdgId[lepZ[0]]) == {pid}")) for (l, pid) in leps)
Wcuts = dict((l, Cut(f"W{l}v", f"abs(LepTight_pdgId[lepW]) == {pid}")) for (l, pid) in leps)
flavSplits = [
    cuts_tight.clone(f"tight_Z{ll}_W{l}v").append(Zcuts[ll], Wcuts[l]) for ll in ("ee", "mm") for l in ("e", "m")
]
procs_3l_tight = [
    Process("TopZ", [mcSamples["TTZ"], mcSamples["TZQ"], mcSamples["TWZ"]], label="t#bar{t}Z+tZ", fillColor=ROOT.kGreen + 1, signal=True),
    Process("TTW", [mcSamples["TTW"]], label="t#bar{t}W", fillColor=ROOT.kGreen + 3),
    Process("VZ", [mcSamples["WZ3l"], mcSamples["ZZ4l"]], label="WZ+ZZ", fillColor=ROOT.kRed - 7, normUncertainty=1.3),
    Process("DY", mcSamples["DY"], label="DY", fillColor=ROOT.kAzure + 10, normUncertainty=2.0),
    Process("WW", mcSamples["WW2l"], label="WW", fillColor=ROOT.kAzure + 2, normUncertainty=2.0),
    Process("TT", [mcSamples["TT2l"], mcSamples["TW"]], label="t#bar{t}+tW", fillColor=ROOT.kViolet - 4, normUncertainty=1.5),
    Data(dataSamples)
]
plots_3l_tight = [
    Plot("l1pt", "LepTight_pt[0]", (20, 20, 240), xTitle="p_{T}(l1)"),
    Plot("l2pt", "LepTight_pt[1]", (20, 00, 150), xTitle="p_{T}(l2)"),
    Plot("l3pt", "LepTight_pt[2]", (20, 00, 90), xTitle="p_{T}(l3)"),
    Plot("minMll", "minMllTight", (20, 0, 120), xTitle="min m(ll)", legend="TL"),
    Plot("mZll", "mZll", (40, 60, 120), xTitle="m(ll)", legend="TL"),
    Plot("met", "MET_pt", (20, 0, 240), xTitle="p_{T}^{miss} (GeV)"),
    Plot("mtWlv", "mtWlv", (20, 0, 160), xTitle="m(ll)", legend="TL"),
    Plot("nBMedium", "nBJetMedium30", (4, 0.5, 4.5), xTitle="Number of medium b-jets (p_{T} > 30)", logy=True, moreY=10),
    Plot("nJet", "nJet30", (5, 2.5, 7.5), xTitle="Number of jets (p_{T} > 30)", logy=True, moreY=10),
]

lumi = 6.90
ROOT.EnableImplicitMT(16)
maker = Processor(cache=SimpleCache())
maker.book(procs_3l_tight, lumi, cuts_tight, plots_3l_tight, withUncertainties=True)
for split in flavSplits:
    maker.book(procs_3l_tight, lumi, split, plots_3l_tight, withUncertainties=True)
result_plots = maker.runPlots()
printer = PlotSetPrinter(topRightText="L = %(lumi).1f fb^{-1} (13 TeV)", showRatio=True, maxRatioRange=(0, 2.49))
printer.printSet(result_plots, "plots/008/{flow}")

cardMaker = DatacardWriter(regularize=True, autoMCStats=False)
cardMaker.makeCards(result_plots, MultiKey(name="minMll"), "plots/008/datacards/flow_{flow}")

## Now we combine the datacards and run a fit
os.system("""
pushd plots/008/datacards &&
combineCards.py $(for f in flow_tight_Z*.txt; do echo .=$f; done)  > flow_combined.txt &&
for f in tight combined; do text2workspace.py flow_${f}.txt || break; done &&
for f in tight combined; do combine -M FitDiagnostics flow_${f}.root -n _${f} --customStartingPoint --setParameters r=1 || break; done &&
popd
""")

## And we make some post-fit plots
postfit = MultiReport()
for fit in ("tight", "combined"):
    fFitDiag = ROOT.TFile.Open(f"plots/008/datacards/fitDiagnostics_{fit}.root")
    fitResult = fFitDiag.Get("fit_b")
    postFitSetup = PostFitSetup(fitResult=fitResult)
    for key, plot in result_plots:
        plot.setPostFit(postFitSetup, applyIt=True)
        postfit.append(key, plot)
    printer.printSet(postfit, f"plots/008/postfit_{fit}/{{flow}}")
