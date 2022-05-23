import copy
import hashlib
import time
from typing import Any, Dict, List, Mapping, Union

import ROOT
from CMGRDF.GenWeightProvider import GenWeightProvider

from CMGRDF.data import Process, Source, Sample
from CMGRDF.utils import MultiKey, MultiReport, _recursiveAddToHash

class FlowStep(object):
    def __init__(self, name, onMC=True, onDataDriven=True, onData=True, eras=None):
        self.name = name
        self.onMC = onMC
        self.onData = onData
        self.onDataDriven = onDataDriven
        self.eras = eras
    def appliesTo(self, sample : Sample, era) -> bool:
        assert(isinstance(sample,Sample))
        if sample.isMC:
            if not self.onMC: return False
        elif sample.isData:
            if not self.onData: return False
        elif sample.isDataDriven:
            if not self.onDataDriven: return False
        if self.eras and (era not in self.eras):
            return False
        return True
    def attach(self, rdf):
        rdf2 = self._attach(rdf)
        if rdf2 != rdf:
            rdf2._from = rdf
            return rdf2
        else:
            return rdf
    @staticmethod
    def _equals(obj1,obj2):
        return (obj1.name == obj2.name and 
                obj1.onMC == obj2.onMC and
                obj1.onData == obj2.onData and
                obj1.onDataDriven == obj2.onDataDriven and
                obj1.eras == obj2.eras)
    def _addToHash(self,hasher):
        _recursiveAddToHash((self.name,self.onMC,self.onData,self.onDataDriven,self.eras),hasher)

class SimpleExprFlowStep(FlowStep):
    """ A Flow step which is fully defined by a single expression.
        This base class implements the equality and hash tests, while it's
        up to the subclass to implement _attach(self, rdf)"""
    def __init__(self, name, expr, **options):
        super().__init__(name, **options)
        self.expr = expr
        for k,v in options.items():
            setattr(self,k,v)
    def __eq__(self, other) -> bool:
        if other.__class__ == self.__class__:
            return FlowStep._equals(self, other) and self.expr == other.expr
        return id(self) == id(other)
    def _addToHash(self,hasher):
        super()._addToHash(hasher)
        _recursiveAddToHash(self.expr, hasher)

class Cut(SimpleExprFlowStep):
    def __init__(self, name, expr, **options):
        super().__init__(name, expr, **options)
    def _attach(self, rdf):
        return rdf.Filter(self.expr, self.name)

class Define(SimpleExprFlowStep):
    def __init__(self, name, expr, **options):
        super().__init__(name, expr, **options)
    def _attach(self, rdf):
        return rdf.Define(self.name, self.expr)

class ReDefine(SimpleExprFlowStep):
    def __init__(self, name, expr, **options):
        super().__init__(name, expr, **options)
    def _attach(self, rdf):
        return rdf.Redefine(self.name, self.expr)

class DefinePerSample(FlowStep):
    def __init__(self, name, provider, **options):
        super().__init__(name, **options)
        self.provider = provider
        for k,v in options.items():
            setattr(self,k,v)
    def __eq__(self, other) -> bool:
        if other.__class__ == self.__class__:
            return FlowStep._equals(self, other) and self.provider == other.provider
        return id(self) == id(other)
    def _addToHash(self,hasher):
        super()._addToHash(hasher)
    def _attach(self, rdf):
        return self.provider.attachAsDefinePerSample(ROOT.RDF.AsRNode(rdf), self.name)

class DefineDefault(SimpleExprFlowStep):
    def __init__(self, name, expr, **options):
        super().__init__(name, expr, **options)
    def _attach(self, rdf):
        # FIXME use DefinePerSample
        if self.name in rdf.GetColumnNames():
            return rdf
        return rdf.Define(self.name,self.expr)

class AddWeight(SimpleExprFlowStep):
    def __init__(self, name, expr, onData=False, onDataDriven=False, **options):
        super().__init__(name, expr, onData=onData, onDataDriven=onDataDriven, **options)
    def _attach(self,rdf):
        return rdf.Redefine("weight","weight*(%s)"%self.expr)

class AddWeightUncertainty(FlowStep):
    def __init__(self, name, exprUp, exprDown=None, nominal="1.0", **options):
        super().__init__(name, **options)
        self.nominal = nominal
        if exprDown is not None:
            self.vars = (exprDown, exprUp)
        else:
            self.vars = ("({0})/({1})".format(nominal,exprUp), exprUp)
    def _attach(self,rdf):
        rdf = rdf.Define(self.name, str(self.nominal))
        rdf = rdf.Vary(self.name, "ROOT::RVecD{%s, %s}" % self.vars, variationTags=["down","up"])
        return rdf.Redefine("weight","weight*(%s)"%self.name)
    def __eq__(self, other) -> bool:
        if other.__class__ == self.__class__:
            return FlowStep._equals(self, other) and self.nominal == other.nominal and self.vars == other.vars
        return id(self) == id(other)
    def _addToHash(self,hasher):
        super()._addToHash(hasher)
        _recursiveAddToHash(self.nominal, hasher)
        _recursiveAddToHash(self.vars, hasher)


class Flow(object):
    def __init__(self, name, *steps, **options):
        self.name = name
        self.steps = Flow._flatten(steps) # type: List[FlowStep]
        for k,v in options.items():
            setattr(self, k, v)
    @staticmethod
    def _flatten(steps):
        ret = []
        for s in steps:
            if type(s) == list:
                ret += Flow._flatten(s)
            else:
                assert(isinstance(s,FlowStep))
                ret.append(s)
        return ret
    def clone(self, newName=None):
        ret = copy.copy(self)
        if newName: ret.name = newName
        ret.steps = copy.copy(self.steps)
        ret._from = self
        return ret
    def prepend(self, *steps):
        self.steps[0:0] = Flow._flatten(steps)
        return self
    def append(self, *steps):
        self.steps += Flow._flatten(steps)
        return self
    def filterSteps(self, filter):
        self.steps = [ s for s in self.steps if filter(s)]
        return self
    def insertBeforeOrAfter(self, when : str, name, *steps):
        assert(when in ("before","after"))
        newSteps = []
        found = True
        for s in self.steps:
            if s.name == name and when == "before":
                newSteps += Flow._flatten(steps)
            newSteps.append(s)
            if s.name == name and when == "after":
                newSteps += Flow._flatten(steps)
        self.steps = newSteps
        if not found: raise RuntimeError("Not found step %s in flow %s" % (name,self.name))
        return self
    def attach(self, rdf, sample : Sample, era):
        assert(isinstance(sample,Sample))
        for s in self.steps:
            if s.appliesTo(sample,era):
                rdf = s.attach(rdf)
        return rdf

class Target(object):
    def __init__(self, name):
        self.name = name
    def attach(self, rdf, sample, era):
        raise RuntimeError("Must be implemented by subclass")
    def finish(self, rdf, sample, era):
        pass

class _Branch(object):
    def __init__(self, step : FlowStep, rdf, hasher = None):
        self.step = step
        self.rdf = rdf
        self.branches = [] # type: List["_Branch"]
        self.leaves = dict() # type: Mapping[Target, Any]
        self.hasher = hashlib.sha256() if hasher == None else hasher # type: hashlib.sha256
        if step: step._addToHash(self.hasher)
    def maybeBranch(self, step : FlowStep, verbose=False):
        for b in self.branches:
            if b.step == step:
                if verbose: print(" Re-used branch for step %s: %s: %s" % (step.name, step, b.hasher.hexdigest()))
                return b
        b = _Branch(step, step.attach(self.rdf), self.hasher.copy())
        if verbose: print(" Created new branch for step %s: %s: %s" % (step.name, step, b.hasher.hexdigest()))
        self.branches.append(b)
        return b

class Forest(object):
    def __init__(self):
        self._trees = dict() # type: Dict[Source,_Branch]
    def growBranch(self, source : Source, flow : Flow, treeName="Events", verbose=False):
        if source not in self._trees:
            if verbose: print("Created new source tree for %s" % source.longId())
            self._trees[source] = _Branch(None,source.createRDF(treeName))
        else:
            if verbose: print("Reused source for %s" % source.longId())
        tree = self._trees[source]
        for step in flow.steps:
            tree = tree.maybeBranch(step, verbose=verbose)
        return tree
    def growLeaves(self, source : Source, flow : Flow, targets : List[Target], sample : Sample, era, treeName="Events", verbose=False):
        branch = self.growBranch(source, flow, treeName=treeName, verbose=verbose)
        futures = []
        for t in targets:
            if t not in branch.leaves:
                branch.leaves[t] = t.attach(branch.rdf, sample, era)
            futures.append((t,branch.leaves[t]))
        return futures
    def clear(self):
        self._trees.clear()

class Processor(object):
    def __init__(self):
        self._forest = Forest()
        self._summer = GenWeightProvider()
        self.clear()
    def clear(self):
        self._futures = []
        if self._forest: self._forest.clear()
    def book(self, processes : List[Process], lumi, flows : Union[Flow,List[Flow]], targets : List[Target], eras=None, taskName="", withUncertainties=False, logPerformance=True):
        t0 = time.perf_counter()
        n0 = (self._summer.nSamples(), len(self._futures))
        if eras is None: 
            eras = [None]
            lumi = {None:lumi}
        for p in processes:
            for s in p.samples:
                if s.isMC: 
                    s.bookSumWeight(self._summer, eras)
        if isinstance(flows,Flow): flows = [flows]
        for flow in flows:
            for era in eras:
                for proc in processes:
                    procKey = MultiKey(taskName=taskName, flow=flow.name, era=era, process=proc.name)
                    for sample in proc.samples:
                        src = sample.source(era)
                        if not src: continue
                        sampleKey = procKey.addKeys(sample=sample.name)
                        if sample.isMC:
                            sflow = sample.customizeFlow(flow.clone(), lumi[era], self._summer.provider(), era=era)
                        else:
                            sflow = sample.customizeFlow(flow.clone(), era=era)
                        futures = self._forest.growLeaves(src, sflow, targets, sample, era)
                        for t,fut in futures:
                            if fut is None: continue
                            vars = ROOT.RDF.Experimental.VariationsFor(fut) if withUncertainties else None
                            self._futures.append((sampleKey.addKeys(name = t.name), proc, sample, t, fut, vars))         
        t1 = time.perf_counter()
        n1 = (self._summer.nSamples(), len(self._futures))
        if logPerformance: print("Booked %d sums and %d targets in %.3fs" % ((n1[0]-n0[0]),(n1[1]-n0[1]),t1-t0))
        return self
    def runAllRaw(self, logPerformance=True):
        """returns a MultiReport with value being (process,sample,target,future,vars)"""
        t0 = time.perf_counter()
        n0 = (self._summer.nSamples(), len(self._futures))
        self._summer.runAll()
        t0b = time.perf_counter()
        if logPerformance: print("Filled %d sums in %.3fs" % (n0[0],t0b-t0))
        # run the graphs
        ROOT.RDF.RunGraphs([fut[-2] for fut in self._futures])
        t1 = time.perf_counter()
        if logPerformance: print("Filled %d sums and %d targets in %.3fs (+%.3f)" % (n0[0],n0[1],t1-t0,t1-t0b))
        # finalize the plots
        ret = MultiReport()
        for (plotKey, proc, sample, target, future, vars) in self._futures:
            ret.append(plotKey, (proc, sample, target, future, vars))
        return ret