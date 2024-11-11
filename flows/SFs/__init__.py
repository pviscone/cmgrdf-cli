from CMGRDF.flow import FlowStep
from CMGRDF.utils import _recursiveAddToHash


class BaseCorrection(FlowStep):
    def __init__(self, name, *args, doSyst=True, nuisName=None, era=None, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._isCorrection = True
        self.doSyst = doSyst
        self._init = False
        self.nuisName = nuisName if nuisName else name

        self.era = era
        if self.era is not None and hasattr(self, "init"):
            self.init(era=self.era)


class BranchCorrection(BaseCorrection):
    def __init__(
        self,
        name,
        nominal,
        exprUp=None,
        exprDown=None,
        nuisName=None,
        redefine=True,
        doSyst=True,
        preserve=False,
        **kwargs,
    ):
        if doSyst and (exprUp is None or exprDown is None):
            raise ValueError("exprUp and exprDown must be defined for systematics")

        super().__init__(name, doSyst=doSyst, nuisName=nuisName, **kwargs)
        self.nominal = nominal
        self.exprUp = exprUp
        self.exprDown = exprDown
        self.redefine = redefine
        self._init = True

        #! In some cases preserving a branch is needed (e.g if the redefined variable is then used for the variation)
        #! This is needed because Varying and then redefining will throw an invalid pointer error
        if isinstance(preserve, str):
            self.preserve = [self.preserve]
        else:
            self.preserve = preserve

    def _attach(self, rdf):
        if self.preserve:
            for preserve in self.preserve:
                rdf = rdf.Define(f"_OLD_{preserve}_", preserve)

        rdf_func = "Redefine" if self.redefine else "Define"
        rdf = getattr(rdf, rdf_func)(self.name, self.nominal)
        if self.doSyst:
            rdf = rdf.Vary(
                self.name,
                f"ROOT::RVec<ROOT::RVecF>{{{self.exprDown}, {self.exprUp}}}",
                variationTags=["down", "up"],
                variationName=self.nuisName,
            )

        return rdf
