from typing import List
from CMGRDF.flow import Flow, FlowStep

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
