from math import hypot, ceil
import re
import os
import os.path
from array import array
from typing import Any

import ROOT
from CMGRDF.histoWithNuisances import HistoWithNuisances, PostFitSetup, RooFitContext, listAllNuisances, mergePlots, warnAboutNegativeBins
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
    def __init__(self, name, *args, typ="Histo1D", mcOnly=False, cut=None, **options):
        super(Plot, self).__init__(name, mcOnly=mcOnly)
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
            self._template = self._model.GetHistogram()
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
            self._template = self._model.GetHistogram()
        else:
            raise NotImplementedError(f"Plot not implemented for {typ}")

        self.cut = cut
        self._bigHash = None

    def _prepareExpr(self, rdf, expr, name):
        if expr in rdf.GetColumnNames():
            return (rdf, expr)
        #print("Will create a new expression for plot "+self.name)
        if self.cut is not None:
            rdf2 = rdf.Filter(self.cut)
            rdf2 = rdf2.Define(name, expr)
        else:
            rdf2 = rdf.Define(name, expr)
        rdf2._from = rdf
        return (rdf2, name)

    def getOpt(self, name, default=None):
        return getattr(self, name, default)

    def hasOpt(self, name):
        return hasattr(self, name)

    def bookHisto1D(self, rdf, sample : Sample, era) -> Any:
        rdf, expr = self._prepareExpr(rdf, self._expr, self.name + "__plot_expr_")
        ret = rdf.Histo1D(self._model, expr, "weight")
        ret._from = rdf
        return ret

    def bookHisto2D(self, rdf, sample : Sample, era) -> Any:
        rdf, expr_y = self._prepareExpr(rdf, self._expr.split(":")[0], self.name + "__plot_expr_y")
        rdf, expr_x = self._prepareExpr(rdf, self._expr.split(":")[1], self.name + "__plot_expr_x")
        ret = rdf.Histo2D(self._model, expr_x, expr_y, "weight")
        ret._from = rdf
        return ret

    def finishHisto1D(self, plot, sample : Sample, era) -> Any:
        """Make changes to the plot that affect the contents"""
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

    def finishHisto2D(self, plot, sample : Sample, era) -> Any:
        return plot

    def styleHisto(self, plot, process : Process):
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

    def styleHisto1D(self, plot, process : Process):
        plot = self.styleHisto(plot, process)

        """Make changes to the plot that affect only the style"""
        ## Axis
        plot.GetXaxis().SetTitle(self.getOpt('xTitle', self._expr))
        if self.getOpt('xBinLabels', None) is not None:
            for (i, l) in enumerate(self.getOpt('xBinLabels')):
                plot.GetXaxis().SetBinLabel(i + 1, l)
        return plot

    def styleHisto2D(self, plot, process : Process):
        plot = self.styleHisto(plot, process)
        return plot

    def restyleAsOutline(self, plot):
        plot.SetLineWidth(3)
        plot.SetLineColor(plot.GetFillColor())
        plot.SetFillStyle(0)

    def __eq__(self, other):
        if other.__class__ == Plot:
            if self.name != other.name:
                return False
            if self.type != other.type:
                return False
            return self._forEquals == other._forEquals
        return False

    def __hash__(self):
        return hash(self.bigHash())

    def bigHash(self):
        if not self._bigHash:
            self._bigHash = recursiveHash(self.name, self.type, self._forEquals)
        return self._bigHash

    def longId(self):
        return "%s-%s" % (safeName(self), self.bigHash())


class PlotResult(object):
    """A plot, with the specifications, the histograms with all the individual components and possibly some totals"""

    def __init__(self, plot, histos, fillTotals=True):
        self.spec = plot
        self.name = plot.name
        self.template = self.spec._template
        self.histos = [(k, h if isinstance(h, HistoWithNuisances) else HistoWithNuisances(h)) for (k, h) in histos]
        self.totals = {}
        self._roofit = None
        if fillTotals:
            self.fillTotals()

    def __getattr__(self, key):
        return getattr(self.spec, key)

    def histByProcName(self, procName):
        for (p, h) in self.histos:
            if p.name == procName:
                return h
        return None

    def histData(self):
        for (p, h) in self.histos:
            if p.isData:
                return h
        return None

    def fillTotals(self):
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

    def initRooFit(self, workspace=None, xvarName="x", density=False, context : RooFitContext = None):
        """Set up RooFit for all the plots"""
        if self._roofit:
            print("Warning, calling initRooFit twice on PlotResult {self.name}")
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

    def getRooFit(self):
        if self._roofit is None:
            self.initRooFit()
        return self._roofit

    def setPostFit(self, posfit : PostFitSetup, applyIt : bool, signalPOI : str = "r"):
        if not self._roofit:
            self.initRooFit()
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


def getDataPoissonErrors(h, drawZeroBins=False, drawXbars=False):
    xaxis = h.GetXaxis()
    q = (1 - 0.6827) / 2.
    points = []
    errors = []
    for i in range(h.GetNbinsX()):
        N = h.GetBinContent(i + 1)
        dN = h.GetBinError(i + 1)
        if drawZeroBins or N > 0:
            if N > 0 and dN > 0 and abs(dN**2 / N - 1) > 1e-4:
                #print "Hey, this is not Poisson to begin with! %.2f, %.2f, neff = %.2f, yscale = %.5g" % (N, dN, (N/dN)**2, (dN**2/N))
                yscale = (dN**2 / N)
                N = (N / dN)**2
            else:
                yscale = 1
            x = xaxis.GetBinCenter(i + 1)
            points.append((x, yscale * N))
            EYlow = (N - ROOT.ROOT.Math.chisquared_quantile_c(1 - q, 2 * N) / 2.) if N > 0 else 0
            EYhigh = ROOT.ROOT.Math.chisquared_quantile_c(q, 2 * (N + 1)) / 2. - N
            EXhigh, EXlow = (xaxis.GetBinUpEdge(i + 1) - x, x - xaxis.GetBinLowEdge(i + 1)) if drawXbars else (0, 0)
            errors.append((EXlow, EXhigh, yscale * EYlow, yscale * EYhigh))
    ret = ROOT.TGraphAsymmErrors(len(points))
    ret.SetName(h.GetName() + "_graph")
    for i, ((x, y), (EXlow, EXhigh, EYlow, EYhigh)) in enumerate(zip(points, errors)):
        ret.SetPoint(i, x, y)
        ret.SetPointError(i, EXlow, EXhigh, EYlow, EYhigh)
    ret.SetLineWidth(h.GetLineWidth())
    ret.SetLineColor(h.GetLineColor())
    ret.SetLineStyle(h.GetLineStyle())
    ret.SetMarkerSize(h.GetMarkerSize())
    ret.SetMarkerColor(h.GetMarkerColor())
    ret.SetMarkerStyle(h.GetMarkerStyle())
    h.poissonGraph = ret  # attach it so it doesn't get deleted
    return ret


class PlotSetPrinter(object):
    @staticmethod
    def defaultOptions():
        opts = Options()
        opts.declare("stack", True, bool, help="Whether different contributions should be stacked")
        opts.declare("plotFormats", "png,pdf,root,txt", help="Output format for plots")
        opts.declare("noStackSignals", False, bool, help="Don't include signals in the stack")
        opts.declare("showErrors", False, bool, help="Show errors: in stacked plots, it will be on total (shaded band), otherwise it will be on individual outlines")
        opts.declare("extraLabel", help="Additional label to put in the plots")
        opts.declare("topLeftText", "#bf{CMS} #it{Internal}", help="Text on the top left of the canvas")
        opts.declare("topRightText", "", help="Text on the top right of the canvas")
        opts.declare("widePlot", False, bool, help="Make a wide plot (2:1 aspect ratio)")
        opts.declare("showRatio", False, bool, help="Add a ratio panel")
        opts.declare("maxRatioRange", (0.0, 4.99), float, nargs=2, help="Max range for ratio plots")
        opts.declare("fixRatioRange", False, bool, help="Use a fixed range for ratio plots")
        opts.declare("ratioYLabel", "Data/pred.", help="Y axis label for ratio plot")
        opts.declare("poisson", True, bool, help="Use Poisson errors for data")
        opts.declare("legendCutOffBackgrounds", 1e-5, float, help="Legend cut-off value for signals")
        opts.declare("legendCutOffSignals", 1e-5, float, help="Override legend cut-off value for signals")
        opts.declare("smallTextSize", 0.04, float, help="Text size for plot decoration labels")
        opts.declare("legendTextSize", 0.05, float, help="Text size for legend")
        opts.declare("legendColumns", 1, int, help="Legend columns")
        opts.declare("legendWidth", 0.25, float, help="Legend width")
        opts.declare("legendHeader", "", help="Legend header text")
        opts.declare("legendBorder", False, bool, help="Legend border box")
        opts.declare("warnAboutNegativeBins", False, bool, help="Warn about bins with negative yields")
        return opts

    def __init__(self, **options):
        self._options = PlotSetPrinter.defaultOptions().update(**options)

    def printSet(self, plots : MultiReport, path, **options):
        assert isinstance(plots, MultiReport)
        ## Loop on the plots and print them
        for plotKey, plot in plots:
            self.printPlot(plot, path.format(**plotKey), **options)

    def printPlot(self, plot, path, **options):
        ## make directory (FIXME make this better)
        if not os.path.exists(path):
            os.makedirs(path)
        if not os.path.exists(os.path.join(path, "index.php")):
            moduledir = os.environ["CMGRDF"]
            os.system(f"cp {moduledir}/externals/index.php " + path)
        opts = self._options.cloneAndUpdate(**options)
        outputName = plot.name
        stack = ROOT.THStack(outputName + "_stack", outputName)
        total = HistoWithNuisances(plot.template)
        total.SetName(outputName + "_total")
        outputFormats = opts.plotFormats.split(",")
        if "jupyter" in outputFormats:
            from IPython.display import Image, HTML, display
            outputFormats.remove("jupyter")
            if "png" not in outputFormats:
                outputFormats.append("png")
            outputFormats.append("jupyter")
            display(HTML("<h2>%s</h2>" % outputName))
        outputTDir = ROOT.TFile.Open("%s/%s.root" % (path, outputName), "RECREATE") if "root" in outputFormats else None
        print("Printing %s in %s (formats: %s)" % (outputName, path, outputFormats))
        data = []
        outlines = []

        for (proc, hist) in reversed(plot.histos):
            fullName = (os.path.basename(path), outputName, proc.name)
            if proc.isData:
                data.append((proc, hist))
                continue
            # warn if negative values
            if opts.warnAboutNegativeBins:
                warnAboutNegativeBins(hist, fullName)
            if hist.Integral() <= 0:
                continue
            if proc.isSignal and opts.noStackSignals:
                plot.restyleAsOutline(hist)
                outlines.append(hist)
                continue
            if opts.stack:
                stack.Add(hist.raw())
                total += hist
            else:
                plot.restyleAsOutline(hist)
                stack.Add(hist.raw())
                total.SetMaximum(max(total.GetMaximum(), 1.3 * hist.GetMaximum()))
            if outputTDir:
                hist.writeToFile(outputTDir)
            if opts.showErrors and not opts.stack:
                hist.SetMarkerColor(hist.GetFillColor())
                hist.SetMarkerStyle(21)
                hist.SetMarkerSize(1.5)
            else:
                hist.SetMarkerStyle(0)
        fullName = (os.path.basename(path), outputName)
        if stack.GetNhists() == 0:
            print("ERROR: for %s, all histograms are empty\n " % str(fullName))
            return
        if outputTDir:
            total.writeToFile(outputTDir)
        # define aspect ratio
        doWide = opts.widePlot or plot.getOpt("Wide", False)
        plotformat = [1200, 600] if doWide else [600, 600]
        if opts.showRatio:
            plotformat[1] += 200
        stack.Draw("GOFF")
        # FIXME clean up this
        total.GetXaxis().SetTitleSize(0.05)
        total.GetXaxis().SetTitleOffset(1.1)
        total.GetXaxis().SetLabelSize(0.05)
        total.GetXaxis().SetLabelOffset(0.007)
        total.GetYaxis().SetTitleSize(0.05)
        total.GetYaxis().SetTitleOffset(0.9 if doWide else 2.0)
        total.GetYaxis().SetLabelSize(0.05)
        total.GetYaxis().SetLabelOffset(0.007)
        total.GetYaxis().SetTitle(plot.getOpt('yTitle', "Events"))
        total.GetXaxis().SetTitle(plot.getOpt('xTitle', outputName))
        total.GetXaxis().SetNdivisions(plot.getOpt('xNDiv', 510))
        if plot.getOpt('xBinLabels', None) is not None:
            for (i, l) in enumerate(plot.getOpt('xBinLabels')):
                total.GetXaxis().SetBinLabel(i + 1, l)
        if outputTDir:
            outputTDir.WriteTObject(stack)
        islog = plot.getOpt('logy', False)
        ROOT.gStyle.SetPaperSize(20., 20. / plotformat[0] * plotformat[1])
        # create canvas
        ROOT.gStyle.SetOptStat(0)
        ROOT.gStyle.SetOptTitle(0)
        c1 = ROOT.TCanvas(outputName + "_canvas", outputName, plotformat[0], plotformat[1])
        c1.SetWindowSize(plotformat[0] + (plotformat[0] - c1.GetWw()), (plotformat[1] + (plotformat[1] - c1.GetWh())))
        c1.SetTopMargin(0.05)
        c1.SetBottomMargin(0.13)
        c1.SetLeftMargin(0.18)
        c1.SetRightMargin(0.04)
        c1.SetTicks()
        c1.Draw()
        p1, p2 = c1, None  # high and low panes
        # set borders, if necessary create subpads
        if opts.showRatio:
            p1 = ROOT.TPad("pad1", "pad1", 0, 0.27, 1, 1)
            p1.SetTopMargin(0.05)
            p1.SetBottomMargin(0.042)
            p2 = ROOT.TPad("pad2", "pad2", 0, 0, 1, 0.30)
            p2.SetTopMargin(0)
            p2.SetBottomMargin(0.3)
            p2.SetFillStyle(0)
            for p in p1, p2:
                p.SetLeftMargin(c1.GetLeftMargin())
                p.SetRightMargin(c1.GetRightMargin())
                p.SetTicks()
                p.Draw()
            p1.cd()
        p1.SetLogy(islog)
        p1.SetLogz(plot.getOpt('logz', False))
        if plot.getOpt('logx', False):
            p1.SetLogx(True)
            if p2:
                p2.SetLogx(True)
            total.GetXaxis().SetNoExponent(True)
            total.GetXaxis().SetMoreLogLabels(True)
        if data:
            total.SetMaximum(max(total.GetMaximum(), max(1.3 * d[1].GetMaximum() for d in data)))
        for o in outlines:
            total.SetMaximum(max(total.GetMaximum(), 1.3 * o.GetMaximum()))
        if islog:
            total.SetMaximum(2 * total.GetMaximum())
        if not islog:
            total.SetMinimum(0)
        total.Draw("HIST")
        if opts.stack:
            stack.Draw("SAME HIST")
            for o in outlines:
                o.Draw("SAME HIST")
            total.Draw("AXIS SAME")
        else:
            if opts.showErrors:
                ROOT.gStyle.SetErrorX(0.5)
                stack.Draw("SAME E NOSTACK")
            else:
                stack.Draw("SAME HIST NOSTACK")
        if plot.getOpt('moreY', 1.0) > 1.0:
            total.SetMaximum(plot.getOpt('moreY', 1.0) * total.GetMaximum())

        is2D = total.InheritsFrom("TH2")
        totalError = self.doShadedUncertainty(total) if opts.showErrors and not is2D else None

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
            if opts.poisson:
                pdata = getDataPoissonErrors(dhist, True, True)
                if outputTDir:
                    outputTDir.WriteTObject(pdata)
                pdata.Draw("PZ SAME")
            else:
                dhist.Draw("E SAME")
            ### FIXME restore?
            #if xblind[0] < xblind[1]:
            #    blindbox = ROOT.TBox(xblind[0],total.GetYaxis().GetXmin(),xblind[1],total.GetMaximum())
            #    blindbox.SetFillColor(ROOT.kBlue+3)
            #    blindbox.SetFillStyle(3944)
            #    blindbox.Draw()
            #    dhist.xblind = blindbox # so it doesn't get deleted
            #if options.doStatTests:
            #    doStatTests(total, dhist, options.doStatTests, legendCorner=plot.getOpt('legend','TR'))
        smallTextSize = opts.smallTextSize * (1.15 if opts.showRatio else 1.0)
        if plot.hasOpt('yMin') and plot.hasOpt('yMax'):
            total.GetYaxis().SetRangeUser(plot.getOpt('yMin'), plot.getOpt('yMax'))
        elif plot.hasOpt('yMin'):
            total.SetMinimum(plot.getOpt('yMin'))
        if plot.hasOpt('zMin') and plot.hasOpt('zMax'):
            total.GetZaxis().SetRangeUser(plot.getOpt('zMin'), plot.getOpt('zMax'))
        if opts.extraLabel:
            if plot.getOpt('legend', 'TR') == "TL":
                self.addLabel(c1, opts.extraLabel, .68, .855, .9, .895, align=32, textSize=smallTextSize)
            else:
                self.addLabel(c1, opts.extraLabel, .23, .855, .6, .895, align=12, textSize=smallTextSize)
        self.doLegend(p1, plot, total, totalError, opts, locals())
        self.addLabels(p1, hasExpo=total.GetMaximum() > 9e4 and not islog, textSize=smallTextSize, opts=opts, doWide=doWide, lumi=plot.lumi)
        if outputTDir:
            outputTDir.WriteTObject(c1)
        if opts.showRatio:
            nums = data
            den = total
            self.doRatioHists(p2, plot, nums, den, opts, locals())
            total.GetXaxis().SetLabelOffset(999)  # send them away
            total.GetXaxis().SetTitleOffset(999)  # in outer space
            total.GetYaxis().SetTitleSize(0.06)
            total.GetYaxis().SetTitleOffset(0.75 if doWide else 1.48)
            total.GetYaxis().SetLabelSize(0.05)
            total.GetYaxis().SetLabelOffset(0.007)
            c1.cd()
        for ext in outputFormats:
            if ext == "txt":
                if "TProfile" in total.ClassName():
                    continue
                dump = open("%s/%s.%s" % (path, outputName, ext), "w")
                dump_perBin = open("%s/%s_perBin.%s" % (path, outputName, ext), "w")
                toprint = [(_unTLatex(p.label), hist) for (p, hist) in plot.histos if not p.isData]
                row1 = len(toprint)
                for tot in "signal", "background":
                    if tot in plot.totals:
                        toprint.append((tot.title(), plot.totals[tot]))
                toprint.append(("Total", total))
                maxlen = max([len(l) for (l, h) in toprint] + [10])
                fmt = "%%-%ds %%9.2f +/- %%9.2f (stat)" % (maxlen + 1)
                fmt_perbin = "%%-%ds " % (maxlen + 1) + " ".join(["%%9.2f" for _ in range(total.GetNbinsX())])
                for i, (label, hist) in enumerate(toprint):
                    if hist.Integral() <= 0:
                        continue
                    norm = hist.Integral()
                    stat = hist.integralStatError()
                    syst = hist.integralSystError(symmetrize=True)
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
            elif ext in ("png", "pdf", "eps"):
                if total.InheritsFrom("TH2"):
                    for p, hist in plot.histos:
                        c1.SetRightMargin(0.20)
                        hist.SetContour(100)
                        hist.Draw("COLZ TEXT45")
                        c1.Print("%s/%s_data_%s.%s" % (path, outputName, p.label, ext))

                else:
                    savErrorLevel = ROOT.gErrorIgnoreLevel
                    ROOT.gErrorIgnoreLevel = ROOT.kWarning
                    c1.Print("%s/%s.%s" % (path, outputName, ext))
                    ROOT.gErrorIgnoreLevel = savErrorLevel

            elif ext == "root":
                pass  # already being done
            elif ext == "jupyter":
                display(Image("%s/%s.png" % (path, outputName)))
            else:
                raise RuntimeError("Unsupported output format %r" % ext)
        if outputTDir:
            outputTDir.Close()
        c1.Close()

    def addLabel(self, c1, text, x1, y1, x2, y2, align=12, fill=False, textSize=0.033):
        cmsprel = ROOT.TPaveText(x1, y1, x2, y2, "NDC")
        cmsprel.SetTextSize(textSize)
        cmsprel.SetFillColor(0)
        cmsprel.SetFillStyle(1001 if fill else 0)
        cmsprel.SetLineStyle(2)
        cmsprel.SetLineColor(0)
        cmsprel.SetTextAlign(align)
        cmsprel.SetTextFont(42)
        cmsprel.AddText(text)
        cmsprel.Draw("same")
        if not hasattr(c1, '_labels'):
            c1._labels = []
        c1._labels.append(cmsprel)
        return cmsprel

    def addLabels(self, c1, opts, hasExpo=False, textSize=0.033, xoffs=0, doWide=False, lumi=None):
        ymin, ymax = .955, .995
        if opts.topLeftText not in ['', None]:
            self.addLabel(c1, opts.topLeftText % dict(lumi=lumi),
                          (.28 if hasExpo else 0.07 if doWide else .16) + xoffs, ymin, .60 + xoffs, ymax,
                          align=12, textSize=textSize)
        if opts.topRightText not in ['', None]:
            self.addLabel(c1, opts.topRightText % dict(lumi=lumi),
                          (0.5 if doWide else .58) + xoffs, ymin, .98 + xoffs, ymax,
                          align=32, textSize=textSize)

    def doLegend(self, c1, plot, total, totalError, opts, locvars):
        if opts.stack:
            if opts.noStackSignals:
                mcStyle = ("L", "F")
            else:
                mcStyle = ("F", "F")
        else:
            mcStyle = ("L", "L")
        corner = plot.getOpt("legend", "TR")
        if corner in ("none", "off"):
            return
        totvalue = total.Integral()
        dataEntries, sigEntries, bgEntries = [], [], []
        for (proc, hist) in plot.histos:
            if proc.getOpt("hideInLegend", False):
                continue
            if proc.isData:
                dataEntries.append((hist.raw(), proc.label, "LPE"))
            elif proc.isSignal:
                if hist.Integral() < opts.legendCutOffSignals * totvalue:
                    continue
                sigEntries.append((hist.raw(), proc.label, mcStyle[0]))
            else:
                if hist.Integral() < opts.legendCutOffBackgrounds * totvalue:
                    continue
                bgEntries.append((hist.raw(), proc.label, mcStyle[1]))
        entries = dataEntries + sigEntries + bgEntries
        if totalError:
            entries.append((totalError, "Total unc.", "F"))
        nentries = len(entries)
        height = (.20 + opts.legendTextSize * max(nentries - 3, 0))
        if opts.legendColumns > 1:
            height = 1.3 * height / opts.legendColumn
        if corner == "TR":
            (x1, y1, x2, y2) = (0.97 - opts.legendWidth if locvars["doWide"] else .85 - opts.legendWidth, .9 - height, .90, .91)
        elif corner == "TC":
            (x1, y1, x2, y2) = (.5, .9 - height, .55 + opts.legendWidth, .91)
        elif corner == "TL":
            (x1, y1, x2, y2) = (.2, .9 - height, .25 + opts.legendWidth, .91)
        elif corner == "BR":
            (x1, y1, x2, y2) = (.85 - opts.legendWidth, .16 + height, .90, .15)
        elif corner == "BC":
            (x1, y1, x2, y2) = (.5, .16 + height, .5 + opts.legendWidth, .15)
        elif corner == "BL":
            (x1, y1, x2, y2) = (.2, .16 + height, .2 + opts.legendWidth, .15)
        else:
            raise RuntimeError("Unsupported legend placement %r" % corner)
        leg = ROOT.TLegend(x1, y1, x2, y2)
        leg.SetFillColor(0)
        leg.SetShadowColor(0)
        if opts.legendHeader:
            leg.SetHeader(opts.legendHeader)
        if not opts.legendBorder:
            leg.SetLineColor(0)
        leg.SetTextFont(42)
        leg.SetTextSize(opts.legendTextSize)
        leg.SetNColumns(opts.legendColumns)
        nrows = int(ceil(nentries / float(opts.legendColumns)))
        for r in range(nrows):
            for c in range(opts.legendColumns):
                i = r + c * nrows
                if i >= nentries:
                    break
                leg.AddEntry(*entries[i])
        leg.Draw()
        c1._legend = leg

    def doRatioHists(self, pane, plot, nums, den, opts, locvars):
        if plot.type not in ["Histo1D"]:
            return
        doWide = locvars["doWide"]
        textSize = opts.smallTextSize
        pane.cd()
        ratios = []
        if not nums:
            return
        for (proc, hist) in nums:
            if hasattr(hist, 'poissonGraph'):
                ratio = hist.poissonGraph.Clone("data_div")
                for i in range(ratio.GetN()):
                    x = ratio.GetX()[i]
                    div = den.GetBinContent(den.GetXaxis().FindBin(x))
                    ratio.SetPoint(i, x, ratio.GetY()[i] / div if div > 0 else 0)
                    ratio.SetPointError(i, ratio.GetErrorXlow(i), ratio.GetErrorXhigh(i),
                                        ratio.GetErrorYlow(i) / div if div > 0 else 0,
                                        ratio.GetErrorYhigh(i) / div if div > 0 else 0)
            else:
                ratio = hist.Clone("data_div")
                ratio.Divide(den.raw())
            ratios.append(ratio)
        unity = den.raw().Clone("")
        unityErr = den.graphAsymmTotalErrors(relative=True)
        unityErr0 = den.graphAsymmTotalErrors(toadd=[], relative=True)
        rmin, rmax = 1, 1
        for b in range(1, unity.GetNbinsX() + 1):
            unity.SetBinContent(b, 1 if unity.GetBinContent(b) > 0 else 0)
            unity.SetBinError(b, 0)
        rmin = min(1 - 2 * unityErr.GetErrorYlow(b) for b in range(unityErr.GetN())) if unityErr.GetN() else 1
        rmax = max(1 + 2 * unityErr.GetErrorYhigh(b) for b in range(unityErr.GetN())) if unityErr.GetN() else 1
        for ratio in ratios:
            if ratio.ClassName() != "TGraphAsymmErrors":
                for b in range(1, unity.GetNbinsX() + 1):
                    if ratio.GetBinContent(b) == 0:
                        continue
                    rmin = min(rmin, ratio.GetBinContent(b) - 2 * ratio.GetBinError(b))
                    rmax = max(rmax, ratio.GetBinContent(b) + 2 * ratio.GetBinError(b))
            else:
                for i in range(ratio.GetN()):
                    rmin = min(rmin, ratio.GetY()[i] - 2 * ratio.GetErrorYlow(i))
                    rmax = max(rmax, ratio.GetY()[i] + 2 * ratio.GetErrorYhigh(i))
        if rmin < opts.maxRatioRange[0] or opts.fixRatioRange:
            rmin = opts.maxRatioRange[0]
        if rmax > opts.maxRatioRange[1] or opts.fixRatioRange:
            rmax = opts.maxRatioRange[1]
        if (rmax > 3 and rmax <= 3.4):
            rmax = 3.4
        if (rmax > 2 and rmax <= 2.4):
            rmax = 2.4
        unity.SetMarkerStyle(1)
        unity.SetMarkerColor(ROOT.kBlue - 7)
        unityErr.SetFillStyle(1001)
        unityErr.SetFillColor(ROOT.kCyan)
        unityErr.SetMarkerStyle(1)
        unityErr.SetMarkerColor(ROOT.kCyan)
        unityErr0.SetFillStyle(1001)
        unityErr0.SetFillColor(ROOT.kBlue - 7)
        unityErr0.SetMarkerStyle(1)
        unityErr0.SetMarkerColor(ROOT.kBlue - 7)
        ROOT.gStyle.SetErrorX(0.5)
        unity.Draw("AXIS")
        #if errorsOnRef:
        unityErr.Draw("E2")
        #if fitRatio is not None and len(ratios) == 1:
        #    from CMGTools.TTHAnalysis.tools.plotDecorations import fitTGraph
        #    fitTGraph(ratio,order=fitRatio)
        #    unityErr.SetFillStyle(3013);
        #    unityErr0.SetFillStyle(3013);
        #    if errorsOnRef:
        #        unityErr0.Draw("E2 SAME");
        #else:
        # if errorsOnRef:
        unityErr0.Draw("E2 SAME")
        unity.Draw("AXIS SAME")
        rmin = float(plot.getOpt("ratioMin", rmin))
        rmax = float(plot.getOpt("ratioMax", rmax))
        unity.GetYaxis().SetRangeUser(rmin, rmax)
        unity.GetXaxis().SetTitleFont(42)
        unity.GetXaxis().SetTitleSize(0.14)
        unity.GetXaxis().SetTitleOffset(1.0)
        unity.GetXaxis().SetLabelFont(42)
        unity.GetXaxis().SetLabelSize(0.1)
        unity.GetXaxis().SetLabelOffset(0.015)
        unity.GetYaxis().SetNdivisions(505)  # FIXME
        unity.GetYaxis().SetTitleFont(42)
        unity.GetYaxis().SetTitleSize(0.14)
        offset = 0.32 if doWide else 0.62
        unity.GetYaxis().SetTitleOffset(offset)
        unity.GetYaxis().SetLabelFont(42)
        unity.GetYaxis().SetLabelSize(0.11)
        unity.GetYaxis().SetLabelOffset(0.01)
        unity.GetYaxis().SetDecimals(True)
        unity.GetYaxis().SetTitle(opts.ratioYLabel)
        if plot.getOpt('xBinLabels', None) is not None:
            for (i, l) in enumerate(plot.getOpt('xBinLabels')):
                unity.GetXaxis().SetBinLabel(i + 1, l)
            unity.GetXaxis().SetLabelSize(0.15 * (textSize / 0.035))
        line = ROOT.TLine(unity.GetXaxis().GetXmin(), 1, unity.GetXaxis().GetXmax(), 1)
        line.SetLineWidth(2)
        line.SetLineColor(58)
        line.Draw("L")
        for ratio in ratios:
            ratio.Draw("E SAME" if ratio.ClassName() != "TGraphAsymmErrors" else "PZ SAME")
        #leg0 = ROOT.TLegend(0.12 if doWide else 0.2, 0.84, 0.25 if doWide else 0.45, 0.94)
        #leg0.SetFillColor(0)
        #leg0.SetShadowColor(0)
        #leg0.SetLineColor(0)
        #leg0.SetTextFont(42)
        #leg0.SetTextSize(textSize*0.7/0.3)
        #leg0.AddEntry(unityErr0, "stat. unc.", "F")
        #if showStatTotLegend: leg0.Draw()
        #leg1 = ROOT.TLegend(0.25 if doWide else 0.45, 0.84, 0.38 if doWide else 0.7, 0.94)
        #leg1.SetFillColor(0)
        #leg1.SetShadowColor(0)
        #leg1.SetLineColor(0)
        #leg1.SetTextFont(42)
        #leg1.SetTextSize(textSize*0.7/0.3)
        #leg1.AddEntry(unityErr, "total unc.", "F")
        #if showStatTotLegend: leg1.Draw()
        #global legendratio0_, legendratio1_
        #legendratio0_ = leg0
        #legendratio1_ = leg1
        pane._ratioStuff = (ratios, unity, (unityErr, unityErr0), line)

    def doShadedUncertainty(self, hist):
        ret = hist.graphAsymmTotalErrors()
        ret.SetFillStyle(3244)
        ret.SetFillColor(ROOT.kGray + 2)
        ret.SetMarkerStyle(0)
        ret.Draw("PE2 SAME")
        return ret


def normalizePlots(plots, normSumToData=False):
    for k, plotresult in plots:
        normValue = 1.0
        if normSumToData:
            hdata = plotresult.histData()
            if hdata:
                normValue = hdata.Integral()
        for proc, h in plotresult.histos:
            if normSumToData and proc.isData:
                continue
            if h.Integral():
                h.Scale(normValue / h.Integral())
