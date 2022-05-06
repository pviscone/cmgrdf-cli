import copy
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.IgnoreCommandLineOptions = True

class Source(object):
    def __init__(self,files):
        self.files = files
    def createRDF(self,treeName="Events"):
        if len(self.files) == 1:
            ret = ROOT.RDataFrame(treeName,self.files[0])
        else:
            chain = ROOT.TChain(treeName)
            for f in self.files: chain.Add(f)
            ret = ROOT.RDataFrame(treeName,chain)
        return ret

class Sample(object):
    def __init__(self,name,files,hooks=[],**options):
        self.name = name
        if type(files) != list: files = [files]
        self.source = Source([f.format(name=name) for f in files])
        self._hooks = hooks[:]
        for k,v in options.items():
            setattr(self,k,v)
        self.isMC = False
        self.isDataDriven = False
        self.isData = False
    def customizeFlow(self, flow, luminosity):
        for h in self._hooks:
            flow2 = h.customizeFlow(h)
            if flow2 != flow:
                flow2._from = flow
                flow = flow2
        return flow

class MCSample(Sample): 
    def __init__(self,name,samples,**options):
        super(MCSample,self).__init__(name,samples,**options)
        self.isMC = True
        if not hasattr(self, "genWeightName"): 
            self.genWeightName = "genWeight"
        if not hasattr(self, "genSumWeightName"): 
            self.genSumWeightName = "_auto_"
    def customizeFlow(self, flow, luminosity):
        return flow.clone().prepend(
                DefinePerSample("sampleWeight", "{0}*{1}*{2}".format(self.genWeightName,self.xsec,luminosity*1000)),
                Define("weight", "sampleWeight*({})".format(getattr(self,"weight",1))))
    def getWeightSumsFutureList(self):
        if not hasattr(self,"_genWeightSum") and not hasattr(self,"_genWeightSumFuture"):
            savErrorLevel = ROOT.gErrorIgnoreLevel; ROOT.gErrorIgnoreLevel = ROOT.kError;
            self._runsRdf = self.source.createRDF("Runs")
            if self.genSumWeightName == "_auto_":
                colsvec = self._runsRdf.GetColumnNames()
                cols = [ colsvec[i] for i in range(colsvec.size()) ]
                for name in "genEventSumw", "genEventSumw_":
                    if name in cols:
                        self.genSumWeightName = name
                        break
            self._genWeightSumFuture = self._runsRdf.Sum(self.genSumWeightName)
            ROOT.gErrorIgnoreLevel = savErrorLevel;
            return [ self._genWeightSumFuture ]
        return []
    def genWeightSum(self):
        if not hasattr(self,"_genWeightSum"):
            if not hasattr(self,"_genWeightSumFuture"):
                self.getWeightSumsFutureList()
            self._genWeightSum = self._genWeightSumFuture.GetValue()
            del self._runsRdf
        return self._genWeightSum

class DataDrivenSample(Sample): 
    def __init__(self,name,samples,**options):
        super(DataDrivenSample,self).__init__(name,samples,**options)
        self.isMC = False
        self.isDataDriven = True
        self.isData = False
    def customizeFlow(self, flow, luminosity):
        return flow.clone().prepend(
                Define("weight", getattr(self,"weight","1")))
class DataSample(DataDrivenSample): 
    def __init__(self,name,samples,**options):
        super(DataDrivenSample,self).__init__(name,samples,**options)
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
    def __init__(self,name,**options):
        self.name = name
    def attach(self,rdf):
        rdf2 = self._attach(rdf)
        if rdf2 != rdf:
            rdf2._from = rdf
            return rdf2
        else:
            return rdf
    def _attach(self,rdf):
        raise RuntimeError("_attach() not implemented")

class Cut(FlowStep):
    def __init__(self,name,expr,**options):
        super(Cut,self).__init__(name,**options)
        self.expr = expr
        for k,v in options.items():
            setattr(self,k,v)
    def _attach(self,rdf):
        return rdf.Filter(self.expr,self.name)
class Define(FlowStep):
    def __init__(self,name,expr,**options):
        super(Define,self).__init__(name,**options)
        self.expr = expr
        for k,v in options.items():
            setattr(self,k,v)
    def _attach(self,rdf):
        return rdf.Define(self.name,self.expr)
class ReDefine(FlowStep):
    def __init__(self,name,expr,**options):
        super(Define,self).__init__(name,**options)
        self.expr = expr
        for k,v in options.items():
            setattr(self,k,v)
    def _attach(self,rdf):
        return rdf.ReDefine(self.name,self.expr)
class DefinePerSample(FlowStep):
    def __init__(self,name,expr,**options):
        super(DefinePerSample,self).__init__(name,**options)
        self.expr = expr
        for k,v in options.items():
            setattr(self,k,v)
    def _attach(self,rdf):
        # FIXME
        #if hasattr(rdf,"DefinePerSample"):
        #    return rdf.DefinePerSample(self.name,self.expr)
        #else:
        return rdf.Define(self.name,self.expr)
class AddWeight(FlowStep):
    def __init__(self,name,expr,**options):
        super(AddWeight,self).__init__(name,**options)
        self.expr = expr
        self.data = False
        self.mc = True
        for k,v in options.items():
            setattr(self,k,v)
    def _attach(self,rdf):
        return rdf.Redefine("weight","weight*(%s)"%self.expr)

class Flow(object):
    def __init__(self, name, *steps, **options):
        self.name = name
        self.steps = list(steps)
        for k,v in options.items():
            setattr(self,k,v)
    def clone(self):
        ret = copy.copy(self)
        ret.steps = copy.copy(self.steps)
        ret._from = self
        return ret
    def prepend(self,*steps):
        self.steps[0:0] = steps
        return self
    def append(self,*steps):
        self.steps += steps
        return self
    def attach(self,rdf):
        for s in self.steps:
            rdf = s.attach(rdf)
        return rdf

