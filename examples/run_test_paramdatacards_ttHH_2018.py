from CMGRDF import *
import ROOT
from CMGRDF.histoWithNuisances import roofitizeReport

from CMGRDF.stat import DatacardWriter

P = localOrEOS("TREES_TTHH_GG_2018_150922", "/data/shared", "/eos/cms/store/cmst3/group/tthlep") + "/{name}.root"
if P.startswith("/eos") and not os.path.isdir("/eos"):
    P = "root://eoscms.cern.ch/" + P


def mkMC(name, parts=0):
    if parts == 0:
        return MCSample(name, P, xsec="xsec")
    else:
        return MCSample(name, Source(name, [P.format(name=(f"{name}_part{i}")) for i in range(1, parts + 1)]), xsec="xsec")


mcSamples = dict(
    TTHGG=mkMC("TTHToGG_M125_fxfx"),  # ttH, H -> gamma gamma
    # diphoton samples
    GG1B=mkMC("DiPhoton1B"),
    TTG=mkMC("TTGJets"),  # ttbar + 1 photon + jets
    TTGG=mkMC("TTGG"),    # ttbar + 2 photons
)
dataSamples = [
    DataSample("EGamma2018", Source("EGamma", [P.format(name=f"EGamma_Run2018{i}") for i in "ABCD"])),
]

## Common stuff
ROOT.gInterpreter.Declare("""
#include "Math/GenVector/LorentzVector.h"
#include "Math/GenVector/PtEtaPhiM4D.h"

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
                  Define("Photon_tightSel", "Photon_pt > 25 && abs(Photon_eta) < 2.5 && " +
                         "Photon_mvaID_WP90  && !Photon_pixelSeed && Photon_electronVeto"),
                  Define("nPhoTight", "Sum(Photon_tightSel)"),
                  [Define(f"PhoTight_{x}", f"Photon_{x}[Photon_tightSel]") for x in ("pt", "eta", "phi", "jetIdx")],
                  ## Now we can define a selection with 3 leptons
                  Cut("2g", "nPhoTight >= 2"),
                  Cut("pt35", "PhoTight_pt[0] > 35"),
                  Define("mgg", "mass_2(PhoTight_pt[0],PhoTight_eta[0],PhoTight_phi[0],0,PhoTight_pt[1],PhoTight_eta[1],PhoTight_phi[1],0)"),
                  Define("ptgg", "pt_2(PhoTight_pt[0],PhoTight_phi[0],PhoTight_pt[1],PhoTight_phi[1])"),
                  Cut("mggWin", "mgg > 100 && mgg < 150"),
                  # Clean the jets
                  Define("Jet_sel", "Jet_pt > 30 && abs(Jet_eta) < 2.4 && Jet_jetId > 1"),
                  Define("Jet_clean", "cleanByIndex(Jet_sel,Photon_tightSel,Photon_jetIdx)"),
                  [Define(f"JetGood_{v}", f"Jet_{v}[Jet_clean]") for v in ("pt", "eta", "phi", "mass", "btagDeepFlavB")],
                  Define("nJet30", "Sum(JetGood_pt > 30)"),
                  Define("nBJetMedium30", "Sum(JetGood_pt > 30 && JetGood_btagDeepFlavB >= 0.2783)"),
                  Define("nBJetLoose30", "Sum(JetGood_pt > 30 && JetGood_btagDeepFlavB >= 0.0490)"),
                  Cut("3jets", "nJet30 >= 4"),
                  Cut("1b", "nBJetMedium30 >= 1"),
                  )
procs_tight = [
    Process("TTHGG", [mcSamples["TTHGG"]], label="t#bar{t}H", fillColor=ROOT.kRed + 1, signal=True),
    Process("TTGG", [mcSamples["TTGG"]], label="t#bar{t}#gamma#gamma", fillColor=ROOT.kGreen + 1),
    Process("TTG", [mcSamples["TTG"]], label="t#bar{t}#gamma", fillColor=ROOT.kGreen + 3),
    Process("GGB", [mcSamples["GG1B"]], label="#gamma#gamma+b", fillColor=ROOT.kAzure + 2, normUncertainty=0.3),
    Data(dataSamples)
]
plots_tight = [
    Plot("mgg", "mgg", (25, 100, 150), xTitle="min m(ll)", legend="TL"),
    Plot("pt1", "PhoTight_pt[0]", (20, 20, 240), xTitle="p_{T}(#gamma1)"),
    Plot("pt2", "PhoTight_pt[1]", (20, 00, 150), xTitle="p_{T}(#gamma2)"),
    Plot("ptgg", "ptgg", (20, 00, 150), xTitle="p_{T}(#gamma#gamma)"),
    Plot("mggFine", "mgg", (100, 100, 150), xTitle="min m(ll)", legend="TL"),
    Plot("nBMedium", "nBJetMedium30", (4, 0.5, 4.5), xTitle="Number of medium b-jets (p_{T} > 30)", logy=True, moreY=10),
    Plot("nBLoose", "nBJetLoose30", (4, 0.5, 4.5), xTitle="Number of medium b-jets (p_{T} > 30)", logy=True, moreY=10),
    Plot("nJet", "nJet30", (6, 0.5, 6.5), xTitle="Number of jets (p_{T} > 30)", logy=True, moreY=10),
]

lumi = 59.80
cache = SimpleCache()
ROOT.EnableImplicitMT(16)
maker = Processor(cache=cache)
maker.book(procs_tight, lumi, cuts_tight, plots_tight, withUncertainties=True)
result_plots = maker.runPlots()
printer = PlotSetPrinter(topRightText="L = %(lumi).1f fb^{-1} (13 TeV)", showRatio=True, maxRatioRange=(0, 2.49))
#printer.printSet(result_plots, "plots/010/{flow}")

cardMaker = DatacardWriter()
cardMaker.makeCards(result_plots, MultiKey(name="mgg"), "plots/010/datacards/flow_{flow}")

## now we play a bit with RooFit
ROOT.gSystem.Load("libHiggsAnalysisCombinedLimit.so")
SIGNAME = "TTHGG"
BIN = cuts_tight.name
c1 = ROOT.TCanvas("c1", "c1")
mggPlotReport = result_plots.getByKey(MultiKey(name="mggFine"))
roofit = roofitizeReport(mggPlotReport)
roofit.imp(roofit.xvar)
roofit.factory("Gaussian::sig_ttH(%s, mean_ttH[125,110,130],sigma_ttH[1,0.5,5])" % roofit.xname)
roofit.factory("Exponential::sig_nonres(%s, slope_expo[0,-5,5])" % roofit.xname)
roosigpdf = roofit.factory("SUM::sigsumpdf(fSig[0.95,0.5,1]*sig_ttH,sig_nonres)")
roosigdata = mggPlotReport.histByProcName(SIGNAME).asRooDataHist(approxUnweight=True)
roosigpdf.fitTo(roosigdata, Range=(120, 130))
frame = roofit.xvar.frame()
roosigdata.plotOn(frame)
roosigpdf.plotOn(frame)
frame.Draw()
c1.Print("plots/010/tight/roofit_sigpdf.png")
roofit.workspace.var("mean_ttH").setConstant(True)
roofit.workspace.var("sigma_ttH").setConstant(True)
roofit.factory("Exponential::bkg_expo(%s, slope_expo[0,-5,5])" % roofit.xname)
roofit.factory("Chebychev::bkg_poly(%s, { p0_poly[0,-1,1], p1_poly[0,-1,1] } )" % roofit.xname)
roofit.factory("GenericPdf::bkg_pow(\"TMath::Power(@0,@1)\", {%s, expo_pow[-3,-6,-0.001]})" % roofit.xname)
roofit.imp(ROOT.RooCategory("bkg_index", "Index of the bkg pdf"))
bkgnames = "expo poly pow".split()
pdflist = ROOT.RooArgList()
for x in bkgnames:
    pdflist.add(roofit.workspace.pdf("bkg_" + x))
roofit.imp(ROOT.RooMultiPdf("bkg_multi", "All pdfs", roofit.workspace.cat("bkg_index"), pdflist))
NDATA = mggPlotReport.histData().Integral()
NSIG = mggPlotReport.histByProcName(SIGNAME).Integral()
roopdfs = dict((x, roofit.factory(f"SUM::totpdf_{x}(prod::nsig_{x}(mu_{x}[1,-5,20],{NSIG})*sig_ttH,bkg_{x}_norm[0,{2*NDATA}]*bkg_{x})")) for x in bkgnames)
roopdf = roofit.factory(f"SUM::totpdf(prod::nsig(mu[1,-5,10],{NSIG})*sig_ttH,bkg_multi_norm[0,{2*NDATA}]*bkg_multi)")
roodata = mggPlotReport.histData().asRooDataHist()
#roopdf.fitTo(roodata) # fitting with MultiPDF won't work in plain RooFit
for x in roopdfs:
    roopdfs[x].fitTo(roodata)
c1.Clear()
frame = roofit.xvar.frame()
roodata.plotOn(frame)
for i, x in enumerate(bkgnames):
    roopdfs[x].plotOn(frame, LineColor=(ROOT.kCyan + i))
    roopdfs[x].plotOn(frame, LineColor=(ROOT.kMagenta + i), Components="bkg_*")
#roopdf.plotOn(frame, Components="bkg_*", LineColor=ROOT.kRed+3)
#roopdf.plotOn(frame, LineColor=(ROOT.kGreen+3))
frame.Draw()
c1.Print("plots/010/tight/roofit.png")
roofit.imp(roodata)
roofit.workspace.writeToFile("plots/010/datacards/flow_param.input.root")
roofit.workspace.Print("")
datacard = open("plots/010/datacards/flow_param.txt", "w")
datacard.write(f"""
shapes {SIGNAME}  * flow_param.input.root w:sig_ttH
shapes background * flow_param.input.root w:bkg_multi
shapes data_obs   * flow_param.input.root w:data
---------------
bin {BIN}
observation {NDATA}
------------------------------
bin          {BIN}      {BIN}
process      {SIGNAME}  background
process      0          1
rate         {NSIG}     1
------------------------------
lumi lnN     1.026      -
bkg_index discrete
""")
