from CMGRDF.flow import FlowStep
from CMGRDF.utils import _recursiveAddToHash


class DefineSkimmedCollection(FlowStep):
    def __init__(self,
                 name : str,
                 srcColl : str,
                 members : list[str],
                 optMembers : list[str] = [],
                 mask : str = None,
                 indices : str = None,
                 **options):
        super().__init__(name, **options)
        self.srcColl = srcColl
        self.members = members
        self.optMembers = optMembers
        self.mask = mask
        self.indices = indices
        if (self.mask is None) == (self.indices is None):
            raise RuntimeError(f"Error in {self.name}: must specify either mask or indices")

    def _params(self):
        return (self.srcColl,
                self.members, self.optMembers,
                self.mask, self.indices)

    def _attach(self, rdf):
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
