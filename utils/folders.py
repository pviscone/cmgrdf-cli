class Folders:
    def __init__(self):
        self.cache = "zzcache"
        self.log = "zlog"

        self.snap_path = "zsnap/era{era}/{flow}"
        self.snap = self.snap_path+"/{name}.root" #! MERGE ERAS FOR SNAPSHOTS MAKE NO SENSE

        self.cards_path = "zcards"
        self.cards = self.cards_path+"/{name}_{era}_{flow}.txt"

        self.tables_path = ""
        self.tables = ""

    def init(self, mergeEras=False, mergeErasYields=False):
        if not mergeEras:
            self.plots_path = "era{era}/{flow}"
        else:
            self.plots_path = "{flow}"

        if not mergeErasYields:
            self.tables_path = "ztables/era{era}/{flow}"
        else:
            self.tables_path = "ztables/{flow}"

        self.tables = self.tables_path+"/{name}.txt"

folders = Folders()