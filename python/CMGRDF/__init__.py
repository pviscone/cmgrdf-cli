import os
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gSystem.Load("libCMGRDF.so")
ROOT.gInterpreter.ProcessLine(".O3")
ROOT.gInterpreter.AddIncludePath(os.path.expandvars("${CMGRDF}/include"))
ROOT.gInterpreter.ProcessLine('#include "functions.h"')

from CMGRDF.utils import MultiKey, MultiReport, localOrEOS, NormUncertainty
from CMGRDF.data import Source, MCSample, MCGroup, DataDrivenSample, DataSample, Process, Data
from CMGRDF.flow import Define, ReDefine, DefineDefault, Vary, Cut, AddWeight, AddWeightUncertainty, Flow, Yield
from CMGRDF.plots import Plot, PlotResult, PlotSetPrinter
from CMGRDF.processor import Processor
from CMGRDF.modifiers import Append, Insert
from CMGRDF.cache import SimpleCache