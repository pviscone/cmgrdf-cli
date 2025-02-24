from math import hypot
import hashlib
import re
import os
from array import array
from typing import Any, Literal, Optional

import ROOT  # type: ignore
from CMGRDF.histoWithNuisances import HistoWithNuisances, PostFitSetup, RooFitContext, listAllNuisances, mergePlots
from CMGRDF.utils import Options, MultiReport, recursiveHash, safeName
from CMGRDF.data import Sample, Process
from CMGRDF.flow import Target


def _unTLatex(string : str) -> str:
    """Replaces a root-formatted string with plaintext"""
    string = string.replace("#chi", "x").replace("#rightarrow", "->").replace("#minus", "-")
    string = re.sub(r"#(mu|tau|gamma)", r"\1", string)
    string = re.sub(r"#bar\{(\w+)\}", r"\1bar", string)
    string = re.sub(r"[\^_]\{([012+\-])\}", r"\1", string)
    return string


class Plot(Target):
    def __init__(self,
                 name,
                 *args : Any,
                 typ : Literal["Histo1D", "Histo2D"] = "Histo1D",
                 mcOnly : bool = False,
                 cut : Optional[str] = None,
                 weight : Optional[str] = "weight",
                 **options):
        super().__init__(name, mcOnly=mcOnly)
        for k, v in options.items():
            setattr(self, k, v)
        self.type = typ
        if typ == "Histo1D":
            self._expr = args[0]
            if isinstance(args[1], list):
                self._bins = [float(e) for e in args[1]]
            elif isinstance(args[1], tuple):
                self._bins = tuple([float(e) if idx != 0 else int(e) for idx, e in enumerate(args[1])])
            else:
                raise ValueError(f"Invalid type for bins: {type(args[1])}")
            self.attach = self.bookHisto1D
            self.finish = self.finishHisto1D
            self.style = self.styleHisto1D
            self._forEquals = (self._expr, self._bins,
                               [self.getOpt(x) for x in ("includeOverflows", "includeOverflow", "includeUnderflow")])
            if isinstance(self._bins, list):
                self._model = ROOT.RDF.TH1DModel(self.name, self.getOpt("title", self.name), len(self._bins) - 1, array('f', self._bins))
            else:
                nbins, low, high = self._bins
                self._model = ROOT.RDF.TH1DModel(self.name, self.getOpt("title", self.name), int(nbins), low, high)
            self.template = self._model.GetHistogram()
        elif typ == "Histo2D":
            self._expr = args[0]
            if isinstance(args[1], list):
                self._bins = [[float(e) for e in ax] for ax in args[1]]
            elif isinstance(args[1], tuple):
                self._bins = tuple([float(e) if idx not in [0, 3] else int(e) for idx, e in enumerate(args[1])])
            else:
                raise ValueError(f"Invalid type for bins: {type(args[1])}")
            self.attach = self.bookHisto2D
            self.finish = self.finishHisto2D
            self.style = self.styleHisto2D
            self._forEquals = (self._expr, self._bins,
                               [self.getOpt(x) for x in ("includeOverflows", "includeOverflow", "includeUnderflow")])
            if isinstance(self._bins, list):
                binsx = self._bins[0]
                binsy = self._bins[1]
                self._model = ROOT.RDF.TH2DModel(self.name, self.getOpt("title", self.name), len(binsx) - 1, array('f', binsx), len(binsy) - 1, array('f', binsy))
            else:
                nbinsx, lowx, highx, nbinsy, lowy, highy = self._bins
                self._model = ROOT.RDF.TH2DModel(self.name, self.getOpt("title", self.name), int(nbinsx), lowx, highx, int(nbinsy), lowy, highy)
            self.template = self._model.GetHistogram()
        else:
            raise NotImplementedError(f"Plot not implemented for {typ}")

        self.cut = cut
        self.weight = weight
        self.hashed_weight = weight
        self._bigHash = None

    def __getstate__(self):
        return dict(name=self.name,
                    type=self.type,
                    expr=self._expr,
                    bins=self._bins,
                    cut=self.cut,
                    options=dict((k, getattr(self, k)) for k in dir(self) if not k.startswith("_")),
                    model=self._model,
                    template=self.template,
                    _forEquals=self._forEquals)

    def __setstate__(self, state):
        self.name = state['name']
        self.type = state['type']
        self._expr = state['expr']
        self._bins = state['bins']
        self.cut = state['cut']
        for k, v in state['options'].items():
            setattr(self, k, v)
        self._model = state['model']
        self.template = state['template']
        self._bigHash = None
        self._forEquals = state['_forEquals']

    def _prepareExpr(self, rdf : Any, expr: str, name : str) -> tuple[Any, str]:
        hashed_weight_col = "__plot_weight_"+hashlib.sha1(self.weight.encode('utf-8')).hexdigest()
        if self.weight != "weight":
            if hashed_weight_col not in rdf.GetColumnNames():
                rdf2 = rdf.Define(hashed_weight_col, self.weight)
            self.hashed_weight = hashed_weight_col
        else:
            rdf2 = rdf

        if expr in rdf2.GetColumnNames():
            return (rdf2, expr)
        #print("Will create a new expression for plot "+self.name)
        if self.cut is not None:
            rdf2 = rdf2.Filter(self.cut)
            rdf2 = rdf2.Define(name, expr)
        else:
            rdf2 = rdf2.Define(name, expr)
        rdf2._from = rdf
        return (rdf2, name)

    def getOpt(self, name : str, default=None) -> Any:
        return getattr(self, name, default)

    def hasOpt(self, name : str) -> bool:
        return hasattr(self, name)

    def bookHisto1D(self, rdf : Any, sample : Sample, era : Optional[str], withUncertainties : bool) -> Any:
        rdf, expr = self._prepareExpr(rdf, self._expr, self.name + "__plot_expr_")
        ret = rdf.Histo1D(self._model, expr, self.hashed_weight)
        ret._from = rdf
        return ret

    def bookHisto2D(self, rdf : Any, sample : Sample, era : Optional[str], withUncertainties : bool) -> Any:
        rdf, expr_y = self._prepareExpr(rdf, self._expr.split(":")[0], self.name + "__plot_expr_y")
        rdf, expr_x = self._prepareExpr(rdf, self._expr.split(":")[1], self.name + "__plot_expr_x")
        ret = rdf.Histo2D(self._model, expr_x, expr_y, self.hashed_weight)
        ret._from = rdf
        return ret

    def finishHisto1D(self, value : Any, sample : Sample, era : Optional[str]) -> Any:
        """Make changes to the plot that affect the contents"""
        plot = value
        ## Contents
        if self.getOpt('includeOverflows', True) or self.getOpt('includeUnderflow', False):
            plot.SetBinContent(1, plot.GetBinContent(0) + plot.GetBinContent(1))
            plot.SetBinError(1, hypot(plot.GetBinError(0), plot.GetBinError(1)))
            plot.SetBinContent(0, 0)
            plot.SetBinError(0, 0)
        if self.getOpt('includeOverflows', True) or self.getOpt('includeOverflow', False):
            n = plot.GetNbinsX()
            plot.SetBinContent(n, plot.GetBinContent(n + 1) + plot.GetBinContent(n))
            plot.SetBinError(n, hypot(plot.GetBinError(n + 1), plot.GetBinError(n)))
            plot.SetBinContent(n + 1, 0)
            plot.SetBinError(n + 1, 0)
        return plot

    def finishHisto2D(self, value : Any, sample : Sample, era : Optional[str]) -> Any:
        return value

    def styleHisto(self, plot : Any, process : Process):
        """Common for 2D and 1D"""

        plot.SetTitle(self.getOpt('title', self.name))
        ## Graphics
        if process.getOpt('fillColor', None) is not None:
            plot.SetFillColor(process.getOpt('fillColor', 0))
            plot.SetFillStyle(process.getOpt('fillStyle', 1001))
        else:
            plot.SetFillStyle(0)
            plot.SetLineWidth(process.getOpt('lineWidth', 1))

        plot.SetLineColor(process.getOpt('lineColor', 1))
        plot.SetLineStyle(process.getOpt('lineStyle', 1))
        plot.SetMarkerColor(process.getOpt('markerColor', 1))
        plot.SetMarkerStyle(process.getOpt('markerStyle', 20))
        plot.SetMarkerSize(process.getOpt('markerSize', 1.1))
        plot.GetXaxis().SetTitleFont(42)
        plot.GetYaxis().SetTitleFont(42)
        plot.GetXaxis().SetLabelFont(42)
        plot.GetYaxis().SetLabelFont(42)
        return plot

    def styleHisto1D(self, plot : Any, process : Process) -> Any:
        plot = self.styleHisto(plot, process)

        """Make changes to the plot that affect only the style"""
        ## Axis
        plot.GetXaxis().SetTitle(self.getOpt('xTitle', self._expr))
        if self.getOpt('xBinLabels', None) is not None:
            for (i, l) in enumerate(self.getOpt('xBinLabels')):
                plot.GetXaxis().SetBinLabel(i + 1, l)
        return plot

    def styleHisto2D(self, plot : Any, process : Process) -> Any:
        plot = self.styleHisto(plot, process)
        return plot

    def __eq__(self, other) -> bool:
        if other.__class__ == Plot:
            if self.name != other.name:
                return False
            if self.type != other.type:
                return False
            return self._forEquals == other._forEquals
        return False

    def __hash__(self) -> int:
        return hash(self.bigHash())

    def bigHash(self) -> str:
        if not self._bigHash:
            self._bigHash = recursiveHash(self.name, self.type, self._forEquals)
        return self._bigHash

    def longId(self) -> str:
        return "%s-%s" % (safeName(self), self.bigHash())


class PlotResult:
    """A plot, with the specifications, the histograms with all the individual components and possibly some totals"""

    def __init__(self,
                 plot : Plot,
                 histos : list[tuple[Process, Any]],
                 fillTotals : bool = True):
        self.spec = plot
        self.name = plot.name
        self.template = self.spec.template
        self.histos = [(k, h if isinstance(h, HistoWithNuisances) else HistoWithNuisances(h)) for (k, h) in histos]
        self.totals : dict[Literal["signal", "background"], HistoWithNuisances] = {}
        self.lumi : Optional[float] = None
        self._roofit : Optional[RooFitContext] = None
        self._roofitPOI : Optional[Any] = None
        if fillTotals:
            self.fillTotals()

    def __getstate__(self):
        return dict(name=self.name, histos=self.histos, spec=self.spec, lumi=self.lumi, totals=self.totals, template=self.template)

    def __setstate__(self, state):
        self.name = state['name']
        self.histos = state['histos']
        self.spec = state['spec']
        self.lumi = state['lumi']
        self.totals = state['totals']
        self.template = state['template']

    def __getattr__(self, key : str) -> Any:
        return getattr(self.spec, key)

    def toJSON(self) -> dict[str, Any]:
        return dict(name=self.name, histos=dict((p.name, h.toJSON()) for (p, h) in self.histos))

    def histByProcName(self, procName) -> Optional[HistoWithNuisances]:
        for (p, h) in self.histos:
            if p.name == procName:
                return h
        return None

    def histData(self) -> Optional[HistoWithNuisances]:
        for (p, h) in self.histos:
            if p.isData:
                return h
        return None

    def fillTotals(self) -> None:
        sigs, bkgs = [], []
        for k, h in self.histos:
            if k.isSignal:
                sigs.append(h)
            elif not k.isData:
                bkgs.append(h)
        if sigs:
            self.totals["signal"] = mergePlots("signal", sigs)
        if bkgs:
            self.totals["background"] = mergePlots("background", bkgs)

    def initRooFit(self,
                   workspace : Optional[Any] = None,
                   xvarName : str = "x",
                   density : bool = False,
                   context : Optional[RooFitContext] = None) -> RooFitContext:
        """Set up RooFit for all the plots"""
        if self._roofit:
            print(f"Warning, calling initRooFit twice on PlotResult {self.name}")
        # sanity check all inputs, and get one representative histogram
        h0 = None
        for k, h in self.histos:
            if k.isData:
                continue
            if not str(h.raw().ClassName()).startswith("TH1"):
                raise RuntimeError("element %s (%s, %s) is not a TH1" % (h, h.GetName() if h else "<nil>", h.ClassName() if h else "<nil>"))
            if h.Integral() <= 0:
                continue
            if h0 is None:
                h0 = h
        if h0 is None:
            raise RuntimeError("Empty report")
        roofit = context
        if context is not None:
            if workspace is not None and workspace != context.workspace:
                raise RuntimeError("Mismatch between workspaces")
            workspace = context.workspace
        else:
            # setup the context
            if workspace is None:
                workspace = ROOT.RooWorkspace("w", "w")
            if not hasattr(workspace, 'nodelete'):
                workspace.nodelete = []
            roofit = RooFitContext(workspace)
        assert (roofit is not None) and (workspace is not None)
        if not roofit.xvar:
            # create the x variable
            roofit.prepareXVar(h0, density, name=xvarName)
        for nuis in listAllNuisances(self.histos):
            if not workspace.arg(nuis):
                roofit.factory("%s[0,-7,7]" % nuis)
        # now roofitise all objects
        for k, h in self.histos:
            h.setupRooFit(roofit)
        # and return the context
        self._roofit = roofit
        return self._roofit

    def getRooFit(self) -> RooFitContext:
        return self._roofit if self._roofit is not None else self.initRooFit()

    def setPostFit(self, posfit : PostFitSetup, applyIt : bool, signalPOI : Optional[str] = "r") -> None:
        if not self._roofit:
            self.initRooFit()
        assert self._roofit
        if signalPOI is not None and signalPOI != "":
            poiVar = self._roofit.workspace.var(signalPOI)
            if not poiVar:
                poiVar = self._roofit.workspace.factory("%s[1]" % signalPOI)
                poiVar.setConstant(False)
                poiVar.removeRange()
            self._roofitPOI = poiVar
        for (p, h) in self.histos:
            if not p.isData:
                h.setPostFitInfo(posfit, applyIt)
                if p.isSignal:
                    h.addRooFitScaleFactor(self._roofitPOI)
        # remake totals
        self.fillTotals()


def printPlot(args):
    return _printPlot(*args)


def _printPlot(plot, path : str, txt, stack, noStackSignals) -> None:
    os.makedirs(path, exist_ok=True)
    outputName = plot.name
    outputTDir = ROOT.TFile.Open("%s/%s.root" % (path, outputName), "RECREATE")
    formats = "root"
    if txt:
        formats += ",txt"
    print(f"Printing {outputName} in {path} (formats: {formats})")

    total = HistoWithNuisances(plot.template)
    total.SetName(outputName + "_total")

    data = []
    for (proc, hist) in reversed(plot.histos):
        if proc.isData:
            data.append((proc, hist))
            continue
        if stack and not (proc.isSignal and noStackSignals):
            total += hist

        if outputTDir:
            hist.writeToFile(outputTDir)

    for dproc, dhist in data:
        blind = plot.getOpt('blinded', "None")
        xblind = [9e99, -9e99]
        if re.match(r'(bin|x)\s*([<>]?)\s*(\+|-)?\d+(\.\d+)?|(\+|-)?\d+(\.\d+)?\s*<\s*(bin|x)\s*<\s*(\+|-)?\d+(\.\d+)?', blind):
            xfunc = (lambda h, b: b) if 'bin' in blind else (lambda h, b : h.GetXaxis().GetBinCenter(b))
            test = eval("lambda bin : " + blind) if 'bin' in blind else eval("lambda x : " + blind)
            (dproc, hdata) = data
            for b in range(1, hdata.GetNbinsX() + 1):
                if test(xfunc(hdata, b)):
                    print("blinding bin %d, x = [%s, %s]" % (b, hdata.GetXaxis().GetBinLowEdge(b), hdata.GetXaxis().GetBinUpEdge(b)))
                    hdata.SetBinContent(b, 0)
                    hdata.SetBinError(b, 0)
                    xblind[0] = min(xblind[0], hdata.GetXaxis().GetBinLowEdge(b))
                    xblind[1] = max(xblind[1], hdata.GetXaxis().GetBinUpEdge(b))
            print("final blinded range x = [%s, %s]" % (xblind[0], xblind[1]))
        elif blind != "None":
            raise RuntimeError("Unrecongnized value for 'Blinded' option, stopping here")
        if outputTDir:
            dhist.writeToFile(outputTDir)
        ### FIXME restore?
        #if xblind[0] < xblind[1]:
        #    blindbox = ROOT.TBox(xblind[0],total.GetYaxis().GetXmin(),xblind[1],total.GetMaximum())
        #    blindbox.SetFillColor(ROOT.kBlue+3)
        #    blindbox.SetFillStyle(3944)
        #    blindbox.Draw()
        #    dhist.xblind = blindbox # so it doesn't get deleted
        #if options.doStatTests:
        #    doStatTests(total, dhist, options.doStatTests, legendCorner=plot.getOpt('legend','TR'))
    if outputTDir:
        total.writeToFile(outputTDir)
        outputTDir.Close()

    if txt:
        if "TProfile" in total.ClassName():
            return
        dump = open("%s/%s.%s" % (path, outputName, "txt"), "w")
        dump_perBin = open("%s/%s_perBin.%s" % (path, outputName, "txt"), "w")
        toprint = [(_unTLatex(p.label), hist) for (p, hist) in plot.histos if not p.isData]
        row1 = len(toprint)
        for tot in "signal", "background":
            if tot in plot.totals:
                toprint.append((tot.title(), plot.totals[tot]))
        toprint.append(("Total", total))
        maxlen = max([len(l) for (l, h) in toprint] + [10])
        fmt = "%%-%ds %%9.2f +/- %%9.2f (stat)" % (maxlen + 1)
        for i, (label, hist) in enumerate(toprint):
            if hist.Integral() <= 0:
                continue
            norm = hist.Integral()
            stat = hist.integralStatError()
            syst : float = hist.integralSystError(symmetrize=True)  # type: ignore
            var_perbin = [hist.GetBinContent(i + 1) for i in range(hist.GetNbinsX())]
            if i == row1:
                dump.write(("-" * (maxlen + 45)) + "\n")
                dump_perBin.write(("-" * (maxlen + 45)) + "\n")
            dump.write(fmt % (label, norm, stat))
            dump_perBin.write("%%-%ds " % (maxlen + 1) % label + " ".join(["%9.2f" % x for x in var_perbin]) + "\n")
            if syst:
                dump.write(" +/- %9.2f (syst) = +/- %9.2f (all)" % (syst, hypot(stat, syst)))
            dump.write("\n")
        if data:
            dump.write(("-" * (maxlen + 45)) + "\n")
            dump_perBin.write(("-" * (maxlen + 45)) + "\n")
            for dproc, dhist in data:
                label = "DATA" if len(data) == 1 else dproc.label
                dump       .write(("%%-%ds %%7.0f\n" % (maxlen + 1)) % (label, dhist.Integral()))
                dump_perBin.write(("%%-%ds " % (maxlen + 1)) % (label) + " ".join(["%7.0f" % dhist.GetBinContent(i + 1) for i in range(dhist.GetNbinsX())]) + "\n")
        for logname, loglines in getattr(plot, "allLogs", []):
            dump.write("\n\n --- %s --- \n" % logname)
            for line in loglines:
                dump.write("%s\n" % line)
        dump.write("\n")
        dump.close()


class PlotSetPrinter:
    @staticmethod
    def defaultOptions() -> Options:
        opts = Options()
        opts.declare("stack", True, bool, help="Whether different contributions should be stacked")
        opts.declare("plotFormats", "root,txt", help="Output format for plots")
        opts.declare("noStackSignals", False, bool, help="Don't include signals in the stack")
        return opts

    def __init__(self, **options):
        self._options = PlotSetPrinter.defaultOptions().update(**options)

    def printSet(self, plots : MultiReport, path : str, ncpu=None, **options) -> None:
        assert isinstance(plots, MultiReport)

        opts = self._options.cloneAndUpdate(**options)
        outputFormats = opts.plotFormats.split(",")
        ## Loop on the plots and print them
        pool_data = []
        for plotKey, plot in plots:
            pool_data.append((plot, path.format(**plotKey), "txt" in outputFormats, opts.stack, opts.noStackSignals))

        #TODO enabling multiprocessing or multitheading lead to uncorrect behavior
        if ncpu is None:
            ncpu = os.cpu_count()
        #import concurrent
        #with concurrent.futures.ThreadPoolExecutor(ncpu) as executor:
        #    chunksize = len(pool_data) // ncpu if len(pool_data) // ncpu > 0 else 1
        #    res = executor.map(printPlot, pool_data, chunksize=chunksize)
        #res = list(res)

        #import multiprocessing as mp
        #pool = mp.Pool(ncpu)
        #pool.starmap(_printPlot, pool_data)

        for d in pool_data:
            printPlot(d)
