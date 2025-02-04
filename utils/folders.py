class Folders:
    def __init__(self):
        self.cache = "zcache"
        self.log = "zlog"
        self.snap_path = "zsnap"
        self.cards_path = "zcards"
        self.plots = ""
        self.snap = ""
        self.cards = ""

    def init(self, mergeEras=False):
        if not mergeEras:
            self.plots = "{era}/{flow}"
            self.snap = self.snap_path+"/{era}/{flow}/{name}.root"
            self.cards = self.cards_path+"/{era}/{flow}/{name}.txt"
        else:
            self.plots = "{flow}"
            self.snap = self.snap_path+"/{flow}/{name}.root"
            self.cards = self.cards_path+"/{flow}/{name}.txt"

def create_folders():
    return Folders()

folders = create_folders()