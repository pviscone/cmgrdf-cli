from CMGRDF import Flow, Define, Cut
from CMGRDF.collectionUtils import DefineP4

flow = Flow(
    "example",
    [
        Cut("2ele", "nElectron >= 2"),
        DefineP4("Electron", massvar="0.000511", name="4v"),
        Define("mee", "(Electron_4v[0]+Electron_4v[1]).M()"),
    ],
)
