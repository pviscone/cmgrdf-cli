import copy
import hashlib
import re
from typing import Dict, List, Union
from utils import OptionDecl, Options, recursiveHash, _recursiveAddToHash
import os.path
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.IgnoreCommandLineOptions = True

class Source(object):
    def __init__(self, name : str, files, era = None, friends=None): ## TODO: add support for friends here
        if type(files) == str: files = [files]
        else: assert(len(files) >= 1)
        self.name = name if name else Source._autoName(files)
        self.files = files
        self.era = era
        self.friends = friends
        self._bigHash = None
    def createRDF(self, treeName="Events"):
        if len(self.files) == 1:
            if os.path.isdir(self.files[0]):
                if treeName == "Events": assert(self.friends == None) # not supported
                ret = ROOT.RDataFrame(treeName,self.files[0]+"/*.root")
            else:
                if treeName == "Events" and self.friends != None:
                    tfile = ROOT.TFile.Open(self.files[0])
                    tree = tfile.Get(treeName)
                    for f in self.friends:
                        if type(f) == tuple:
                            tree.AddFriend(f[0],f[1])
                        elif type(f) == str: 
                            tree.AddFriend("Friends",f)
                        else: 
                            raise RuntimeError("Unsupported friend %r for %s" % (f,self))
                    ret = ROOT.RDataFrame(tree)
                    ret._tree = tree
                    ret._tfile = tfile
                else:
                    ret = ROOT.RDataFrame(treeName,self.files[0])
        else:
            chain = ROOT.TChain(treeName)
            for f in self.files: chain.Add(f)
            friendChains = []
            if treeName == "Events": 
                if self.friends != None:
                    #print("Creating friends for %s %s" % (treeName, self.longId()))
                    for i,files in enumerate(self.friends):
                        #print(" -> creating chain for friend %d: %s" % (i+1,files[:2]))
                        ftname = "Friends"
                        if type(files) == tuple:    
                            ftname = files[0]
                            files = files[1]
                        fchain = ROOT.TChain(ftname)#"iFriends%d" % (i+1))
                        for f in files: fchain.Add(f) #f"{f}?#{ftname}")
                        chain.AddFriend(fchain)
                        friendChains.append(fchain)
            ret = ROOT.RDataFrame(chain)
            ret._chain = chain
            ret._friendChains = friendChains
            #print("RDF for %s %s: chain %s, friends %s" % (treeName, self.longId(), chain, friendChains))
        #print("RDF for %s %s: FO branches %s" % (treeName, self.longId(), [s for s in ret.GetColumnNames() if "FO" in str(s)]))
        return ret
    def __eq__(self, o : object) -> bool:
        if o.__class__ == Source:
            return o.name == self.name and o.files == self.files and o.era == self.era and o.friends == self.friends
        else:
            return id(self) == id(o)
    def bigHash(self):
        if not self._bigHash: self._makeBigHash()
        return self._bigHash
    def _makeBigHash(self):
        if os.path.exists(self.files[0]): # files may not exist if e.g. they're globs or root URLs
            tsfiles = [(f,os.path.getmtime(f)) for f in self.files]
            tsfriends = []
            if self.friends:
                for f in self.friends:
                    if type(f) == tuple:
                        if len(self.files) == 1:
                            tsfriends.append((f[0],f[1],os.path.getmtime(f[1])))
                        else:
                            for fi in f[1]: 
                                tsfriends.append((f[0],fi,os.path.getmtime(fi)))
                    else:
                        if len(self.files) == 1:
                            tsfriends.append((f,os.path.getmtime(f)))
                        else:
                            for fi in f:
                                tsfriends.append((fi,os.path.getmtime(fi)))
            self._bigHash = recursiveHash(self.name,self.era,tsfiles,tsfriends)
        else:
            self._bigHash = recursiveHash(self.name,self.era,self.files,self.friends)
    def __hash__(self):
        return hash(self.bigHash())
    def safeName(self):
        return re.sub("[^A-Za-z0-9_]","",self.name)
    def longId(self):
        return "%s-%s-%s" % (self.safeName(), self.era if self.era else "", self.bigHash())
    def __str__(self):
        return "Source(%s%s, %d files[%s%s]%s, id %s)" % (
            self.name, (", era %s" % self.era) if self.era else "",
            len(self.files), self.files[0], ", ..." if len(self.files) > 1 else "",
            (", %d friends[%s, ...]" % (len(self.friends), self.friends[0])) if self.friends else "",
            self.bigHash()
        )
    @staticmethod
    def _autoName(files: List[str]) -> str:
        assert(files)
        if len(files) > 1 or files[0].endswith("/*.root"):
            return os.path.basename(os.path.dirname(files[0]))
        else:
            return os.path.basename(files[0]).replace("*","").replace(".root","")

class Sample(object):
    #options = Options(
    #                OptionDecl("eras", None, help="If specified, it can be a list of eras (e.g. years)"))
    def __init__(self, name : str, source, hooks=[], eras=None, friends=None, **kwargs):
        """source can be any 4 of the following:
             - a source object, if this sample doesn't have a list of eras
             - a dict (era -> Source) if this sample has a list of eras.
             - a string, being a file name or directory name or glob string, which may include {name} and/or {era} inside
             - a dict (era -> String) if this sample has a list of eras
        """
        self.name = name
        self._hooks = hooks[:]
        self.eras = eras
        for k,v in kwargs.items():
            setattr(self,k,v)
        if self.eras:
            if type(source) == str:
                friendFiles = dict((era, [ f.format(name=name, era=era) for f in friends] if friends else None) for era in self.eras)
                self._sources = dict((era, Source('', source.format(name=name, era=era), era=era, friends=friendFiles[era])) for era in self.eras)
            else:
                self._sources = dict((era, source[era]) for era in self.eras)
        elif isinstance(source,Source):
            assert(friends == None) # should have been put in the Source object
            self._source = source
        else:
            friendFiles = [ f.format(name=name) for f in friends] if friends else None
            self._source = Source('', source.format(name = name), friends=friendFiles)
        self.isMC = False
        self.isDataDriven = False
        self.isData = False
    def source(self, era = None):
        if era != None:
            assert(self.eras != None)
            return self._sources[era] if era in self._sources else None
        else:
            assert(self.eras == None)
            return self._source
    def hasEra(self, era):
        if era != None:
            assert(self.eras != None)
            return era in self._sources
        else:
            assert(self.eras == None)
            return True
    def customizeFlow(self, flow, era=None):
        for h in self._hooks:
            flow2 = h.customizeFlow(flow, era=era)
            if flow2 != flow:
                flow2._from = flow
                flow = flow2
        if era:
            flow.filterSteps(lambda s : s.appliesTo(self,era))
        return flow

class MCSample(Sample): 
   #__options = Sample.options.cloneAndExtend(
   #                OptionDecl("genWeightName", "genWeight", help="Generator weight (added to thhe default weight)"),
   #                OptionDecl("genWeightSum", None, help="Pre-computed sum of generator weights [for each era]. If not specified, will be computed from genSumWeightName"),
   #                OptionDecl("genSumWeightName", "_auto_", help="Generator weight sum name in the Runs tree. _auto_ selects 'genEventSumw' or 'genEventSumw_' depending on what is available"),
   #                OptionDecl("xsec", "1.0", help="Cross section times BR, in pb (can be a branch name)"))
    def __init__(self, name : str, source, genWeightName="genWeight", genWeightSum=None, genSumWeightName="_auto_", xsec="1.0", **kwargs):
        super().__init__(name, source, **kwargs)
        self.genWeightName = genWeightName
        if self.eras:
            if genWeightSum:
                self._genWeightSum = genWeightSum
            else:
                self._genWeightSum = dict((e,None) for e in self.eras)
        else:
            self._genWeightSum = {None:genWeightSum}
        self.genSumWeightName = genSumWeightName
        self.xsec = xsec
        self.isMC = True
    def customizeFlow(self, flow, luminosity, sumWeightProvider, era=None):
        flow2 = super().customizeFlow(flow, era=era)
        return flow2.prepend(
                DefinePerSample("genWeightSum", sumWeightProvider),
                Define("sampleWeight", "{0}*{1}*{2}/genWeightSum".format(self.genWeightName,self.xsec,luminosity*1000)),
                Define("weight", "sampleWeight*({})".format(getattr(self,"weight",1))))
    def genWeightSum(self,era=None):
        assert((self.eras is None) == (era == None))
        return self._genWeightSum[era]
    def bookSumWeight(self, sumWeightProvider, eras):
        sumWeightProvider.bookEras(self, eras)        

def _mergeEras(samples):
    if all((s.eras == None) for s in samples):
        return None
    else:
        return list(set([e for s in samples for e in s.eras])) # make unique
def _mergeSources(name, samples):
    eras = _mergeEras(samples)
    if eras is None: eras = [None]
    sources = dict()
    for e in eras:
        files, friends = [], None
        for s in samples:
            src = s.source(e)
            if src == None: continue
            assert(len(src.files) == 1)
            files.append(src.files[0])
            if friends is None:
                friends = [[f] for f in src.friends ]
            else:
                for i,f in enumerate(src.friends):
                    friends[i].append(f)
        sources[e] = Source(name, files, era=e, friends=friends)
    return sources if eras != [None] else sources[None]

class MCGroup(Sample): 
    def __init__(self, name : str, samples : List[MCSample], moreHooks=[], extraWeight=None):
        super().__init__(name, _mergeSources(name, samples), eras=_mergeEras(samples))
        self.samples = samples
        self._hooks = samples[0]._hooks[:]
        for s in samples[1:]: assert(s._hooks == self._hooks)
        self._hooks += moreHooks[:]
        self.xsec = samples[0].xsec
        for s in samples[1:]: assert(s.xsec == self.xsec)
        self.genWeightName = samples[0].genWeightName
        for s in samples[1:]: assert(s.genWeightName == self.genWeightName)
        self.weight = getattr(samples[0], 'weight', 1)
        for s in samples[1:]: assert(getattr(s, 'weight', 1) == self.weight)
        if extraWeight:
            self.weight = "({})*({})" % (self.weight, extraWeight)
        self.isMC = True
    def customizeFlow(self, flow, luminosity, sumWeightProvider, era=None):
        flow2 = super().customizeFlow(flow, era=era)
        return flow2.prepend(
                #DefinePerSample("genWeightSum", sumWeightProvider),
                #Define("sampleWeight", "{0}*{1}*{2}/genWeightSum".format(self.genWeightName,self.xsec,luminosity*1000)),
                Define("sampleWeight", "{0}*{1}*{2}".format(self.genWeightName,self.xsec,luminosity*1000)),
                Define("weight", "sampleWeight*({})".format(self.weight)))
    def bookSumWeight(self, sumWeightProvider, eras):
        for s in self.samples:
            sumWeightProvider.bookEras(s, eras)

class DataDrivenSample(Sample): 
    #defaults = Sample.defaults.cloneAndExtend(
    #            OptionDecl("weight", "1", help="Starting weight for this sample"))
    def __init__(self, name, source, weight="1", **options):
        super().__init__(name, source, **options)
        self.weight = weight
        self.isMC = False
        self.isDataDriven = True
        self.isData = False
    def customizeFlow(self, flow, era):
        flow2 = super().customizeFlow(flow, era=era)
        return flow2.prepend(
                Define("weight", getattr(self,"weight","1")))

class DataSample(DataDrivenSample): 
    def __init__(self,name,samples,**options):
        super().__init__(name, samples, **options)
        self.isData = True

class Process(object):
    def __init__(self,name,samples,**options):
        self.name = name
        self.samples = samples
        for k,v in options.items():
            setattr(self,k,v)
        if "label" not in options: self.label = self.name
        self.isData = False
        self.isSignal = self.getOpt("signal",False)
    def getOpt(self, name, default=None):
        return getattr(self, name, default)

class Data(Process):
    def __init__(self,samples,**options):
        if "label" not in options: options["label"] = "Data"
        super(Data,self).__init__("data",samples,**options)
        self.isData = True

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


class Append(object):
    def __init__(self, *steps : List[FlowStep]):
        self.steps = list(steps)
    def customizeFlow(self, flow, era):
        return flow.append(self.steps)

class Insert(object):
    def __init__(self, *steps : List[FlowStep], before=None, after=None):
        self.steps = list(steps)
        if before != None:
            assert(after == None)
            self.when = ("before", before)
        elif after != None:
            assert(before == None)
            self.when = ("after", after)
        else:
            raise RuntimeError("Must specify either before or after")
    def customizeFlow(self, flow : "Flow", era):
        return flow.insertBeforeOrAfter(self.when[0], self.when[1], *self.steps)

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
    def grow(self, source : Source, flow : Flow, treeName="Events", verbose=False):
        if source not in self._trees:
            if verbose: print("Created new source tree for %s" % source.longId())
            self._trees[source] = _Branch(None,source.createRDF(treeName))
        else:
            if verbose: print("Reused source for %s" % source.longId())
        tree = self._trees[source]
        for step in flow.steps:
            tree = tree.maybeBranch(step, verbose=verbose)
        return tree.rdf
    def clear(self):
        self._trees.clear()
