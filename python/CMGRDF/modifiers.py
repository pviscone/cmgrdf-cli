from typing import Optional
from collections.abc import Sequence
from CMGRDF.flow import Flow, FlowStep


class Append(object):
    def __init__(self, *steps : Sequence[FlowStep]):
        self.steps = list(steps)

    def customizeFlow(self, flow : Flow, era : Optional[str]) -> Flow:
        return flow.append(self.steps)


class Prepend(object):
    def __init__(self, *steps : FlowStep):
        self.steps = list(steps)

    def customizeFlow(self, flow : Flow, era : Optional[str]) -> Flow:
        return flow.prepend(self.steps)


class Replace(object):
    def __init__(self, *steps : FlowStep, name):
        self.steps = list(steps)
        self.name = name

    def customizeFlow(self, flow : Flow, era : Optional[str]) -> Flow:
        return flow.replace(self.name, self.steps)


class Remove(object):
    def __init__(self, name : str):
        self.name = name

    def customizeFlow(self, flow : Flow, era : Optional[str]) -> Flow:
        return flow.remove(self.name)


class Insert(object):
    def __init__(self,
                 *steps : FlowStep,
                 before : Optional[str] = None,
                 after : Optional[str] = None):
        self.steps = list(steps)
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
