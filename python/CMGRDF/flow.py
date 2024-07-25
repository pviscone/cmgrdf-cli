import copy
import re
import ROOT
from CMGRDF.data import Sample
from CMGRDF.utils import _recursiveAddToHash, safeName


class FlowStep(object):
    """A generic step to the processing flow.

       Subclasses should implement the following methods:
          * _attach(self, rdf):
                add any RDF processing instructions and return the tip of the new graph
          * _getAdditionalWeights: (optional, the default returns None)
                returns a list of column names of weights that are to be
                multiplied together in the final event weight
          * `__eq__(self, other) -> bool`:
                return true if this step is identical to the other
                and so there's no need to instantiate both.
                In the implementation, you can call `FlowStep._equals(self, other)`
                to check the equivalence of the base class datamembers
         * `_addToHash(self,hasher):`
                Add information about this step to a hash, used for caching.
                You can implement it as
                ```
                    super()._addToHash(hasher)
                    _recursiveAddToHash( (all your datamembers), hasher)
                ```

    """

    def __init__(self, name, onMC=True, onDataDriven=True, onData=True, eras=None, sample=None, **options):
        if sample and not onMC:
            raise RuntimeError("Cannot specify sample pattern for a non-MC step")

        self.name = name
        self.onMC = onMC
        self.onData = onData
        self.onDataDriven = onDataDriven
        self.eras = eras
        self.sample = sample #regex pattern
        for k, v in options.items():
            setattr(self, k, v)

    def appliesTo(self, sample : Sample, era) -> bool:
        assert isinstance(sample, Sample)
        if sample.isMC:
            if not self.onMC:
                return False
            elif self.sample:
                return bool(re.match(self.sample,sample.name))
        elif sample.isData:
            if not self.onData:
                return False
        elif sample.isDataDriven:
            if not self.onDataDriven:
                return False
        if self.eras and (era not in self.eras):
            return False
        return True

    def _getAdditionalWeights(self):
        return None

    def attach(self, rdf, weights):
        rdf2 = self._attach(rdf)
        if rdf2 != rdf:
            rdf2._from = rdf
        w = self._getAdditionalWeights()
        if w:
            weights = weights[:] + w
        return (rdf2, weights)

    @staticmethod
    def _equals(obj1, obj2):
        return (obj1.name == obj2.name and
                obj1.onMC == obj2.onMC and
                obj1.onData == obj2.onData and
                obj1.onDataDriven == obj2.onDataDriven and
                obj1.eras == obj2.eras)

    def _addToHash(self, hasher):
        _recursiveAddToHash((self.__class__.__name__, self.name, self.onMC, self.onData, self.onDataDriven, self.eras), hasher)

    def __str__(self):
        out = f"\033[1m{self.__class__.__name__}({self.name})\033[0m\n"
        out += f"\tonMC: {self.onMC} onData: {self.onData} onDataDriven: {self.onDataDriven}\n"
        if self.eras:
            out += f"\teras: {self.eras}\n"
        if self.sample:
            out += f"\tsample: {self.sample}\n"
        return out

    @property
    def show(self):
        print(self)



class SimpleExprFlowStep(FlowStep):
    """ A Flow step which is fully defined by a single expression.
        This base class implements the equality and hash tests, while it's
        up to the subclass to implement _attach(self, rdf)"""

    def __init__(self, name, expr, **options):
        super().__init__(name, **options)
        self.expr = expr

    def __eq__(self, other) -> bool:
        if other.__class__ == self.__class__:
            return FlowStep._equals(self, other) and self.expr == other.expr
        return id(self) == id(other)

    def _addToHash(self, hasher):
        super()._addToHash(hasher)
        _recursiveAddToHash(self.expr, hasher)

    def __str__(self):
        out = f"\033[1m{self.__class__.__name__}({self.name},{self.expr})\033[0m\n"
        out += f"\tonMC: {self.onMC} onData: {self.onData} onDataDriven: {self.onDataDriven}\n"
        if self.eras:
            out += f"\teras: {self.eras}\n"
        if self.sample:
            out += f"\tsample: {self.sample}\n"
        return out


class Cut(SimpleExprFlowStep):
    def __init__(self, name, expr, **options):
        super().__init__(name, expr, **options)

    def _attach(self, rdf):
        try:
            return rdf.Filter(self.expr, self.name)
        except BaseException:
            print(f"ERROR attaching Cut({self.name}, {self.expr}")
            raise


class Define(SimpleExprFlowStep):
    def __init__(self, name, expr, **options):
        super().__init__(name, expr, **options)

    def _attach(self, rdf):
        try:
            return rdf.Define(self.name, self.expr)
        except BaseException:
            print(f"ERROR attaching Define({self.name}, {self.expr}")
            raise


class Alias(SimpleExprFlowStep):
    def __init__(self, name, column, **options):
        super().__init__(name, column, **options)

    def _attach(self, rdf):
        try:
            return rdf.Alias(self.name, self.expr)
        except BaseException:
            print(f"ERROR attaching Alias({self.name}, {self.expr}")
            raise


class ReDefine(SimpleExprFlowStep):
    def __init__(self, name, expr, defineIfMissing=False, **options):
        super().__init__(name, expr, **options)
        self.defineIfMissing = defineIfMissing

    def _attach(self, rdf):
        try:
            if self.defineIfMissing:
                if self.name not in rdf.GetColumnNames():
                    return rdf.Define(self.name, self.expr)
            return rdf.Redefine(self.name, self.expr)
        except BaseException:
            print(f"ERROR attaching ReDefine({self.name}, {self.expr}")
            raise


class DefinePerSample(FlowStep):
    """Attaches a DefinePerSample node.

       This currently needs to be implemented by defining a C++ class with a method
            `ROOT::RDF::RNode attachAsDefinePerSample(ROOT::RDF::RNode &rdf, const std::string &colName)`
       since Python callbacks don't work (as of ROOT 6.26.04)
    """

    def __init__(self, name, provider, *args, **options):
        super().__init__(name, **options)
        self.provider = provider
        self.args = tuple(args)
        for k, v in options.items():
            setattr(self, k, v)

    def __eq__(self, other) -> bool:
        if other.__class__ == self.__class__:
            return FlowStep._equals(self, other) and self.provider == other.provider and self.args == other.args
        return id(self) == id(other)

    def _addToHash(self, hasher):
        super()._addToHash(hasher)
        _recursiveAddToHash(self.args, hasher)

    def _attach(self, rdf):
        return self.provider.attachAsDefinePerSample(ROOT.RDF.AsRNode(rdf), self.name, *self.args)


class DefineDefault(SimpleExprFlowStep):
    """Defines a variable if it's not already present in the tree"""

    def __init__(self, name, expr, **options):
        super().__init__(name, expr, **options)

    def _attach(self, rdf):
        # FIXME use DefinePerSample
        if self.name in rdf.GetColumnNames():
            return rdf
        return rdf.Define(self.name, self.expr)


class Vary(SimpleExprFlowStep):
    """Attaches a rdf Vary node of simple type, with the name of the column and
       an expression that should return `RVec<T>` of varied values.

       Normally, it should be a vector of size 2, with element `0` being the
       down variation, and element `1` being the up variation.

       You can specify a nuisance name, if not it will be set to the column name
    """

    def __init__(self, name, expr, variationTags=["down", "up"], nuisName=None, **options):
        super().__init__(name, expr, **options)
        self.variationTags = variationTags
        self.nuisName = nuisName if nuisName else name

    def _attach(self, rdf):
        try:
            return rdf.Vary(self.name, self.expr, variationTags=self.variationTags, variationName=self.nuisName)
        except BaseException:
            print(f"ERROR attaching Vary({self.name}, {self.expr}, variationTags={self.variationTags}, variationName={self.nuisName}")
            raise


class AddWeight(SimpleExprFlowStep):
    """Attaches one weight to the RDF.

       If the weight already exists as a column, you can just specify the name.
       If not, you should specify a name and an expression to compute it, and it will `Define` it

       **Note:** by default, weights are applied only on MC, not on data
    """

    def __init__(self, name, expr="", onData=False, onDataDriven=False, **options):
        super().__init__(name, expr, onData=onData, onDataDriven=onDataDriven, **options)

    def _attach(self, rdf):
        if self.expr and (self.expr != self.name):
            try:
                return rdf.Define(self.name, self.expr)
            except BaseException:
                print(f"ERROR attaching AddWeight {self.name}: {self.expr}")
                raise
        return rdf

    def _getAdditionalWeights(self):
        return [self.name]


class AddWeightUncertainty(FlowStep):
    """Attaches one weight uncertainty.

       You must specify a name, an optional nominal expression value (default is 1.0),
       an up variation expression, and an optional down variation (default: nominal^2/up)

       **Note:** by default, weights are applied only on MC, not on data
    """

    def __init__(self, name, exprUp, exprDown=None, nominal="1.0", nuisName=None, **options):
        super().__init__(name, **options)
        self.nominal = nominal
        if exprDown is not None:
            self.vars = (exprDown, exprUp)
        else:
            self.vars = ("({0})*({0})/({1})".format(nominal, exprUp), exprUp)
        self.nuisName = nuisName if nuisName else name

    def _attach(self, rdf):
        rdf = rdf.Define(self.name, str(self.nominal))
        rdf = rdf.Vary(self.name, "ROOT::RVecD{%s, %s}" % self.vars, variationTags=["down", "up"], variationName=self.nuisName)
        return rdf

    def _getAdditionalWeights(self):
        return [self.name]

    def __eq__(self, other) -> bool:
        if other.__class__ == self.__class__:
            return FlowStep._equals(self, other) and self.nominal == other.nominal and self.vars == other.vars
        return id(self) == id(other)

    def _addToHash(self, hasher):
        super()._addToHash(hasher)
        _recursiveAddToHash(self.nominal, hasher)
        _recursiveAddToHash(self.vars, hasher)


class ComputeTotalWeight(SimpleExprFlowStep):
    """Computes the total weight, by issuing the necessary Define, Redefine or Alias"""

    def __init__(self, weights=None, name="weight"):
        super().__init__(name, "__auto__" if weights is None else "*".join(weights))
        self.weights = weights

    def attach(self, rdf, weights):
        operands = self.weights if self.weights is not None else weights
        rdf2 = self._attach(rdf, operands)
        if rdf2 != rdf:
            rdf2._from = rdf
        return (rdf2, weights)

    def _attach(self, rdf, weights):
        existing = self.name in rdf.GetColumnNames()
        expr = "*".join(weights)
        if len(weights) == 0:
            if existing:
                #print(f"Warning, new dummy define of {self.name} while a column exists in the RDF\n")
                return rdf.Redefine(self.name, "1.f")
            else:
                return rdf.Define(self.name, "1.f")
        elif len(weights) == 1:
            if existing:
                if weights[0] == self.name:
                    #print(f"Not doing anything for ({self.name}, {expr})")
                    return rdf  # nothing to do
                else:
                    #print(f"Using Redefine[1]({self.name}, {expr})")
                    return rdf.Redefine(self.name, expr)
            else:
                #print(f"Using Alias({self.name}, {expr})")
                return rdf.Alias(self.name, expr)
        else:
            if existing:
                #print(f"Using Redefine({self.name}, {expr})")
                return rdf.Redefine(self.name, expr)
            else:
                #print(f"Using Define({self.name}, {expr})")
                return rdf.Define(self.name, expr)


class Marker(FlowStep):
    """ A Flow step that does nothing at all, but can be used as a marker in the cut flow"""

    def __init__(self, name, doc="", **options):
        super().__init__(name, **options)
        self.doc = doc

    def __eq__(self, other) -> bool:
        if other.__class__ == self.__class__:
            return FlowStep._equals(self, other) and self.doc == other.doc
        return id(self) == id(other)

    def _addToHash(self, hasher):
        super()._addToHash(hasher)

    def _attach(self, rdf):
        return rdf


class Flow(object):
    """A sequence of steps, with a name."""

    def __init__(self, name, *steps, **options):
        self.name = name
        self.steps = Flow._flatten(steps)  # type: list[FlowStep]
        for k, v in options.items():
            setattr(self, k, v)

    @staticmethod
    def _flatten(steps):
        ret = []
        for s in steps:
            if isinstance(s, list):
                ret += Flow._flatten(s)
            else:
                assert isinstance(s, FlowStep)
                ret.append(s)
        return ret

    def clone(self, newName=None):
        ret = copy.copy(self)
        if newName:
            ret.name = newName
        ret.steps = copy.copy(self.steps)
        ret._from = self
        return ret

    def upToStep(self, step, included=True):
        newsteps = []
        for s in self.steps:
            newsteps.append(s)
            if s.name == step:
                if not included:
                    newsteps.pop()
                break
        self.steps = newsteps
        return self

    def fromStep(self, step, included=True):
        newsteps = []
        for s in reversed(self.steps):
            newsteps.append(s)
            if s.name == step:
                if not included:
                    newsteps.pop()
                break
        self.steps = reversed(newsteps)
        return self

    def prepend(self, *steps):
        self.steps[0:0] = Flow._flatten(steps)
        return self

    def append(self, *steps):
        self.steps += Flow._flatten(steps)
        return self

    def replace(self, name, *steps):
        matches = [i for (i, s) in enumerate(self.steps) if s.name == name]
        if len(matches) != 1:
            raise RuntimeError(f"Looking for step {name} in flow {self.name}, found {matches}")
        idx = matches[0]
        self.steps = self.steps[:idx] + Flow._flatten(steps) + self.steps[idx + 1:]
        return self

    def remove(self, *names):
        self.steps = [s for s in self.steps if s.name not in names]
        return self

    def filterSteps(self, stepFilter):
        self.steps = [s for s in self.steps if stepFilter(s)]
        return self

    def insertBeforeOrAfter(self, when : str, name, *steps):
        assert (when in ("before", "after"))
        newSteps = []
        found = True
        for s in self.steps:
            if s.name == name and when == "before":
                newSteps += Flow._flatten(steps)
            newSteps.append(s)
            if s.name == name and when == "after":
                newSteps += Flow._flatten(steps)
        self.steps = newSteps
        if not found:
            raise RuntimeError("Not found step %s in flow %s" % (name, self.name))
        return self

    def __add__(self, other_flow):
        return Flow(f"{self.name}+{other_flow.name}",[*self.steps,*other_flow.steps])

    def __getitem__(self,key):
        return self.steps[key]

    def __str__(self):
        out = f"\033[1mFlow: {self.name}\033[0m ({len(self.steps)} steps)\n\n"
        for idx,s in enumerate(self.steps):
            out +=f"\t{idx+1}. {s.__str__()}\n"
        return out

    @property
    def show(self):
        print(self)



class Target(object):
    """An endpoint of the graph, e.g. a plot, yield, or similar."""

    def __init__(self, name, mcOnly=False):
        self.name = name
        self.mcOnly = mcOnly

    def attach(self, rdf, sample, era):
        raise RuntimeError("Must be implemented by subclass")

    def bookVariations(self, future):
        """Calls RDF.Experimental.VariationsFor or any customization of it"""
        return ROOT.RDF.Experimental.VariationsFor(future)

    def finish(self, value, sample, era):
        """Performs any post-processing of the nominal value returned by the RDF future.
           This is done before caching, so it should do manipulations that affect the
           content (e.g. handling overflows), while presentation aspects (e.g. labels)
           are better done later so that they can be changed even when the object is read from cache."""
        return value

    def finishFuture(self, future, sample, era):
        """Receive a future for the nominal value, unwraps it and return the value.
           By defalut it just calls `finish(future.GetValue(), sample, era)`"""
        return self.finish(future.GetValue(), sample, era)

    def finishVarFuture(self, varfuture, sample, era):
        """Receive the RDF variations for an object, and by default unpacks them into a python map"""
        return dict((k, self.finish(varfuture[k], sample, era)) for k in varfuture.GetKeys())

    def longId(self):
        """If different from None, it should be an unique and it will allow the result to be cached."""
        return None


class Yield(Target):
    """Computes an event yield (sum of the weights), with optional stat and syst uncertainties"""

    def __init__(self, name, weight="weight", mcOnly=False):
        super(Yield, self).__init__(name, mcOnly=mcOnly)
        self.weight = weight

    def attach(self, rdf, sample, era):
        fut = rdf.Sum(self.weight)
        fut._rdf = rdf
        return fut

    def attachSumw2(self, rdf):
        return rdf.Define(self.weight + "2", self.weight + "*" + self.weight).Sum(self.weight + "2")

    def bookVariations(self, future):
        sum2 = self.attachSumw2(future._rdf)
        return (sum2, ROOT.RDF.Experimental.VariationsFor(future))

    def finishVarFuture(self, varfuture, sample, era):
        ret = dict()
        if isinstance(varfuture, tuple):
            sum2, systs = varfuture
            ret = dict((k, systs[k]) for k in systs.GetKeys())
            ret[""] = sum2.GetValue()
        else:
            ret[""] = varfuture.GetValue()
        return ret

    def __eq__(self, other):
        if other.__class__ == Yield:
            return self.name == other.name and self.weight == other.weight
        return False

    def __hash__(self):
        return hash(self.longId())

    def longId(self):
        return "%s-%s" % (safeName(self), self.weight)
