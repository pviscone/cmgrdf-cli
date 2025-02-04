class Folders:
    def __init__(self):
        self.cache = "zzcache"
        self.log = "zlog"
        self.snap_path = "zsnap/era{era}/{flow}"
        self.snap = self.snap_path+"/{name}.root" #! MERGE ERAS FOR SNAPSHOTS MAKE NO SENSE

        self.plots = ""
        self.cards_path = ""
        self.cards = ""
        self.tables_path = ""
        self.tables = ""

    def init(self, mergeEras=False, mergeErasYields=False):
        if not mergeEras:
            self.plots = "era{era}/{flow}"
            self.cards_path = "zcards/era{era}/{flow}"

        else:
            self.plots = "{flow}"
            self.cards_path = "zcards/{flow}"

        self.cards = self.cards_path+"/{name}.txt"

        if not mergeErasYields:
            self.tables_path = "ztables/era{era}/{flow}"
        else:
            self.tables_path = "ztables/{flow}"

        self.tables = self.tables_path+"/{name}.txt"

folders = Folders()