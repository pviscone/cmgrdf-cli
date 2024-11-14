# flake8: noqa: F401
import os
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gSystem.Load("libCMGRDF.so")
ROOT.gInterpreter.ProcessLine(".O3")
ROOT.gInterpreter.AddIncludePath(os.path.expandvars("${CMGRDF}/include"))
ROOT.gInterpreter.ProcessLine('#include "functions.h"')
ROOT.gInterpreter.ProcessLine('#include "jsonFilter.h"')
if "ONNXRUNTIME" in os.environ:
    ROOT.gInterpreter.AddIncludePath(os.path.expandvars("${ONNXRUNTIME}/include"))
    ROOT.gInterpreter.ProcessLine('#include "OnnxDNNEvaluator.h"')

from CMGRDF.utils import MultiKey, MultiReport, localOrEOS, NormUncertainty
from CMGRDF.data import Source, MCSample, DataDrivenSample, DataSample, Process, Data
from CMGRDF.flow import Define, ReDefine, DefineDefault, Alias, Vary, Cut, AddWeight, AddWeightUncertainty, Marker, Flow, Yield, Range
from CMGRDF.snapshot import Snapshot
from CMGRDF.plots import Plot, PlotResult, PlotSetPrinter
from CMGRDF.processor import Processor
from CMGRDF.modifiers import Append, Insert
from CMGRDF.cache import SimpleCache
