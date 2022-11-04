from CMGRDF import *
import ROOT

P="root://eoscms.cern.ch//eos/cms/store/cmst3/group/tthlep/rdftests/{name}_RunIISummer20UL18NanoAODv9.root"
mca = [
    Process("TTHH", [MCSample("TTHHToNon4b", P, xsec=1.)], label="t#bar{t}HH", fillColor=ROOT.kRed),
    Process("TTTT", [MCSample("TTTT", P, xsec=1.)], label="tt#bar{tt}", fillColor=ROOT.kAzure+1),
    Process("TTGG", [MCSample("TTGG", P, xsec=1.)], label="t#bar{t}#gamma#gamma", fillColor=ROOT.kOrange-2),
]
cuts = Flow("sr",
        Cut("3j", "nJet >= 3"),
        Cut("1l", "nElectron >= 1 || nMuon >= 1"))
plots = [ 
        Plot("nJet", "nJet", (18,2.5,20.5), xTitle="Number of jets"),
        Plot("nJet30", "Sum(Jet_pt > 30)", (14,0.5,14.5), xTitle="Number of jets (p_{T} > 30)", logy=True, moreY=10),
        Plot("jpt", "Jet_pt", (20,0,200), xTitle="p_{T}(j)  (GeV)", logy=True),
]

lumi = 138.

ROOT.ROOT.EnableImplicitMT(4)
plots = Processor().book(mca, lumi, cuts, plots).runPlots()
printer = PlotSetPrinter(topRightText="L = %s fb^{-1} (13 TeV)" % lumi)
printer.printSet(plots, "plots/001/mc/cmgrdf")