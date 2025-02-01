from collections.abc import Iterable
from typing import Optional, Union
from CMGRDF.flow import Flow, FlowStep, Hook


class Append(Hook):
    def __init__(self, *steps : Union[FlowStep, Iterable[FlowStep]]):
        self.steps = Flow.flatten(steps)

    def customizeFlow(self, flow : Flow, era : Optional[str]) -> Flow:
        return flow.append(self.steps)


class Prepend(Hook):
    def __init__(self, *steps : Union[FlowStep, Iterable[FlowStep]]):
        self.steps = Flow.flatten(steps)

    def customizeFlow(self, flow : Flow, era : Optional[str]) -> Flow:
        return flow.prepend(self.steps)


class Replace(Hook):
    def __init__(self, *steps : Union[FlowStep, Iterable[FlowStep]], name):
        self.steps = Flow.flatten(steps)
        self.name = name

    def customizeFlow(self, flow : Flow, era : Optional[str]) -> Flow:
        return flow.replace(self.name, self.steps)


class Remove(Hook):
    def __init__(self, name : str):
        self.name = name

    def customizeFlow(self, flow : Flow, era : Optional[str]) -> Flow:
        return flow.remove(self.name)


class Insert(Hook):
    def __init__(self,
                 *steps : Union[FlowStep, Iterable[FlowStep]],
                 before : Optional[str] = None,
                 after : Optional[str] = None):
        self.steps = Flow.flatten(steps)
        if before is not None:
            assert (after is None)
            self.when = ("before", before)
        elif after is not None:
            assert (before is None)
            self.when = ("after", after)
        else:
            raise RuntimeError("Must specify either before or after")

    def customizeFlow(self, flow : Flow, era : Optional[str]) -> Flow:
        return flow.insertBeforeOrAfter(self.when[0], self.when[1], *self.steps)
