from CMGRDF import Flow, Cut

#! Just a dummy function to test the argument parsing with functions
def mccFlow(region : str = "Signal", toprint : int = 0):
    print(f"type {type(toprint)} {toprint}")
    if region=="Signal":
        return Flow("Signal region",
                    [Cut("nJet>1", "nJet>1"),])
    elif region=="Control":
        return Flow("Control region",
                    [Cut("nJet<5", "nJet<5"),])


