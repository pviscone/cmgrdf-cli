from typing import Any, Optional
from collections.abc import Sequence
from CMGRDF.flow import FlowStep
from CMGRDF.utils import recursiveAddToHash
import ROOT  # type: ignore


class JsonFilter(FlowStep):
    def __init__(self, filename : str, eras : Optional[list[str]] = None):
        super().__init__("JSON", onMC=False, onDataDriven=True, onData=True, eras=eras)
        self.filename = filename

    def __eq__(self, other : Any) -> bool:
        if other.__class__ == self.__class__:
            return FlowStep._equals(self, other) and self.filename == other.filename
        return id(self) == id(other)

    def _addToHash(self, hasher : Any) -> None:
        super()._addToHash(hasher)
        recursiveAddToHash(self.filename, hasher)

    def _attach(self, rdf : Any, withUncertainties : bool) -> Any:
        try:
            return rdf.Filter(f'JsonFilter::load("{self.filename}")(run,luminosityBlock)', self.name)
        except BaseException:
            print(f"ERROR attaching JsonFilter({self.name}, {self.filename}")
            raise


class TriggerBitFilter(FlowStep):
    def __init__(self,
                 selectBits : Sequence[str],
                 vetoBits : Sequence[str] = (),
                 onMC : bool = True,
                 onDataDriven : bool = True,
                 onData : bool = True,
                 eras : Optional[list[str]] = None,
                 name : str = "HLT",
                 defineDefaults : bool = False):
        """Define a filter that checks for the OR of the trigger bits in selectBits and vetos the OR of bits in vetoBits.
           defineDefaults can be used to automatically insert a DefineDefault(bit, false) for all the used bits"""
        super().__init__(name, onMC=onMC, onDataDriven=onDataDriven, onData=onData, eras=eras)
        self.selectBits = list(sorted(selectBits))
        self.vetoBits = list(sorted(vetoBits))
        self.defineDefaults = defineDefaults

    def __eq__(self, other) -> bool:
        if other.__class__ == self.__class__:
            return (FlowStep._equals(self, other) and
                    self.selectBits == other.selectBits and
                    self.vetoBits == other.vetoBits and
                    self.defineDefaults == other.defineDefaults)
        return id(self) == id(other)

    def _addToHash(self, hasher : Any) -> None:
        super()._addToHash(hasher)
        recursiveAddToHash((self.selectBits, self.vetoBits, self.defineDefaults), hasher)

    def _attach(self, rdf : Any, withUncertainties : bool) -> Any:
        try:
            if self.defineDefaults:
                if (ROOT.gROOT.GetVersionInt() >= 63400) and ("DistRDF" not in rdf.__module__):
                    for b in self.selectBits + self.vetoBits:
                        src = rdf
                        rdf = rdf.DefaultValueFor(b, False)
                        rdf._from = src
                else:
                    colnames = rdf.GetColumnNames()
                    for b in self.selectBits + self.vetoBits:
                        if b not in colnames:
                            src = rdf
                            rdf = rdf.Define(b, "false")
                            rdf._from = src
            sel = " || ".join(self.selectBits)
            veto = " || ".join(self.vetoBits)
            src = rdf
            if self.selectBits and self.vetoBits:
                rdf = rdf.Filter(f"({sel}) && !({veto})", self.name)
                rdf._from = src
            elif self.selectBits:
                rdf = rdf.Filter(sel, self.name)
                rdf._from = src
            elif self.vetoBits:
                rdf = rdf.Filter(f"!({veto})", self.name)
                rdf._from = src
            return rdf
        except BaseException:
            print(f"ERROR attaching TriggerBitFilter({self.name}, {self.selectBits}, {self.vetoBits}, {self.defineDefaults}")
            raise
