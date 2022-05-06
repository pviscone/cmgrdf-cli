from math import ceil, hypot, sqrt
import re
import os, os.path
from array import array
import copy

import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.IgnoreCommandLineOptions = True

from flow import *
from plots import *

P="/eos/cms/store/cmst3/group/tthlep/rdftests"
mca_tthh = [
    Process("TTHH", [MCSample("TTHHToNon4b",P+"/{name}_RunIISummer20UL18NanoAODv9.root", xsec=1.)], label="t#bar{t}HH", fillColor=ROOT.kRed),
    Process("TTTT", [MCSample("TTTT",P+"/{name}_RunIISummer20UL18NanoAODv9.root", xsec=1.)], label="tt#bar{tt}", fillColor=ROOT.kAzure+1),
    Process("TTGG", [MCSample("TTGG",P+"/{name}_RunIISummer20UL18NanoAODv9.root", xsec=1.)], label="t#bar{t}\#gamma\#gamma", fillColor=ROOT.kOrange-2),
]
cuts_tthh = Flow("tthh",
        Cut("3j", "nJet >= 3"),
        Cut("1l", "nElectron >= 1 || nMuon >= 1"))
plots_tthh = [ 
        Plot("nJet", "nJet", (18,2.5,20.5), xTitle="Number of jets"),
        Plot("nJet30", "Sum(Jet_pt > 30)", (14,0.5,14.5), xTitle="Number of jets (p_{T} > 30)", logy=True, moreY=10),
        Plot("jpt", "Jet_pt", (20,0,200), xTitle="p_{T}(j)  (GeV)", logy=True),
]

lumi_tthh = 138.


ROOT.ROOT.EnableImplicitMT(4)
plots_tthh = makePlots(mca_tthh, [cuts_tthh], lumi_tthh, plots_tthh)
printer_tthh = PlotSetPrinter(topRightText="L = 138 fb^{-1} (13 TeV)")
printer_tthh.printSet(plots_tthh[0][1], "plots/001/tthh/cmgrdf")
