from CMGRDF import Flow, Cut

#! Just a dummy function to test the argument parsing with functions
def mccFlow(region="Signal", toprint= 0):
    print(f"type {type(toprint)} {toprint}")
    if region=="Signal":
        print("Signal region")
    elif region=="Control":
        print("Control region")

    return Flow("alwaysTrue", [Cut("alwaysTrue", "1")])