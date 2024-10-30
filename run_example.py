import ROOT
import multiprocessing

from CMGRDF import Processor, PlotSetPrinter
from CMGRDF.cms.eras import lumis as lumi
from data import AddMC, AddData, all_data

import cpp_functions
cpp_functions.load()
#! ------------------------- RDF CONFIG -------------------------- !#
verbosity = ROOT.Experimental.RLogScopedVerbosity(
    ROOT.Detail.RDF.RDFLogChannel(), ROOT.Experimental.ELogLevel.kInfo
)
cpu=multiprocessing.cpu_count()
#! Set number of cores (max by default)
ROOT.EnableImplicitMT(cpu)

#! ---------------------- IMPORTS TO CHANGE ----------------------- !#
#! WIP: ADD CLI

from data.data_example import DataDict

#from mcc.mcc_sos_allYears_disp import mccFlow
mccFlow = None

from data.MCProcesses_example import all_processes
from cfg.cfg_example import era_paths_Data, era_paths_MC, PFs, PMCs
from plots.plots_example import plots
from flows.flow_example import flow

eras=["2022"]
outfolder="temp/plots_{flow}_{era}/"
#! ---------------------- DATASET BUILDING ----------------------- !#
#! They create the datasets, adding everything to all_data list
AddData(DataDict, era_paths=era_paths_Data, friends=PFs, mccFlow=mccFlow)
AddMC(all_processes, era_paths=era_paths_MC, friends=PMCs, mccFlow=mccFlow)
#breakpoint()
#! ---------------------- RUN THE ANALYSIS ----------------------- !#
maker = Processor().book(all_data, lumi, flow, plots, eras=eras).runPlots()
printer = PlotSetPrinter(
    topRightText="L = %(lumi).1f fb^{-1} (13 TeV)", stack=True, maxRatioRange=(0,2), showRatio=True
).printSet(maker, outfolder)
