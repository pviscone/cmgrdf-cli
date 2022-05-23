import os
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gSystem.Load("libCMGRDF.so")
ROOT.gInterpreter.ProcessLine(".O3")
ROOT.gInterpreter.AddIncludePath(os.path.expandvars("${CMGRDF}/include"))
ROOT.gInterpreter.ProcessLine('#include "functions.h"')

from CMGRDF.utils import MultiKey, MultiReport, localOrEOS
from CMGRDF.data import MCSample, MCGroup, DataDrivenSample, DataSample, Process, Data
from CMGRDF.flow import Define, ReDefine, DefineDefault, Cut, AddWeight, AddWeightUncertainty, Flow
from CMGRDF.plots import Plot, PlotResult, PlotMaker, PlotSetPrinter
from CMGRDF.modifiers import Append, Insert