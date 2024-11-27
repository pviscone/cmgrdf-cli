from math import sqrt
import time
import hashlib
from typing import Any, List, Sequence, Tuple, Union
from enum import Enum

import ROOT
from CMGRDF.GenWeightProvider import GenWeightProvider
from CMGRDF.histoWithNuisances import HistoWithNuisances, YieldWithNuisances, mergePlots
from CMGRDF.utils import MultiKey, MultiReport, safeName
from CMGRDF.data import Source, Process
from CMGRDF.flow import ComputeTotalWeight, Alias, Define, ReDefine, DefineDefault, Vary, FlowStep, Flow, Target, Yield
from CMGRDF.plots import Plot, PlotResult
from CMGRDF.snapshot import Snapshot


class _Branch(object):
    def __init__(self, parentOrSource : "Union[_Branch,Source]", stepOrTreeName : "Union[FlowStep,str]"):
        if isinstance(parentOrSource, _Branch):
            assert isinstance(stepOrTreeName, FlowStep)
            self.source = parentOrSource.source
            self.sourceTreeName = parentOrSource.sourceTreeName
            self.parentBranch = parentOrSource
            self.hasher = parentOrSource.hasher.copy()
            self.step = stepOrTreeName
            stepOrTreeName._addToHash(self.hasher)
        else:
            assert isinstance(parentOrSource, Source) and isinstance(stepOrTreeName, str)
            self.source = parentOrSource
            self.sourceTreeName = stepOrTreeName
            self.parentBranch = None
            self.hasher = hashlib.sha256()
            self.step = None
        self.branches = []  # type: List["_Branch"]
        self.leaves = dict()  # type: dict[Target, Any]
        self._rdfAndWeights = None  # type: Tuple[Any, list[str]]
        self._hasUncertainties = None

    def maybeBranch(self, step : FlowStep, verbose=False):
        for b in self.branches:
            if b.step == step:
                if verbose:
                    print(" Re-used branch for step %s: %s: %s" % (step.name, step, b.hasher.hexdigest()))
                return b
        b = _Branch(self, step)
        if verbose:
            print(" Created new branch for step %s: %s: %s" % (step.name, step, b.hasher.hexdigest()))
        self.branches.append(b)
        return b

    def longId(self):
        return "%s-%s" % (safeName(self.step), self.hasher.hexdigest())

    def rdfAndWeights(self) -> "Tuple[Any, list[str]]":
        if self._rdfAndWeights is None:
            if self.parentBranch is None:
                self._rdfAndWeights = (self.source.createRDF(self.sourceTreeName), [])
                self._hasUncertainties = False
            else:
                self._rdfAndWeights = self.step.attach(*self.parentBranch.rdfAndWeights())
        return self._rdfAndWeights

    def rdf(self):
        return self.rdfAndWeights()[0]

    def weights(self) -> "list[str]":
        return self.rdfAndWeights()[1]

    def hasUncertainties(self) -> bool:
        if self._hasUncertainties is None:
            self._hasUncertainties = bool(self.rdf().GetVariations().AsString())
        return self._hasUncertainties


class Processor(object):
    State = Enum("State", ["Clean", "Booked", "Run"])

    def __init__(self, cache=None):
        self._trees = dict()  # type: dict[Source,_Branch]
        self._summer = GenWeightProvider(cache=cache)
        self._lumiMap = dict()  # type: dict[MultiKey, float]
        self._cache = cache
        self._toCache = dict()
        self.clear()

    def clear(self):
        self._futures = []
        self._fromCache = []
        self._toCache.clear()
        self._trees.clear()
        self._rawResults = None
        self._state = Processor.State.Clean
        return self

    def _growBranch(self, source : Source, flow : Flow, treeName="Events", verbose=False):
        if source not in self._trees:
            if verbose:
                print("Created new source tree for %s" % source.longId())
            self._trees[source] = _Branch(source, treeName)
        else:
            if verbose:
                print("Reused source for %s" % source.longId())
        tree = self._trees[source]
        if flow:
            for step in flow.steps:
                tree = tree.maybeBranch(step, verbose=verbose)
            tree = tree.maybeBranch(ComputeTotalWeight(), verbose=verbose)
        return tree

    def _bookCutFlowReports(self):
        return [(src, b.rdf().Report()) for (src, b) in self._trees.items()]

    def bookedLumi(self, multiKey):
        if multiKey not in self._lumiMap:
            lumi = sum([l for (k, l) in self._lumiMap.items() if multiKey.isSuperSet(k)])
            self._lumiMap[multiKey] = lumi
        return self._lumiMap[multiKey]

    def book(self, processes : Sequence[Process], lumi, flows : Union[Flow, Sequence[Flow]], targets : Union[Target, Sequence[Target]], eras=None, taskName="", withUncertainties=False, logPerformance=True):
        if self._state == Processor.State.Run:
            raise RuntimeError("After book() and run(), call clear() before booking again")
        self._state = Processor.State.Booked
        self._rawResults = None  # invalidate existing results
        t0 = time.perf_counter()
        n0 = (self._summer.nSamples(), len(self._futures))
        if eras is None:
            eras = [None]
            lumi = {None: lumi}
        for p in processes:
            for s in p.samples:
                if s.isMC and s.genWeightName is not None:
                    s.bookSumWeight(self._summer, eras)
        if isinstance(flows, Flow):
            flows = [flows]
        if isinstance(targets, Target):
            targets = [targets]
        futuresToVary = []
        for flow in flows:
            for era in eras:
                self._lumiMap[MultiKey(taskName=taskName, flow=flow.name, era=era)] = lumi[era]
                for proc in processes:
                    procKey = MultiKey(taskName=taskName, flow=flow.name, era=era, process=proc.name)
                    for sample in proc.samples:
                        src = sample.source(era)
                        if not src:
                            continue
                        sampleKey = procKey.addKeys(sample=sample.name)
                        if sample.isMC:
                            sflow = sample.customizeFlow(flow.clone(), lumi[era], self._summer.provider(), era=era)
                        else:
                            sflow = sample.customizeFlow(flow.clone(), era=era)
                        branch = self._growBranch(src, sflow)
                        for t in targets:
                            if t.mcOnly and not sample.isMC:
                                continue
                            plotKey = sampleKey.addKeys(name=t.name)
                            k3 = (src.longId(), branch.longId(), t.longId()) if self._cache else None
                            if isinstance(t, Snapshot) and self._cache:
                                cached = t.fromCache(sample, era, k3)
                                if cached:
                                    self._fromCache.append((plotKey, proc, sample, t, cached, None))
                                    continue
                            if self._cache and (k3[-1] is not None) and self._cache.hasPlot(k3):
                                (res, resvar) = self._cache.getPlot(k3)
                                self._fromCache.append((plotKey, proc, sample, t, res, resvar))
                            else:
                                if t not in branch.leaves:
                                    branch.leaves[t] = t.attach(branch.rdf(), sample, era)
                                fut = branch.leaves[t]
                                if withUncertainties and branch.hasUncertainties():
                                    # postpone to all at the end, to avoid multiple JITs
                                    futuresToVary.append((plotKey, proc, sample, t, fut))
                                elif isinstance(t, Yield):
                                    self._futures.append((plotKey, proc, sample, t, fut, t.attachSumw2(branch.rdf())))
                                else:
                                    self._futures.append((plotKey, proc, sample, t, fut, None))
                                if self._cache and k3[-1] is not None:
                                    self._toCache[plotKey] = k3
        for (plotKey, proc, sample, t, fut) in futuresToVary:
            futvars = t.bookVariations(fut)
            self._futures.append((plotKey, proc, sample, t, fut, futvars))
        t1 = time.perf_counter()
        n1 = (self._summer.nSamples(), len(self._futures))
        if logPerformance:
            print("Booked %d sums and %d targets in %.3fs" % ((n1[0] - n0[0]), (n1[1] - n0[1]), t1 - t0))
        return self

    def bookCutFlow(self, processes : List[Process], lumi, flows : Union[Flow, List[Flow]], cutNames=None, eras=None, taskName="", withUncertainties=False, logPerformance=True):
        self._rawResults = None  # invalidate existing results
        t0 = time.perf_counter()
        n0 = (self._summer.nSamples(), len(self._futures))
        if eras is None:
            eras = [None]
            lumi = {None: lumi}
        for p in processes:
            for s in p.samples:
                if s.isMC and s.genWeightName is not None:
                    s.bookSumWeight(self._summer, eras)
        if isinstance(flows, Flow):
            flows = [flows]
        futuresToVary = []
        verbose = False
        for flow in flows:
            for era in eras:
                for proc in processes:
                    procKey = MultiKey(taskName=taskName, flow=flow.name, era=era, process=proc.name)
                    for sample in proc.samples:
                        src = sample.source(era)
                        if not src:
                            continue
                        sampleKey = procKey.addKeys(sample=sample.name)
                        if sample.isMC:
                            sflow = sample.customizeFlow(flow.clone(), lumi[era], self._summer.provider(), era=era)
                        else:
                            sflow = sample.customizeFlow(flow.clone(), era=era)
                        ## now we have to go cut by cut
                        branch = self._growBranch(src, None, verbose=verbose)
                        for step in sflow.steps:
                            branch = branch.maybeBranch(step, verbose=verbose)
                            if type(step) not in (Alias, Define, ReDefine, DefineDefault, Vary):
                                if (cutNames is None) or (step.name in cutNames):
                                    wbranch = branch.maybeBranch(ComputeTotalWeight(), verbose=verbose)
                                    t = Yield(step.name, "weight")
                                    plotKey = sampleKey.addKeys(name=t.name)
                                    k3 = (src.longId(), wbranch.longId(), t.longId()) if self._cache else None
                                    if self._cache and (k3[-1] is not None) and self._cache.hasPlot(k3):
                                        (res, resvar) = self._cache.getPlot(k3)
                                        self._fromCache.append((plotKey, proc, sample, t, res, resvar))
                                    else:
                                        if t not in wbranch.leaves:
                                            wbranch.leaves[t] = t.attach(wbranch.rdf(), sample, era)
                                        fut = wbranch.leaves[t]
                                        if withUncertainties and branch.hasUncertainties():
                                            # postpone to all at the end, to avoid multiple JITs
                                            futuresToVary.append((plotKey, proc, sample, t, fut))
                                        else:
                                            self._futures.append((plotKey, proc, sample, t, fut, t.attachSumw2(wbranch.rdf())))
                                        if self._cache and k3[-1] is not None:
                                            self._toCache[plotKey] = k3
        for (plotKey, proc, sample, t, fut) in futuresToVary:
            fvars = ROOT.RDF.Experimental.VariationsFor(fut)
            self._futures.append((plotKey, proc, sample, t, fut, fvars))
        t1 = time.perf_counter()
        n1 = (self._summer.nSamples(), len(self._futures))
        if logPerformance:
            print("Booked %d sums and %d targets in %.3fs" % ((n1[0] - n0[0]), (n1[1] - n0[1]), t1 - t0))
        return self

    def _runAllRaw(self, logPerformance=True, makeCutFlowReports=False, debug=False):
        """returns a MultiReport with value being (process,sample,target,future.GetValue(),vars)"""
        self._state = Processor.State.Run
        if self._rawResults is None:
            self._reports = self._bookCutFlowReports() if makeCutFlowReports else []
            t0 = time.perf_counter()
            n0 = (self._summer.nSamples(), len(self._futures))
            self._summer.runAll()
            t0b = time.perf_counter()
            if logPerformance:
                print("Filled %d sums in %.3fs" % (n0[0], t0b - t0))
            # run the graphs
            if self._futures:
                if debug:
                    for fut in self._futures:
                        name = str(fut[0]).replace(",", "_").replace(")", "").replace("(", "").replace("=", "_")
                        ROOT.RDF.SaveGraph(fut[-2], f'{name}.dot')
                ROOT.RDF.RunGraphs([fut[-2] for fut in self._futures])
                print("")
                t1 = time.perf_counter()
                if logPerformance:
                    print("Filled %d sums and %d targets in %.3fs (+%.3f)" % (n0[0], n0[1], t1 - t0, t1 - t0b))
            # finalize the plots
            ret = MultiReport()
            for (plotKey, proc, sample, target, future, fvars) in self._futures:
                result = target.finishFuture(future, sample, plotKey.era)
                resvars = target.finishVarFuture(fvars, sample, plotKey.era) if fvars else None
                if plotKey in self._toCache:
                    if isinstance(target, Snapshot):
                        target.toCache(result, self._toCache[plotKey])
                    else:
                        self._cache.writePlot(self._toCache[plotKey], result, resvars)
                ret.append(plotKey, (proc, sample, target, result, resvars))
            for (plotKey, proc, sample, target, result, resvars) in self._fromCache:
                ret.append(plotKey, (proc, sample, target, result, resvars))
            self._rawResults = ret
        return self._rawResults

    def printRawCutFlowReports(self):
        for source, report in sorted(self._reports, key=lambda p : p[0].longId()):
            print("Cut flow for %s" % source.longId())
            report.GetValue().Print()
            print("")

    def runPlots(self, mergeEras=False, mergeSamples=True, logPerformance=True, **kwargs):
        rawReport = self._runAllRaw(logPerformance=logPerformance, **kwargs)
        t0 = time.perf_counter()
        plots = MultiReport()
        for plotKey, (proc, sample, plot, hraw, hvars) in rawReport:
            if not isinstance(plot, Plot):
                continue  # there may be other stuff depending on book
            hist = HistoWithNuisances(hraw)
            if hvars:
                for k in hvars.keys():
                    if ":" in k:
                        (var, sign) = str(k).split(":")
                        hist.addVariation(var, sign, hvars[k])
                    elif k != "nominal":
                        print("ERROR: unknown variation %s for %s" % (k, plotKey))
            for nuis in sample.normUncertainties + proc.normUncertainties:
                if nuis.eras and plotKey.era not in nuis.eras:
                    continue
                hist.addYieldVariations(nuis.name, nuis.kappaUp, nuis.kappaDown)
            hist = plot.style(hist, proc)
            plots.append(plotKey, (plot, proc, sample, hist))
        # merge the plots
        keysToRemove = []
        if mergeSamples:
            keysToRemove.append("sample")
        if mergeEras:
            keysToRemove.append("era")
        merged = MultiReport()
        for mergedKey, mergeList in plots.groupRemoving(*keysToRemove):
            plot = mergeList[0][0]
            proc = mergeList[0][1]
            hists = [r[-1] for r in mergeList]
            if mergeSamples:
                merged.append(mergedKey, (plot, proc, mergePlots(proc.name, hists)))
            else:
                sample = mergeList[0][2]
                merged.append(mergedKey, (plot, proc, sample, mergePlots(sample.name, hists)))
        keysToRemove = ["process"] if mergeSamples else ["process", "sample"]
        results = MultiReport()
        for mergedKey, mergeList in merged.groupRemoving(*keysToRemove):
            plot = mergeList[0][0]
            histos = [r[1:] for r in mergeList]
            result = PlotResult(plot, histos)
            results.append(mergedKey, result)
            result.lumi = self.bookedLumi(mergedKey.removeKeys("name"))
        if logPerformance:
            print("Merged %d plots in %.3fs" % (len(plots), time.perf_counter() - t0))
        return results

    def runYields(self, mergeEras=False, mergeSamples=True, logPerformance=True, **kwargs):
        rawReport = self._runAllRaw(logPerformance=logPerformance, **kwargs)
        t0 = time.perf_counter()
        plots = MultiReport()
        for plotKey, (proc, sample, plot, evyield, yvars) in rawReport:
            if not isinstance(plot, Yield):
                continue  # there may be other stuff depending on book
            hist = YieldWithNuisances(plot.name, evyield)
            if yvars:
                for k in yvars.keys():
                    if ":" in k:
                        (var, sign) = str(k).split(":")
                        hist.addVariation(var, sign, yvars[k])
                    elif k == "":  # sum(weight2)
                        hist.stat = sqrt(yvars[k])
                    elif k != "nominal":
                        print("ERROR: unknown variation %s for %s" % (k, plotKey))
            for nuis in sample.normUncertainties + proc.normUncertainties:
                if nuis.eras and plotKey.era not in nuis.eras:
                    continue
                hist.addYieldVariations(nuis.name, nuis.kappaUp, nuis.kappaDown)
            plots.append(plotKey, (proc, sample, hist))
        # merge the plots
        keysToRemove = []
        if mergeSamples:
            keysToRemove.append("sample")
        if mergeEras:
            keysToRemove.append("era")
        merged = MultiReport()
        for mergedKey, mergeList in plots.groupRemoving(*keysToRemove):
            proc = mergeList[0][0]
            hists = [r[-1] for r in mergeList]
            if mergeSamples:
                merged.append(mergedKey, (proc, mergePlots(proc.name, hists)))
            else:
                sample = mergeList[0][1]
                merged.append(mergedKey, (proc, sample, mergePlots(sample.name, hists)))
        if logPerformance:
            print("Merged %d yields in %.3fs" % (len(merged), time.perf_counter() - t0))
        return merged

    def runSnapshots(self, logPerformance=True):
        rawReport = self._runAllRaw(logPerformance=logPerformance)
        plots = MultiReport()
        for plotKey, (proc, sample, plot, hraw, hvars) in rawReport:
            if not isinstance(plot, Snapshot):
                continue  # there may be other stuff depending on book
            plots.append(plotKey, hraw)
        return plots
