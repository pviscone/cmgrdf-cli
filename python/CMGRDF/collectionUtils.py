from typing import Optional, Union
from CMGRDF.flow import Define, FlowStep
from CMGRDF.utils import _recursiveAddToHash

class DefineFromCollection(FlowStep):
    """Define new scalar branchs looping over the members of a collection.
    Index can be an explicit index or a string with the name of the index branch (ex. 0 or LepGood_photonIdx[0])
    (ex To define LepGood1_pt. DefineFromCollection("LepGood1",members=["pt"],index="iLepFO_Recl[0]") )
    """

    def __init__(self, name, srcColl, members : "list[str]" = None, index = None, **options):
        super().__init__(name, **options)
        self.members=members
        self.srcColl=srcColl
        self.index=str(index)
        if index is None:
            raise RuntimeError(f"Error in {self.name}: must specify index")


    def _attach(self, rdf):
        if self.members is None:
            self.members = [branch.c_str().split(f"{self.srcColl}_",1)[1] for branch in rdf.GetColumnNames()
                            if branch.c_str().startswith((f"{self.srcColl}_",f"Friends.{self.srcColl}_"))]
            self.members=list(dict.fromkeys(self.members)) #Remove duplicates


        for m in self.members:
            try:
                rdf=rdf.Define(f"{self.name}_{m}", f"{self.srcColl}_{m}[{self.index}]")
            except BaseException:
                print(f"ERROR attaching Define({self.name}, {self.srcColl}_{m}[{self.index}]")
                raise
        return rdf

class DefineSkimmedCollection(FlowStep):
    """Make a subcollection of a collection, given a cut, bool mask, or vector of indices, and a list of members to copy"""

    def __init__(self,
                 name : str,
                 srcColl : str,
                 members : "list[str]" = None,
                 optMembers : "list[str]" = [],
                 cut : str = None,
                 mask : str = None,
                 indices : str = None,
                 redefine=False,
                 **options):
        super().__init__(name, **options)
        self.srcColl = srcColl
        self.members = members
        self.optMembers = optMembers
        self.cut = cut
        self.mask = mask
        self.indices = indices
        if len([x for x in (cut, mask, indices) if x is not None]) != 1:
            raise RuntimeError(f"Error in {self.name}: must specify exactly one of cut, mask or indices")
        if self.cut is not None:
            self.mask = srcColl + "_is" + name
        self.rdf_func = "Redefine" if redefine else "Define"

    def _params(self):
        return (self.srcColl,
                self.members, self.optMembers,
                self.cut, self.mask, self.indices)

    def _attach(self, rdf):
        if self.members is None:
            self.members = [branch.c_str().split(f"{self.srcColl}_",1)[1] for branch in rdf.GetColumnNames()
                            if branch.c_str().startswith((f"{self.srcColl}_",f"Friends.{self.srcColl}_"))]
            self.members=list(dict.fromkeys(self.members)) #Remove duplicates
        if self.cut:
            rdf = getattr(rdf,self.rdf_func)(self.mask, self.cut)
        if self.mask:
            rdf = getattr(rdf,self.rdf_func)(f"n{self.name}", f"Sum({self.mask})")
            copyexpr = f"{self.srcColl}_{{m}}[{self.mask}]"
        elif self.indices:
            rdf = getattr(rdf,self.rdf_func)(f"n{self.name}", f"{self.indices}.size()")
            copyexpr = f"Take({self.srcColl}_{{m}}, {self.indices})"
        for m in self.members:
            rdf = getattr(rdf,self.rdf_func)(f"{self.name}_{m}", copyexpr.format(m=m))
        cols = set(rdf.GetColumnNames())
        for m in self.optMembers:
            if f"{self.srcColl}_{m}" in cols:
                rdf = getattr(rdf,self.rdf_func)(f"{self.name}_{m}", copyexpr.format(m=m))
        return rdf

    def __eq__(self, other) -> bool:
        if other.__class__ == self.__class__:
            return FlowStep._equals(self, other) and self._params() == other._params()
        return id(self) == id(other)

    def _addToHash(self, hasher):
        super()._addToHash(hasher)
        _recursiveAddToHash(self._params(), hasher)


class DefineP4(Define):
    """Build the 4-vector for a collection of objects"""

    def __init__(self,
                 coll : str,
                 mass : Union[str, float] = "mass",
                 pt : str = "pt",
                 eta : str = "eta",
                 phi : str = "phi",
                 #energy : Optional[str] = None,
                 name : str = "p4",
                 **options):
        massvar = str(mass) if isinstance(mass, float) else f"{coll}_{mass}"
        #if energy is not None:
        #    expr = f"makeP4E({coll}_{energy},{coll}_{eta},{coll}_{phi},{massvar})"
        #else:
        expr = f"makeP4({coll}_{pt},{coll}_{eta},{coll}_{phi},{massvar})"
        super().__init__(f"{coll}_{name}", expr, **options)


class DefinePairs(Define):
    """Define a list of pairs for all combinations of objects in a collection, with optional requirements on charge or flavour"""

    def __init__(self,
                 name : str,
                 coll : str,
                 kind : Optional[str] = None,
                 pdgId : str = "pdgId",
                 **options):
        if kind is None:
            expr = f"allPairs(n{coll})"
        elif kind in ("OS", "SS"):
            expr = f"pairs{kind}({coll}_{pdgId})"
        elif kind in ("SFOS", "SFSS", "DFOS"):
            expr = f"pairs{kind}({coll}_{pdgId})"
        else:
            raise RuntimeError("kind can only be None, 'OS', 'SS', 'SFOS', 'SFSS', 'DFOS'")
        super().__init__(name, expr, **options)


class DefineMinMass(Define):
    def __init__(self,
                 name : str,
                 coll : str,
                 kind : Optional[str] = None,
                 p4 : str = "p4",
                 pdgId : str = "pdgId",
                 **options):
        if kind is None:
            pairs = f"allPairs(n{coll})"
        elif kind in ("OS", "SS"):
            pairs = f"pairs{kind}({coll}_{pdgId})"
        elif kind in ("SFOS", "SFSS", "DFOS"):
            pairs = f"pairs{kind}({coll}_{pdgId})"
        else:
            raise RuntimeError("kind can only be None, 'OS', 'SS', 'SFOS', 'SFSS', 'DFOS'")
        super().__init__(name, f"minPairMass({pairs}, {coll}_{p4})", **options)
