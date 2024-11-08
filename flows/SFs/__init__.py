from CMGRDF.flow import FlowStep


class BaseCorrection(FlowStep):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._isCorrection = True