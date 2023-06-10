from typing import Optional, Union
from CMGRDF.flow import Define, FlowStep
from CMGRDF.utils import _recursiveAddToHash


class DefineSkimmedCollection(FlowStep):
    """Make a subcollection of a collection, given a cut, bool mask, or vector of indices, and a list of members to copy"""

    def __init__(self,
                 name : str,
                 srcColl : str,
                 members : "list[str]",
                 optMembers : "list[str]" = [],
                 cut : str = None,
                 mask : str = None,
                 indices : str = None,
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

    def _params(self):
        return (self.srcColl,
                self.members, self.optMembers,
                self.cut, self.mask, self.indices)

    def _attach(self, rdf):
        if self.cut:
            rdf = rdf.Define(self.mask, self.cut)
        if self.mask:
            rdf = rdf.Define(f"n{self.name}", f"Sum({self.mask})")
            copyexpr = f"{self.srcColl}_{{m}}[{self.mask}]"
        elif self.indices:
            rdf = rdf.Define(f"n{self.name}", f"{self.mask}.size()")
            copyexpr = f"Take({self.srcColl}_{{m}}, {self.indices})"
        for m in self.members:
            rdf = rdf.Define(f"{self.name}_{m}", copyexpr.format(m=m))
        cols = set(rdf.GetColumnNames())
        for m in self.optMembers:
            if m in cols:
                rdf = rdf.Define(f"{self.name}_{m}", copyexpr.format(m=m))
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
