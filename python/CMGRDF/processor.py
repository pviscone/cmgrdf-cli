import copy
from math import sqrt
import time
from typing import Any, Optional, Union
from collections.abc import Container, Sequence
from enum import Enum

import ROOT  # type: ignore
from CMGRDF.init import HasherFromGlobalConfig
from CMGRDF.histoWithNuisances import HistoWithNuisances, YieldWithNuisances, mergePlots
from CMGRDF.utils import MultiKey, MultiReport, safeName
from CMGRDF.data import MCSample, Sample, Source, MCGroup, Process
from CMGRDF.flow import ComputeTotalWeight, Alias, Define, ReDefine, DefineDefault, Vary, FlowStep, Flow, Target, Yield
from CMGRDF.plots import Plot, PlotResult
from CMGRDF.snapshot import Snapshot, mergeSnapshot
from CMGRDF.cache import SimpleCache


class _Branch(object):
    def __init__(self,
                 parentOrSource : "Union[_Branch,Source]",
                 stepOrTreeName : "Union[FlowStep,str]",
                 withUncertainties : bool,
                 hasher : Optional[Any] = None,
                 local : Optional[bool] = None,
                 cache : Optional[SimpleCache] = None,
                 DataFrameClass=ROOT.RDataFrame,
                 **kwargs):
        if isinstance(parentOrSource, _Branch):
            assert isinstance(stepOrTreeName, FlowStep)
            self.source = parentOrSource.source
            self.sourceTreeName = parentOrSource.sourceTreeName
            self._local = parentOrSource._local
            self.DataFrameClass = parentOrSource.DataFrameClass
            self.DataFrameArgs = parentOrSource.DataFrameArgs
            self.parentBranch = parentOrSource
            self.hasher = parentOrSource.hasher.copy()
            self.withUncertainties = parentOrSource.withUncertainties
            self.step = stepOrTreeName
            stepOrTreeName._addToHash(self.hasher)  # pyright: ignore[reportPrivateUsage]
        else:
            assert isinstance(parentOrSource, Source) and isinstance(stepOrTreeName, str) and (hasher is not None)
            self.source = parentOrSource
            self.sourceTreeName = stepOrTreeName
            self._local = local
            self.DataFrameClass = DataFrameClass
            self.DataFrameArgs = dict(**kwargs)
            self.parentBranch = None
            self.hasher = hasher
            self.withUncertainties = withUncertainties
            self.step = None
        self.branches : list[_Branch] = []
        self.leaves : dict[Target, Any] = dict()
        self._rdfAndWeights : Optional[tuple[Any, list[str]]] = None
        self._hasUncertainties = None
        self._cache = cache

    def maybeBranch(self, step : FlowStep, verbose=False) -> "_Branch":
        for b in self.branches:
            if b.step == step:
                if verbose:
                    print(" Re-used branch for step %s: %s: %s" % (step.name, step, b.hasher.hexdigest()))
                return b
        b = _Branch(self, step, self.withUncertainties)
        if verbose:
            print(" Created new branch for step %s: %s: %s" % (step.name, step, b.hasher.hexdigest()))
        self.branches.append(b)
        return b

    def longId(self) -> str:
        return "%s-%s" % (safeName(self.step), self.hasher.hexdigest())

    def rdfAndWeights(self) -> tuple[Any, list[str]]:
        if self._rdfAndWeights is None:
            if self.parentBranch is None:
                self._rdfAndWeights = (self.source.createRDF(self.sourceTreeName, self.DataFrameClass, cache=self._cache, **self.DataFrameArgs), [])
                self._hasUncertainties = False
            else:
                assert (self.step)
                self._rdfAndWeights = self.step.attach(*self.parentBranch.rdfAndWeights(), withUncertainties=self.withUncertainties)
        return self._rdfAndWeights

    def rdf(self) -> Any:
        return self.rdfAndWeights()[0]

    def weights(self) -> list[str]:
        return self.rdfAndWeights()[1]

    def hasUncertainties(self) -> bool:
        if not self.withUncertainties:
            return False
        if self._hasUncertainties is None:
            if self._local:
                self._hasUncertainties = bool(self.rdf().GetVariations().AsString())
            else:
                self._hasUncertainties = False
                node = self.rdf()
                while node is not None:
                    if node.operation is not None and node.operation.name == "Vary":
                        self._hasUncertainties = True
                        break
                    node = node.parent
        return self._hasUncertainties


class Processor(object):
    State = Enum("State", ["Clean", "Booked", "Run"])

    def __init__(self,
                 cache : Optional[SimpleCache] = None,
                 executor : Optional[tuple[str, Any]] = None,
                 withUncertainties : Optional[bool] = None):
        self._trees : dict[Source, _Branch] = dict()
        self._lumiMap : dict[MultiKey, float] = dict()
        self._cache = cache
        self._rawResults : Optional[MultiReport] = None
        self._reports : list[tuple[Source, Any]] = []
        self._futures: list[tuple[MultiKey, Process, Sample, Target, Any, Any]] = []
        self._fromCache: list[tuple[MultiKey, Process, Sample, Target, Any, Any]] = []
        self._toCache : dict[MultiKey, tuple[str, str, str]] = dict()
        self._executor = executor
        self.withUncertainties = withUncertainties
        if executor is not None:
            self._local = False
            self.RunGraphs = ROOT.RDF.Experimental.Distributed.RunGraphs
            self.VariationsFor = ROOT.RDF.Experimental.Distributed.VariationsFor
            if executor[0] == "dask":
                self.DataFrameClass = ROOT.RDF.Experimental.Distributed.Dask.RDataFrame
                self.DataFrameArgs = dict(daskclient=executor[1])
        else:
            self._local = True
            self.RunGraphs = ROOT.RDF.RunGraphs
            self.VariationsFor = ROOT.RDF.Experimental.VariationsFor
            self.DataFrameClass = ROOT.RDataFrame
            self.DataFrameArgs = {}
        self._hasher = HasherFromGlobalConfig()
        self._state = Processor.State.Clean

    def clear(self) -> "Processor":
        self._futures.clear()
        self._fromCache.clear()
        self._toCache.clear()
        self._trees.clear()
        self._rawResults = None
        self._state = Processor.State.Clean
        return self

    def _growBranch(self,
                    source : Source,
                    flow : Optional[Flow],
                    treeName : str = "Events",
                    verbose : bool = False,
                    withUncertainties : bool = False) -> _Branch:
        if source not in self._trees:
            if verbose:
                print("Created new source tree for %s, local %s" % (source.longId(), self._local))
            self._trees[source] = _Branch(source, treeName, withUncertainties, hasher=self._hasher.copy(), local=self._local, DataFrameClass=self.DataFrameClass, cache=self._cache, **self.DataFrameArgs)
        else:
            if verbose:
                print("Reused source for %s" % source.longId())
        tree = self._trees[source]
        if flow:
            for step in flow.steps:
                tree = tree.maybeBranch(step, verbose=verbose)
            tree = tree.maybeBranch(ComputeTotalWeight(), verbose=verbose)
        return tree

    def _bookCutFlowReports(self) -> list[tuple[Source, Any]]:
        return [(src, b.rdf().Report()) for (src, b) in self._trees.items()]

    def bookedLumi(self, multiKey : MultiKey) -> float:
        if multiKey not in self._lumiMap:
            lumi = sum([l for (k, l) in self._lumiMap.items() if multiKey.isSuperSet(k)])
            self._lumiMap[multiKey] = lumi
        return self._lumiMap[multiKey]

    def prebookSumWeights(self,
                          processes : Sequence[Process],
                          eras : Sequence[Optional[str]],
                          logPerformance : bool = True) -> None:
        t0 = time.perf_counter()
        n = 0
        for p in processes:
            for s in p.samples:
                if isinstance(s, (MCSample, MCGroup)) and s.genWeightName is not None:
                    n += s.bookSumWeight(eras, cache=self._cache)
        if self._cache:
            self._cache.commitSums()
        t1 = time.perf_counter()
        if logPerformance and n > 0:
            print(f"Computed sum weights for {n} samples in {t1 - t0:.3f}s")

    def _samplesForProc(self, proc : Process) -> list[Sample]:
        if self._local:
            return proc.samples
        ret : list[Sample] = []
        for sample in proc.samples:
            if isinstance(sample, MCGroup):
                print(f"Splitting MCGroup {sample.name} since it's not supported in DistRDF")
                ret.extend(sample.split())
            else:
                ret.append(sample)
        return ret

    def book(self,
             processes : Sequence[Process],
             lumi : Union[float, dict[str, float]],
             flows : Union[Flow, Sequence[Flow]],
             targets : Union[Target, Sequence[Target]],
             eras : Optional[list[str]] = None,
             taskName : str = "",
             withUncertainties : Optional[bool] = None,
             logPerformance : bool = True) -> "Processor":
        if withUncertainties is None:
            withUncertainties = self.withUncertainties or False
        if self._state == Processor.State.Run:
            raise RuntimeError("After book() and run(), call clear() before booking again")
        self._state = Processor.State.Booked
        self._rawResults = None  # invalidate existing results

        if eras is None:
            eralist = [None]
            assert isinstance(lumi, float)
        else:
            eralist = eras
            assert isinstance(lumi, dict)

        self.prebookSumWeights(processes, eralist, logPerformance=logPerformance)

        t0 = time.perf_counter()
        n0 = len(self._futures)

        if isinstance(flows, Flow):
            flows = [flows]
        if isinstance(targets, Target):
            targets = [targets]
        futuresToVary = []

        for flow in flows:
            for era in eralist:
                thislumi : float = lumi[era] if eras is not None else lumi  # type: ignore
                self._lumiMap[MultiKey(taskName=taskName, flow=flow.name, era=era)] = thislumi
                for proc in processes:
                    procKey = MultiKey(taskName=taskName, flow=flow.name, era=era, process=proc.name)
                    for sample in self._samplesForProc(proc):

                        src = sample.source(era)
                        if not src:
                            continue
                        srcid = src.longId()
                        sampleKey = procKey.addKeys(sample=sample.name)
                        if sample.isMC:
                            assert isinstance(sample, (MCSample, MCGroup))
                            sflow = sample.customizeFlowMC(flow.clone(), thislumi, era=era)
                        else:
                            sflow = sample.customizeFlow(flow.clone(), era=era)
                        branch = self._growBranch(src, sflow, withUncertainties=withUncertainties)
                        branchid = branch.longId()
                        for t in targets:
                            if t.mcOnly and not sample.isMC:
                                continue
                            plotKey = sampleKey.addKeys(name=t.name)
                            tid = t.longId()
                            if self._cache and (tid is not None):
                                k3 = (srcid, branchid, tid)
                                if isinstance(t, Snapshot):
                                    cached = t.fromCache(sample, era, k3)
                                    if cached:
                                        self._fromCache.append((plotKey, proc, sample, t, cached, None))
                                        continue
                                elif self._cache.hasPlot(k3):
                                    (res, resvar) = self._cache.getPlot(k3)
                                    self._fromCache.append((plotKey, proc, sample, t, res, resvar))
                                    continue
                            if t not in branch.leaves:
                                branch.leaves[t] = t.attach(branch.rdf(), sample, era, withUncertainties)
                            fut = branch.leaves[t]
                            if withUncertainties and branch.hasUncertainties():
                                # postpone to all at the end, to avoid multiple JITs
                                futuresToVary.append((plotKey, proc, sample, t, fut))
                            elif isinstance(t, Yield):
                                self._futures.append((plotKey, proc, sample, t, fut, t.attachSumw2(branch.rdf())))
                            else:
                                self._futures.append((plotKey, proc, sample, t, fut, None))
                            if self._cache and (tid is not None):
                                self._toCache[plotKey] = (srcid, branchid, tid)
        for (plotKey, proc, sample, t, fut) in futuresToVary:
            futvars = t.bookVariations(fut, self.VariationsFor)
            self._futures.append((plotKey, proc, sample, t, fut, futvars))
        n1 = len(self._futures)
        t1 = time.perf_counter()

        if logPerformance:
            print("Booked %d targets in %.3fs, uncertainties %s" % (n1 - n0, t1 - t0, withUncertainties))
        return self

    def bookCutFlow(self,
                    processes : Sequence[Process],
                    lumi : Union[float, dict[str, float]],
                    flows : Union[Flow, list[Flow]],
                    cutNames : Optional[Container[str]] = None,
                    eras : Optional[list[str]] = None,
                    taskName="",
                    withUncertainties=None,
                    logPerformance=True) -> "Processor":
        if withUncertainties is None:
            withUncertainties = self.withUncertainties or False
        self._rawResults = None  # invalidate existing results

        if eras is None:
            eralist = [None]
            assert isinstance(lumi, float)
        else:
            eralist = eras
            assert isinstance(lumi, dict)

        self.prebookSumWeights(processes, eralist, logPerformance=logPerformance)

        t0 = time.perf_counter()
        n0 = len(self._futures)
        if isinstance(flows, Flow):
            flows = [flows]
        futuresToVary: list[tuple[MultiKey, Process, Sample, Target, Any]] = []
        verbose = False
        for flow in flows:
            for era in eralist:
                thislumi : float = lumi[era] if eras is not None else lumi  # type: ignore
                for proc in processes:
                    procKey = MultiKey(taskName=taskName, flow=flow.name, era=era, process=proc.name)
                    for sample in self._samplesForProc(proc):
                        src = sample.source(era)
                        if not src:
                            continue
                        sampleKey = procKey.addKeys(sample=sample.name)
                        if sample.isMC:
                            assert isinstance(sample, (MCSample, MCGroup))
                            sflow = sample.customizeFlowMC(flow.clone(), thislumi, era=era)
                        else:
                            sflow = sample.customizeFlow(flow.clone(), era=era)
                        ## now we have to go cut by cut
                        branch = self._growBranch(src, None, verbose=verbose, withUncertainties=withUncertainties)
                        for step in sflow.steps:
                            branch = branch.maybeBranch(step, verbose=verbose)
                            if type(step) not in (Alias, Define, ReDefine, DefineDefault, Vary):
                                if (cutNames is None) or (step.name in cutNames):
                                    wbranch = branch.maybeBranch(ComputeTotalWeight(), verbose=verbose)
                                    t = Yield(step.name, "weight")
                                    plotKey = sampleKey.addKeys(name=t.name)
                                    k3 = (src.longId(), wbranch.longId(), t.longId())
                                    if self._cache and self._cache.hasPlot(k3):
                                        (res, resvar) = self._cache.getPlot(k3)
                                        self._fromCache.append((plotKey, proc, sample, t, res, resvar))
                                    else:
                                        if t not in wbranch.leaves:
                                            wbranch.leaves[t] = t.attach(wbranch.rdf(), sample, era, withUncertainties)
                                        fut = wbranch.leaves[t]
                                        if withUncertainties and branch.hasUncertainties():
                                            # postpone to all at the end, to avoid multiple JITs
                                            futuresToVary.append((plotKey, proc, sample, t, fut))
                                        else:
                                            self._futures.append((plotKey, proc, sample, t, fut, t.attachSumw2(wbranch.rdf())))
                                        if self._cache:
                                            self._toCache[plotKey] = k3
        for (plotKey, proc, sample, t, fut) in futuresToVary:
            fvars = self.VariationsFor(fut)
            self._futures.append((plotKey, proc, sample, t, fut, fvars))
        t1 = time.perf_counter()
        n1 = len(self._futures)
        if logPerformance:
            print("Booked %d targets in %.3fs" % (n1 - n0, t1 - t0))
        return self

    def _runAllRaw(self, logPerformance=True, makeCutFlowReports=False, debug=False) -> MultiReport:
        """returns a MultiReport with value being (process,sample,target,future.GetValue(),vars)"""
        self._state = Processor.State.Run
        if self._rawResults is None:
            if not self._local:
                assert self._executor
                from CMGRDF.init import RunDistributedInitializer
                RunDistributedInitializer(self._executor[1])
                from CMGRDF.init import DistributedInitializerCode
                ROOT.RDF.Experimental.Distributed.initialize(exec, DistributedInitializerCode())
            self._reports = self._bookCutFlowReports() if makeCutFlowReports else []
            t0 = time.perf_counter()
            n0 = len(self._futures)
            # run the graphs
            if self._futures:
                if debug and self._local:
                    for fut in self._futures:
                        name = str(fut[0]).replace(",", "_").replace(")", "").replace("(", "").replace("=", "_")
                        ROOT.RDF.SaveGraph(fut[-2], f'{name}.dot')
                if logPerformance:
                    print(f"Scheduling to run {n0} targets from {len(self._trees)} sources")
                self.RunGraphs([fut[-2] for fut in self._futures])
                print("")
                t1 = time.perf_counter()
                if logPerformance:
                    print("Filled %d targets in %.3fs" % (n0, t1 - t0))
            # finalize the plots
            ret = MultiReport()
            for (plotKey, proc, sample, target, future, fvars) in self._futures:
                result = target.finishFuture(future, sample, plotKey.era)
                resvars = target.finishVarFuture(fvars, sample, plotKey.era) if fvars else None
                if plotKey in self._toCache:
                    if isinstance(target, Snapshot):
                        target.toCache(result, self._toCache[plotKey])
                    else:
                        self._cache.writePlot(self._toCache[plotKey], result, resvars)  # type: ignore
                ret.append(plotKey, (proc, sample, target, result, resvars))

            for (plotKey, proc, sample, target, result, resvars) in self._fromCache:
                ret.append(plotKey, (proc, sample, target, result, resvars))
            self._rawResults = ret
        return self._rawResults

    def printRawCutFlowReports(self) -> None:
        for source, report in sorted(self._reports, key=lambda p : p[0].longId()):
            print("Cut flow for %s" % source.longId())
            report.GetValue().Print()
            print("")

    def runPlots(self, mergeEras=False, mergeSamples=True, logPerformance=True, **kwargs) -> MultiReport:
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
                pcopy = copy.copy(proc)
                pcopy.name = f"{proc.name}_{sample.name}"
                pcopy.sample = sample
                merged.append(mergedKey, (plot, pcopy, mergePlots(sample.name, hists)))
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

    def runYields(self, mergeEras=False, mergeSamples=True, logPerformance=True, **kwargs) -> MultiReport:
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
                        assert (sign in ("up", "down"))
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

    def runSnapshots(self, logPerformance=True, hadd=True) -> MultiReport:
        rawReport = self._runAllRaw(logPerformance=logPerformance)
        plots = MultiReport()
        for plotKey, (proc, sample, plot, hraw, hvars) in rawReport:
            if not isinstance(plot, Snapshot):
                continue  # there may be other stuff depending on book
            plots.append(plotKey, hraw)
        if hadd and not self._local:
            tomerge = [h for (k, h) in plots if len(h.fnames) > 1]
            if logPerformance:
                print(f"I have {len(tomerge)} snapshots to merge")
            t0 = time.perf_counter()
            for s in tomerge:
                mergeSnapshot(s)
            if logPerformance:
                print(f"Merged {len(tomerge)} snapshots in {time.perf_counter() - t0:.3f}s")
        return plots
