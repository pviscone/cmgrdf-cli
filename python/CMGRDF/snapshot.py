import json
import os
from typing import Union

import ROOT
from CMGRDF.flow import Target
from CMGRDF.utils import recursiveHash, selectColumns


class Snapshot(Target):
    """Makes a snapshot into a new ROOT file, specifying a list of columns
       to select and optionally to veto (list of regexps).
       The special '#old', '#new' can be used to match all columns existing in the
       input file, and all the columns added in the RDF processing."""

    def __init__(self,
                 filename : str,
                 columnSel : 'Union[str, list[str], None]' = None,
                 columnVeto : 'Union[str, list[str], None]' = None,
                 compression : 'tuple[str, int]' = ("ZLIB", 1),
                 treeName="Events"):
        super(Snapshot, self).__init__(os.path.basename(filename).replace(".root", ""))
        self.filename = filename
        self.treeName = treeName
        self.columnSel = ([] if columnSel is None else ([columnSel] if isinstance(columnSel, str) else list(columnSel)))
        self.columnVeto = ([] if columnVeto is None else ([columnVeto] if isinstance(columnVeto, str) else list(columnVeto)))
        self.compression = ("ZLIB", 0) if compression is None else compression
        self._hash = recursiveHash(filename, treeName, columnSel, columnVeto, compression)
        self.hadd = False

    def fromCache(self, sample, era, k3, verbose=False):
        outname = self.filename.format(era=era, name=sample.name, suffix=sample.suffix)
        sourceid, branchid, selfid = k3
        if os.path.exists(outname):
            metafile = outname.replace(".root", "") + ".meta.json"
            if os.path.exists(metafile) and os.path.getmtime(metafile) > os.path.getmtime(outname):
                try:
                    meta = json.load(open(metafile))
                    if meta['sourceid'] == sourceid:
                        if meta['branchid'] == branchid:
                            if meta['id'] == selfid:
                                if verbose:
                                    print(f"Not remaking snapshot {outname} for {sample.name}")
                                ret = ROOT.RDataFrame(self.treeName, outname)
                                ret.fname = outname
                                ret.entries = meta['entries']
                                ret.size = meta['size']
                                ret.sample = sample.name
                                ret.era = era
                                return ret
                except BaseException:  # noqa: B036
                    # if the cache is not readable or corrupted we just ignore it
                    pass
        return None

    def toCache(self, snapshot, k3, verbose=False):
        sourceid, branchid, selfid = k3
        metafile = snapshot.fname.replace(".root", "") + ".meta.json"
        meta = dict(sourceid=sourceid, branchid=branchid, id=selfid,
                    entries=snapshot.entries, size=snapshot.size)
        try:
            if verbose:
                print(f"Saving metadata in {metafile} for {k3}")
            json.dump(meta, open(metafile, 'w'))
        except BaseException as e:  # noqa: B036
            # don't throw if we fail to write the metadata
            print(f"Error when saiving metadata in {metafile} for {k3}: {e}")
            pass

    def attach(self, rdf, sample, era):
        if ROOT.gROOT.GetVersionInt() >= 63400:
            comprAlgo = getattr(ROOT.RCompressionSetting.EAlgorithm, "k" + self.compression[0].upper())
        else:
            comprAlgo = getattr(ROOT, "k" + self.compression[0].upper())
        opts = ROOT.RDF.RSnapshotOptions("RECREATE", comprAlgo, self.compression[1], 0, 99, True)
        columns = selectColumns(rdf, self.columnSel, self.columnVeto)
        outname = self.filename.format(era=era, name=sample.name, suffix=sample.suffix)
        os.makedirs(os.path.dirname(outname), exist_ok=True)
        future = rdf.Snapshot(self.treeName, outname, columns, opts)
        future._entries = rdf.Count()
        future._fname = outname
        return future

    def finishFuture(self, future, sample, era):
        """Receive a future for the nominal value, unwraps it and return the value.
           By defalut it just calls `finish(future.GetValue(), sample, era)`"""
        rdf = future.GetValue()
        rdf.fname = future._fname
        rdf.entries = future._entries.GetValue()
        if "DistRDF" in rdf.__module__:
            rdf.fnames = rdf._headnode.inputfiles
            rdf.size = sum(os.path.getsize(f) for f in rdf.fnames)
        else:
            rdf.size = os.path.getsize(future._fname)
        rdf.sample = sample.name
        rdf.era = era
        return rdf

    def bookVariations(self, future):
        return None

    def finishVarFuture(self, varfuture, sample, era):
        return None

    def __hash__(self):
        return hash(self._hash)

    def longId(self):
        return "Snapshot-" + self._hash


def mergeSnapshot(snap, verbose=False):
    import subprocess
    try:
        out = subprocess.check_output(["hadd", "-ff", snap.fname] + snap.fnames, stderr=subprocess.STDOUT, encoding="utf-8")
        outsize = os.path.getsize(snap.fname)
        safetyFactor = 0.5 if snap.entries > 1000 or outsize > 1024 * 1024 else 0.2
        if outsize > 1024 and outsize > safetyFactor * snap.size:  # safety margin if it recompresses better
            for f in snap.fnames:
                os.unlink(f)
            #print(f"merged {snap.fnames} (total: {snap.size} bytes) into {snap.fname} ({outsize} bytes)")
        else:
            print(f"WARNING: merged {snap.fnames} (total: {snap.size} bytes) into {snap.fname} ({outsize} bytes): BAD SIZE")
        if verbose:
            quoted_output = out.replace('\n', '\n>> ')
            print(f"merged {snap.fnames} (total: {snap.size} bytes) into {snap.fname} ({outsize} bytes)\n>> {quoted_output}\n")
    except subprocess.CalledProcessError as e:
        quoted_output = e.stdout.replace('\n', '\n>> ')
        print(f"ERROR when merging {snap.fnames} into {snap.fname}: {e}\n>> {quoted_output}\n")
