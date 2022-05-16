from math import hypot, sqrt, ceil
import re
import os, os.path
from array import array
import time
from typing import Any, List

import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.IgnoreCommandLineOptions = True

from histoWithNuisances import HistoWithNuisances, mergePlots, warnAboutNegativeBins
from utils import Options, MultiKey, MultiReport
from flow import Target, Sample, Process, Flow, Forest

def _unTLatex(string : str) -> str:
    string = string.replace("#chi","x").replace("#rightarrow","->").replace("#minus","-")
    string = re.sub(r"#(mu|tau|gamma)", r"\1", string)
    string = re.sub(r"#bar\{(\w+)\}", r"\1bar", string)
    string = re.sub(r"[\^_]\{([012+\-])\}", r"\1", string)
    return string

class Plot(Target):
    def __init__(self, name, *args, **options):
        super(Plot, self).__init__(name)
        for k,v in options.items():
            setattr(self, k, v)
        t = options["1Gtype"] if "type" in options else "Histo1D"
        if t == "Histo1D":
            self._expr = args[0]
            self._bins = args[1]
            self.attach = self.bookHisto1D
            self.finish = self.finishHisto1D
            self.style = self.styleHisto1D
    def _prepareExpr(self, rdf, expr, name):
        if expr in rdf.GetColumnNames():
            return (rdf, expr)
        #print("Will create a new expression for plot "+self.name)
        rdf2 = rdf.Define(name, expr)
        rdf2._from = rdf
        return (rdf2, name)
    def getOpt(self, name, default=None):
        return getattr(self, name, default)
    def hasOpt(self, name):
        return hasattr(self, name)
    def bookHisto1D(self, rdf, sample : Sample, era) -> Any:
        if type(self._bins) == list:
            model = ROOT.RDF.TH1DModel(self.name, self.getOpt("title",self.name), len(self._bins)-1, array('f',self._bins)) 
        else:
            nbins, low, high = self._bins
            model = ROOT.RDF.TH1DModel(self.name, self.getOpt("title",self.name), int(nbins), low, high)
        self._template = model.GetHistogram()
        rdf, expr = self._prepareExpr(rdf, self._expr, self.name+"__plot_expr_")
        ret = rdf.Histo1D(model, expr, "weight")
        ret._from = rdf
        return ret
    def finishHisto1D(self, plot, sample : Sample, era) -> Any:
        ## Contents
        if self.getOpt('includeOverflows',True) or self.getOpt('includeUnderflow',False):
            plot.SetBinContent(1,plot.GetBinContent(0)+plot.GetBinContent(1))
            plot.SetBinError(1,hypot(plot.GetBinError(0),plot.GetBinError(1)))
            plot.SetBinContent(0,0)
            plot.SetBinError(0,0)
        if self.getOpt('includeOverflows',True) or self.getOpt('includeOverflow',False):
            n = plot.GetNbinsX()
            plot.SetBinContent(n,plot.GetBinContent(n+1)+plot.GetBinContent(n))
            plot.SetBinError(n,hypot(plot.GetBinError(n+1),plot.GetBinError(n)))
            plot.SetBinContent(n+1,0)
            plot.SetBinError(n+1,0)
        if sample.isMC:
            plot.Scale(1.0/sample.genWeightSum(era))
        return plot
    def styleHisto1D(self, plot, process : Process):
        ## Axis
        plot.GetXaxis().SetTitle(self.getOpt('xTitle',self._expr))
        ## Graphics
        if process.getOpt('fillColor',None) != None:
            plot.SetFillColor(process.getOpt('fillColor',0))
            plot.SetFillStyle(process.getOpt('fillStyle',1001))
        else:
            plot.SetFillStyle(0)
            plot.SetLineWidth(process.getOpt('lineWidth',1))
        plot.SetLineColor(process.getOpt('lineColor',1))
        plot.SetLineStyle(process.getOpt('lineStyle',1))
        plot.SetMarkerColor(process.getOpt('markerColor',1))
        plot.SetMarkerStyle(process.getOpt('markerStyle',20))
        plot.SetMarkerSize(process.getOpt('markerSize',1.1))
        plot.GetXaxis().SetTitleFont(42)
        plot.GetYaxis().SetTitleFont(42)
        plot.GetXaxis().SetLabelFont(42)
        plot.GetYaxis().SetLabelFont(42)
        return plot
    def restyleAsOutline(self,plot):
        plot.SetLineWidth(3)
        plot.SetLineColor(plot.GetFillColor())
        plot.SetFillStyle(0)


class PlotResult(object):
    def __init__(self,plot,histos,fillTotals=True):
        self.spec = plot
        self.name = plot.name
        self.template = self.spec._template
        self.histos = [(k, h if isinstance(h,HistoWithNuisances) else HistoWithNuisances(h)) for (k,h) in histos]
        self.totals = {}
        if fillTotals:
            sigs, bkgs = [], []
            for k,h in histos:
                if k.isSignal: sigs.append(h)
                elif not k.isData: bkgs.append(h)
            if sigs: self.totals["signal"] = mergePlots("signal", sigs)
            if bkgs: self.totals["background"] = mergePlots("background", bkgs)
    def __getattr__(self,key):
        return getattr(self.spec,key)



def getDataPoissonErrors(h, drawZeroBins=False, drawXbars=False):
    xaxis = h.GetXaxis()
    q=(1-0.6827)/2.;
    points = []
    errors = []
    for i in range(h.GetNbinsX()):
        N = h.GetBinContent(i+1);
        dN = h.GetBinError(i+1);
        if drawZeroBins or N > 0:
            if N > 0 and dN > 0 and abs(dN**2/N-1) > 1e-4: 
                #print "Hey, this is not Poisson to begin with! %.2f, %.2f, neff = %.2f, yscale = %.5g" % (N, dN, (N/dN)**2, (dN**2/N))
                yscale = (dN**2/N)
                N = (N/dN)**2
            else:
                yscale = 1
            x = xaxis.GetBinCenter(i+1);
            points.append( (x,yscale*N) )
            EYlow  = (N-ROOT.ROOT.Math.chisquared_quantile_c(1-q,2*N)/2.) if N > 0 else 0
            EYhigh = ROOT.ROOT.Math.chisquared_quantile_c(q,2*(N+1))/2.-N;
            EXhigh, EXlow = (xaxis.GetBinUpEdge(i+1)-x, x-xaxis.GetBinLowEdge(i+1)) if drawXbars else (0,0)
            errors.append( (EXlow,EXhigh,yscale*EYlow,yscale*EYhigh) )
    ret = ROOT.TGraphAsymmErrors(len(points))
    ret.SetName(h.GetName()+"_graph")
    for i,((x,y),(EXlow,EXhigh,EYlow,EYhigh)) in enumerate(zip(points,errors)):
        ret.SetPoint(i, x, y)
        ret.SetPointError(i, EXlow,EXhigh,EYlow,EYhigh)
    ret.SetLineWidth(h.GetLineWidth())
    ret.SetLineColor(h.GetLineColor())
    ret.SetLineStyle(h.GetLineStyle())
    ret.SetMarkerSize(h.GetMarkerSize())
    ret.SetMarkerColor(h.GetMarkerColor())
    ret.SetMarkerStyle(h.GetMarkerStyle())
    h.poissonGraph = ret ## attach it so it doesn't get deleted
    return ret

class PlotMaker(object):
    def __init__(self,growForest=True):
        self._forest = Forest() if growForest else None
        self.clear()
    def clear(self):
        self._sample_norm_futures = []
        self._plot_futures = []
        if self._forest: self._forest.clear()
    def book(self, processes : List[Process], lumi, flows, plots : List[Plot], eras=None, taskName="", withUncertainties=False):
        t0 = time.perf_counter()
        n0 = (len(self._sample_norm_futures), len(self._plot_futures))
        if eras is None: 
            eras = [None]
            lumi = {None:lumi}
        for p in processes:
            for s in p.samples:
                if s.isMC: 
                    self._sample_norm_futures += s.getWeightSumsFutureList(eras)
        if isinstance(flows,Flow): flows= [flows]
        for flow in flows:
            for era in eras:
                for proc in processes:
                    procKey = MultiKey(taskName=taskName, flow=flow.name, era=era, process=proc.name)
                    for sample in proc.samples:
                        src = sample.source(era)
                        if not src: continue
                        sampleKey = procKey.addKeys(sample=sample.name)
                        sflow = sample.customizeFlow(flow.clone(), lumi[era], era=era)
                        if self._forest:
                            rdf = self._forest.grow(src, sflow)
                        else:
                            rdf = sflow.attach(src.createRDF(), sample, era)
                        for pl in plots:
                            pfut = pl.attach(rdf, sample, era)
                            if pfut is None: continue
                            vars = ROOT.RDF.Experimental.VariationsFor(pfut) if withUncertainties else None
                            self._plot_futures.append((sampleKey.addKeys(plot = pl.name), proc, sample, pl, pfut, vars))         
        t1 = time.perf_counter()
        n1 = (len(self._sample_norm_futures), len(self._plot_futures))
        print("Booked %d sums and %d plots in %.3fs" % ((n1[0]-n0[0]),(n1[1]-n0[1]),t1-t0))
        return self
    def runAll(self, mergeEras=False, mergeSamples=True):
        t0 = time.perf_counter()
        n0 = (len(self._sample_norm_futures), len(self._plot_futures))
        # run the graphs
        ROOT.RDF.RunGraphs(self._sample_norm_futures+[pfut[-2] for pfut in self._plot_futures])
        t1 = time.perf_counter()
        print("Filled %d sums and %d plots in %.3fs" % (n0[0],n0[1],t1-t0))
        # finalize the plots
        plots = MultiReport()
        for (plotKey, proc, sample, plot, pfut, vars) in self._plot_futures:
            hist = HistoWithNuisances(plot.finish(pfut.GetValue(), sample, plotKey.era))
            if vars:
                for k in vars.GetKeys():
                    if ":" in k:
                        (var,sign) = str(k).split(":")
                        hist.addVariation(var, sign, plot.finish(vars[k], sample, plotKey.era))
                    elif k != "nominal":
                        print("ERROR: unknown variation %s for %s" % (k, plotKey))
            hist = plot.style(hist, proc)
            plots.append(plotKey, (plot, proc, sample, hist))
        # merge the plots
        keysToRemove = []
        if mergeSamples: keysToRemove.append("sample")
        if mergeEras: keysToRemove.append("era")
        merged = MultiReport()
        for mergedKey, mergeList in plots.groupRemoving(*keysToRemove):
            plot = mergeList[0][0]
            proc = mergeList[0][1]
            hists = [r[-1] for r in mergeList]
            if mergeSamples:
                merged.append(mergedKey, (plot, proc, mergePlots(proc.name, hists)))
            else:
                merged.append(mergedKey, (plot, proc, sample, mergePlots(proc.name, hists)))
        keysToRemove = ["process"] if mergeSamples else ["process","sample"]
        results = MultiReport()
        for mergedKey, mergeList in merged.groupRemoving(*keysToRemove):
            plot = mergeList[0][0]
            histos = [r[1:] for r in mergeList]
            result = PlotResult(plot, histos)
            results.append(mergedKey, result)
        t2 = time.perf_counter()
        print("Merged %d sums and %d plots in %.3fs" % (n0[0],n0[1],t2-t1))
        self.clear()
        return results

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
        opts.declare("maxRatioRange", (0.0,4.99), float, nargs=2, help="Max range for ratio plots")
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
        return opts
    def __init__(self,**options):
        self._options = PlotSetPrinter.defaultOptions().update(**options)
    def printSet(self, plots : MultiReport, path, **options):
        assert(isinstance(plots,MultiReport))
        ## Loop on the plots and print them
        for plotKey,plot in plots:
            self.printPlot(plot, path.format(**plotKey), **options)
    def printPlot(self, plot, path, **options):
        ## make directory (FIXME make this better, and use https://gitlab.cern.ch/php-plots/php-plots)
        if not os.path.exists(path):
            os.makedirs(path); 
            if os.path.exists("/afs/cern.ch"): os.system("cp /afs/cern.ch/user/g/gpetrucc/php/index.php "+path)
        opts = self._options.cloneAndUpdate(**options)
        outputName = plot.name
        stack = ROOT.THStack(outputName+"_stack",outputName)
        total = HistoWithNuisances(plot.template); 
        total.SetName(outputName+"_total")
        outputFormats = opts.plotFormats.split(",")
        outputTDir = ROOT.TFile.Open("%s/%s.root"%(path,outputName),"RECREATE") if "root" in outputFormats else None
        print("Printing %s in %s (formats: %s)" % (outputName,path,outputFormats))
        data = None
        for (proc, hist) in reversed(plot.histos):
            fullName = (os.path.basename(path), outputName, proc.name)
            if proc.isData: 
                data = (proc,hist)
                continue
            # warn if negative values
            warnAboutNegativeBins(hist,fullName)
            if hist.Integral() <= 0: continue
            if proc.isSignal and opts.noStackSignals:
                plot.restyleAsOutline(hist)
                continue
            if opts.stack:
                stack.Add(hist.raw())
                total += hist
            else:
                plot.restyleAsOutline(hist)
                stack.Add(hist.raw())
                total.SetMaximum(max(total.GetMaximum(),1.3*hist.GetMaximum()))
            if opts.showErrors and not(opts.stack):
                hist.SetMarkerColor(hist.GetFillColor())
                hist.SetMarkerStyle(21)
                hist.SetMarkerSize(1.5)
            else:
                hist.SetMarkerStyle(0)
        fullName = (os.path.basename(path), outputName)
        if stack.GetNhists() == 0:
            print("ERROR: for %s, all histograms are empty\n " % str(fullName))
            return
        # define aspect ratio
        doWide = opts.widePlot or plot.getOpt("Wide",False)
        plotformat = [1200,600] if doWide else [600,600]
        if opts.showRatio: plotformat[1] += 200
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
        total.GetYaxis().SetTitle(plot.getOpt('yTitle',"Events"))
        total.GetXaxis().SetTitle(plot.getOpt('xTitle',outputName))
        total.GetXaxis().SetNdivisions(plot.getOpt('xNDiv',510))
        if outputTDir: outputTDir.WriteTObject(stack) 
        islog = plot.getOpt('logy',False); 
        ROOT.gStyle.SetPaperSize(20.,20./plotformat[0]*plotformat[1])
        # create canvas
        ROOT.gStyle.SetOptStat(0)
        ROOT.gStyle.SetOptTitle(0)
        c1 = ROOT.TCanvas(outputName+"_canvas", outputName, plotformat[0], plotformat[1])
        c1.SetWindowSize(plotformat[0] + (plotformat[0] - c1.GetWw()), (plotformat[1] + (plotformat[1] - c1.GetWh())));
        c1.SetTopMargin(0.05)
        c1.SetBottomMargin(0.13)
        c1.SetLeftMargin(0.18)
        c1.SetRightMargin(0.04)
        c1.SetTicks()
        c1.Draw()
        p1, p2 = c1, None # high and low panes
        # set borders, if necessary create subpads
        if opts.showRatio:
            p1 = ROOT.TPad("pad1","pad1",0,0.27,1,1)
            p1.SetTopMargin(0.05)
            p1.SetBottomMargin(0.042)
            p2 = ROOT.TPad("pad2","pad2",0,0,1,0.30)
            p2.SetTopMargin(0)
            p2.SetBottomMargin(0.3)
            p2.SetFillStyle(0)
            for p in p1, p2:
                p.SetLeftMargin(c1.GetLeftMargin());
                p.SetRightMargin(c1.GetRightMargin());
                p.SetTicks()
                p.Draw()
            p1.cd()
        p1.SetLogy(islog)
        p1.SetLogz(plot.getOpt('logz',False))
        if plot.getOpt('logx',False):
            p1.SetLogx(True)
            if p2: p2.SetLogx(True)
            total.GetXaxis().SetNoExponent(True)
            total.GetXaxis().SetMoreLogLabels(True)
        if data:
            total.SetMaximum(max(total.GetMaximum(),1.3*data[1].GetMaximum()))
        if islog: total.SetMaximum(2*total.GetMaximum())
        if not islog: total.SetMinimum(0)
        total.Draw("HIST")
        if opts.stack:
            stack.Draw("SAME HIST")
            total.Draw("AXIS SAME")
        else: 
            if self._options.errors:
                ROOT.gStyle.SetErrorX(0.5)
                stack.Draw("SAME E NOSTACK")
            else:
                stack.Draw("SAME HIST NOSTACK")
        if plot.getOpt('moreY',1.0) > 1.0:
            total.SetMaximum(plot.getOpt('moreY',1.0)*total.GetMaximum())
        totalError = self.doShadedUncertainty(total) if opts.showErrors else None
        #is2D = total.InheritsFrom("TH2")
        if data:
            (dproc,dhist) = data
            if opts.poisson:
                pdata = getDataPoissonErrors(dhist, True, True)
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
        smallTextSize = opts.smallTextSize*(1.15 if opts.showRatio else 1.0)
        if plot.hasOpt('yMin') and plot.hasOpt('yMax'):
            total.GetYaxis().SetRangeUser(plot.getOpt('yMin'), plot.getOpt('yMax'))
        elif plot.hasOpt('yMin'):
            total.SetMinimum(plot.getOpt('yMin'))
        if plot.hasOpt('zMin') and plot.hasOpt('zMax'):
            total.GetZaxis().SetRangeUser(plot.getOpt('zMin'), plot.getOpt('zMax'))
        if opts.extraLabel:
            if plot.getOpt('legend','TR')=="TL":
                self.addLabel(c1, opts.extraLabel, .68, .855, .9, .895, align=32, textSize=smallTextSize)
                pass
            else:
                self.addLabel(c1, opts.extraLabel, .23, .855, .6, .895, align=12, textSize=smallTextSize)
                pass

        self.doLegend(p1,plot,total,totalError,opts,locals())
        self.addLabels(p1, hasExpo = total.GetMaximum() > 9e4 and not islog, textSize = smallTextSize, opts = opts, doWide = doWide)
        #  signorm = None; datnorm = None; sfitnorm = None
        #  if options.showSigShape or options.showIndivSigShapes or options.showIndivSigs: 
        #      signorms = doStackSignalNorm(pspec,pmap,options.showIndivSigShapes or options.showIndivSigs,extrascale=options.signalPlotScale, norm=not options.showIndivSigs)
        #      for signorm in signorms:
        #          if outputTDir: 
        #              signorm.SetDirectory(outputTDir); #outputTDir.WriteTObject(signorm)
        #          reMax(total,signorm,islog,doWide=doWide)
        #  if options.showDatShape: 
        #      datnorm = doDataNorm(pspec,pmap)
        #      if datnorm != None:
        #          if outputTDir: 
        #              datnorm.SetDirectory(outputTDir); outputTDir.WriteTObject(datnorm)
        #          reMax(total,datnorm,islog,doWide=doWide)
        #  if options.showSFitShape: 
        #      (sfitnorm,sf) = doStackSigScaledNormData(pspec,pmap)
        #      if sfitnorm != None:
        #          if outputTDir: 
        #              sfitnorm.SetDirectory(outputTDir); outputTDir.WriteTObject(sfitnorm)
        #          reMax(total,sfitnorm,islog,doWide=doWide)
        #  if options.flagDifferences and len(pmap) == 4:
        #      new = pmap['signal']
        #      ref = pmap['background']
        #      if "TH1" in new.ClassName():
        #          for b in range(1,new.GetNbinsX()+1):
        #              if abs(new.GetBinContent(b) - ref.GetBinContent(b)) > options.toleranceForDiff*ref.GetBinContent(b):
        #                  print "Plot: difference found in %s, bin %d" % (outputName, b)
        #                  p1.SetFillColor(ROOT.kYellow-10)
        #                  if p2: p2.SetFillColor(ROOT.kYellow-10)
        #                  break
        if outputTDir: outputTDir.WriteTObject(c1)
        if opts.showRatio:
            nums = [data] if data else []
            den = total
            self.doRatioHists(p2, plot, nums, den, opts, locals())
            total.GetXaxis().SetLabelOffset(999) ## send them away
            total.GetXaxis().SetTitleOffset(999) ## in outer space
            total.GetYaxis().SetTitleSize(0.06)
            total.GetYaxis().SetTitleOffset(0.75 if doWide else 1.48)
            total.GetYaxis().SetLabelSize(0.05)
            total.GetYaxis().SetLabelOffset(0.007)
            c1.cd()
        for ext in outputFormats:
            if ext == "txt":
                if "TProfile" in total.ClassName(): continue
                dump = open("%s/%s.%s" % (path, outputName, ext), "w")
                toprint = [(_unTLatex(p.label),hist) for (p,hist) in plot.histos if not p.isData]
                row1 = len(toprint)
                for tot in "signal", "background":
                    if tot in plot.totals: toprint.append((tot.title(),plot.totals[tot]))
                toprint.append(("Total", total)) 
                maxlen = max([len(l) for (l,h) in toprint]+[10])
                fmt    = "%%-%ds %%9.2f +/- %%9.2f (stat)" % (maxlen+1)
                for i, (label, hist) in enumerate(toprint):
                    if hist.Integral() <= 0: continue
                    norm = hist.Integral()
                    stat = hist.integralStatError()
                    syst = hist.integralSystError(symmetrize=True)
                    if i == row1:
                        dump.write(("-"*(maxlen+45))+"\n");
                    dump.write(fmt % (label, norm, stat))
                    if syst: dump.write(" +/- %9.2f (syst) = +/- %9.2f (all)"  % (syst, hypot(stat,syst)))
                    dump.write("\n")
                total
                if data: 
                    dump.write(("-"*(maxlen+45))+"\n");
                    dump.write(("%%-%ds %%7.0f\n" % (maxlen+1)) % ('DATA', dhist.Integral()))
                for logname, loglines in getattr(plot,"allLogs",[]):
                    dump.write("\n\n --- %s --- \n" % logname)
                    for line in loglines: dump.write("%s\n" % line)
                dump.write("\n")
                dump.close()
            elif ext in ("png","pdf","eps"):
                savErrorLevel = ROOT.gErrorIgnoreLevel; ROOT.gErrorIgnoreLevel = ROOT.kWarning;
                c1.Print("%s/%s.%s" % (path, outputName, ext))
                ROOT.gErrorIgnoreLevel = savErrorLevel;
            elif ext == "root":
                pass # already being done
            else:
                raise RuntimeError("Unsupported output format %r"%ext)
        if outputTDir: outputTDir.Close()
        c1.Close() 
    def addLabel(self,c1,text,x1,y1,x2,y2,align=12,fill=False,textSize=0.033,_noDelete={}):
        cmsprel = ROOT.TPaveText(x1,y1,x2,y2,"NDC");
        cmsprel.SetTextSize(textSize);
        cmsprel.SetFillColor(0);
        cmsprel.SetFillStyle(1001 if fill else 0);
        cmsprel.SetLineStyle(2);
        cmsprel.SetLineColor(0);
        cmsprel.SetTextAlign(align);
        cmsprel.SetTextFont(42);
        cmsprel.AddText(text);
        cmsprel.Draw("same");
        if not hasattr(c1, '_labels'): c1._labels =[]
        c1._labels.append(cmsprel)
        return cmsprel
    def addLabels(self, c1, opts, hasExpo=False, textSize=0.033, xoffs=0, doWide=False):
        if opts.topLeftText not in ['', None]:
            self.addLabel(c1,opts.topLeftText, (.28 if hasExpo else 0.07 if doWide else .16)+xoffs, .955, .60+xoffs, .995, align=12, textSize=textSize)
        if opts.topRightText not in ['', None]:
            self.addLabel(c1,opts.topRightText,(0.5 if doWide else .58)+xoffs, .955, .98+xoffs, .995, align=32, textSize=textSize)
    def doLegend(self,c1,plot,total,totalError,opts,locvars):
        if opts.stack:
            if opts.noStackSignals: mcStyle = ("L","F")
            else:                   mcStyle = ("F","F")
        else: mcStyle = "L"
        corner = plot.getOpt("legend","TR")
        if corner in ("none","off"): return
        totvalue = total.Integral()
        dataEntries, sigEntries, bgEntries = [],[],[]
        for (proc,hist) in plot.histos:
            if proc.getOpt("hideInLegend",False): continue
            if proc.isData:
                dataEntries.append((hist.raw(),proc.label,"LPE"))
            elif proc.isSignal:
                if hist.Integral() < opts.legendCutOffBackgrounds*totvalue: continue
                sigEntries.append((hist.raw(),proc.label,mcStyle[0]))
            else:
                if hist.Integral() < opts.legendCutOffSignals*totvalue: continue
                bgEntries.append((hist.raw(),proc.label,mcStyle[1]))
        entries = dataEntries + sigEntries + bgEntries 
        if totalError:  entries.append((totalError,"Total unc.","F"))
        nentries = len(entries)
        height = (.20 + opts.legendTextSize*max(nentries-3,0))
        if opts.legendColumns > 1: height = 1.3*height/opts.legendColumn
        if corner == "TR":
            (x1,y1,x2,y2) = (0.97-opts.legendWidth if locvars["doWide"] else .85-opts.legendWidth, .9 - height, .90, .91)
        elif corner == "TC":
            (x1,y1,x2,y2) = (.5, .9 - height, .55+opts.legendWidth, .91)
        elif corner == "TL":
            (x1,y1,x2,y2) = (.2, .9 - height, .25+opts.legendWidth, .91)
        elif corner == "BR":
            (x1,y1,x2,y2) = (.85-opts.legendWidth, .16 + height, .90, .15)
        elif corner == "BC":
            (x1,y1,x2,y2) = (.5, .16 + height, .5+opts.legendWidth, .15)
        elif corner == "BL":
            (x1,y1,x2,y2) = (.2, .16 + height, .2+opts.legendWidth, .15)
        else:
            raise RuntimeError("Unsupported legend placement %r" % corner)
        leg = ROOT.TLegend(x1,y1,x2,y2)
        leg.SetFillColor(0)
        leg.SetShadowColor(0)
        if opts.legendHeader: leg.SetHeader(opts.legendHeader)       
        if not opts.legendBorder: leg.SetLineColor(0)
        leg.SetTextFont(42)
        leg.SetTextSize(opts.legendTextSize)
        leg.SetNColumns(opts.legendColumns)
        nrows = int(ceil(nentries/float(opts.legendColumns)))
        for r in range(nrows):
            for c in range(opts.legendColumns):
                i = r+c*nrows
                if i >= nentries: break
                leg.AddEntry(*entries[i])
        leg.Draw()
        c1._legend =  leg
    def doRatioHists(self,pane,plot,nums,den,opts,locvars):
        doWide = locvars["doWide"]
        textSize = opts.smallTextSize
        pane.cd()
        ratios = []
        if not nums: return
        for (proc,hist) in nums:
            if hasattr(hist, 'poissonGraph'):
                ratio = hist.poissonGraph.Clone("data_div"); 
                for i in range(ratio.GetN()):
                    x    = ratio.GetX()[i]
                    div  = den.GetBinContent(den.GetXaxis().FindBin(x))
                    ratio.SetPoint(i, x, ratio.GetY()[i]/div if div > 0 else 0)
                    ratio.SetPointError(i, ratio.GetErrorXlow(i), ratio.GetErrorXhigh(i), 
                                        ratio.GetErrorYlow(i)/div  if div > 0 else 0, 
                                        ratio.GetErrorYhigh(i)/div if div > 0 else 0) 
            else:
                ratio = hist.Clone("data_div"); 
                ratio.Divide(den.raw())
            ratios.append(ratio)
        unity  = den.raw().Clone("")
        unityErr  = den.graphAsymmTotalErrors(relative=True)
        unityErr0 = den.graphAsymmTotalErrors(toadd=[],relative=True)
        rmin, rmax =  1,1
        for b in range(1,unity.GetNbinsX()+1):
            e,n = unity.GetBinError(b), unity.GetBinContent(b)
            unity.SetBinContent(b, 1 if n > 0 else 0)
            unity.SetBinError(b, 0)
        rmin = min(1-2*unityErr.GetErrorYlow(b)  for b in range(unityErr.GetN())) if unityErr.GetN() else 1
        rmax = max(1+2*unityErr.GetErrorYhigh(b) for b in range(unityErr.GetN())) if unityErr.GetN() else 1
        for ratio in ratios:
            if ratio.ClassName() != "TGraphAsymmErrors":
                for b in range(1,unity.GetNbinsX()+1):
                    if ratio.GetBinContent(b) == 0: continue
                    rmin = min( rmin, ratio.GetBinContent(b) - 2*ratio.GetBinError(b) ) 
                    rmax = max( rmax, ratio.GetBinContent(b) + 2*ratio.GetBinError(b) )  
            else:
                for i in range(ratio.GetN()):
                    rmin = min( rmin, ratio.GetY()[i] - 2*ratio.GetErrorYlow(i)  ) 
                    rmax = max( rmax, ratio.GetY()[i] + 2*ratio.GetErrorYhigh(i) )  
        if rmin < opts.maxRatioRange[0] or opts.fixRatioRange: rmin = opts.maxRatioRange[0]; 
        if rmax > opts.maxRatioRange[1] or opts.fixRatioRange: rmax = opts.maxRatioRange[1];
        if (rmax > 3 and rmax <= 3.4): rmax = 3.4
        if (rmax > 2 and rmax <= 2.4): rmax = 2.4
        unity.SetMarkerStyle(1);
        unity.SetMarkerColor(ROOT.kBlue-7);
        unityErr.SetFillStyle(1001);
        unityErr.SetFillColor(ROOT.kCyan);
        unityErr.SetMarkerStyle(1);
        unityErr.SetMarkerColor(ROOT.kCyan);
        unityErr0.SetFillStyle(1001);
        unityErr0.SetFillColor(ROOT.kBlue-7);
        unityErr0.SetMarkerStyle(1);
        unityErr0.SetMarkerColor(ROOT.kBlue-7);
        ROOT.gStyle.SetErrorX(0.5);
        unity.Draw("AXIS");
        #if errorsOnRef:
        unityErr.Draw("E2");
       #if fitRatio != None and len(ratios) == 1:
       #    from CMGTools.TTHAnalysis.tools.plotDecorations import fitTGraph
       #    fitTGraph(ratio,order=fitRatio)
       #    unityErr.SetFillStyle(3013);
       #    unityErr0.SetFillStyle(3013);
       #    if errorsOnRef:
       #        unityErr0.Draw("E2 SAME");
       #else:
        #if errorsOnRef:
        unityErr0.Draw("E2 SAME");
        unity.Draw("AXIS SAME");
        rmin = float(plot.getOpt("ratioMin",rmin))
        rmax = float(plot.getOpt("ratioMax",rmax))
        unity.GetYaxis().SetRangeUser(rmin,rmax);
        unity.GetXaxis().SetTitleFont(42)
        unity.GetXaxis().SetTitleSize(0.14)
        unity.GetXaxis().SetTitleOffset(1.0)
        unity.GetXaxis().SetLabelFont(42)
        unity.GetXaxis().SetLabelSize(0.1)
        unity.GetXaxis().SetLabelOffset(0.015)
        unity.GetYaxis().SetNdivisions(505) # FIXME
        unity.GetYaxis().SetTitleFont(42)
        unity.GetYaxis().SetTitleSize(0.14)
        offset = 0.32 if doWide else 0.62
        unity.GetYaxis().SetTitleOffset(offset)
        unity.GetYaxis().SetLabelFont(42)
        unity.GetYaxis().SetLabelSize(0.11)
        unity.GetYaxis().SetLabelOffset(0.01)
        unity.GetYaxis().SetDecimals(True) 
        unity.GetYaxis().SetTitle(opts.ratioYLabel)
        binlabels = plot.getOpt("xBinLabels","")
        if binlabels != "" and len(binlabels.split(",")) == unity.GetNbinsX():
            blist = binlabels.split(",")
            for i in range(1,unity.GetNbinsX()+1): 
                unity.GetXaxis().SetBinLabel(i,blist[i-1]) 
            unity.GetXaxis().SetLabelSize(0.15*(textSize/0.035))
        line = ROOT.TLine(unity.GetXaxis().GetXmin(),1,unity.GetXaxis().GetXmax(),1)
        line.SetLineWidth(2);
        line.SetLineColor(58);
        line.Draw("L")
        for ratio in ratios:
            ratio.Draw("E SAME" if ratio.ClassName() != "TGraphAsymmErrors" else "PZ SAME");
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
        pane._ratioStuff = (ratios, unity,(unityErr,unityErr0), line)
    def doShadedUncertainty(self, hist):
        ret = hist.graphAsymmTotalErrors()
        ret.SetFillStyle(3244);
        ret.SetFillColor(ROOT.kGray+2)
        ret.SetMarkerStyle(0)
        ret.Draw("PE2 SAME")
        return ret
     
 