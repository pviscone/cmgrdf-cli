# flake8: noqa: F401
# pyright: reportUnusedImport=false
import os
import ROOT  # type: ignore
ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.IgnoreCommandLineOptions = True

from CMGRDF.init import Declare, ProcessLine, AddHeader, LoadLibrary, GlobalConfigHash
LoadLibrary("libCMGRDF.so")
ProcessLine(".O3")
AddHeader("functions.h")
AddHeader("jsonFilter.h")
if "ONNXRUNTIME" in os.environ:
    LoadLibrary("libonnxruntime.so", "${ONNXRUNTIME}/lib")
    AddHeader("OnnxDNNEvaluator.h", extraIncludePaths=["${ONNXRUNTIME}/include"])

from CMGRDF.utils import MultiKey, MultiReport, localOrEOS, NormUncertainty
from CMGRDF.data import Source, MCSample, MCGroup, DataDrivenSample, DataSample, Process, Data
from CMGRDF.flow import Define, ReDefine, DefineDefault, Alias, Vary, Cut, AddWeight, AddWeightUncertainty, Marker, Flow, Yield, Range
from CMGRDF.snapshot import Snapshot
from CMGRDF.plots import Plot, PlotResult, PlotSetPrinter
from CMGRDF.processor import Processor
from CMGRDF.modifiers import Append, Insert
from CMGRDF.cache import SimpleCache

# Record the state after initialization, for further study
_initialConfigHash = GlobalConfigHash()
