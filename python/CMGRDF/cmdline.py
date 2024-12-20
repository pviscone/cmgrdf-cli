from typing import Any, Optional
import argparse
import ROOT  # type: ignore
from CMGRDF.cache import SimpleCache
from CMGRDF.data import Source
from CMGRDF.processor import Processor


def processorFromCommandLineArgs(parser : Optional[argparse.ArgumentParser] = None) -> Processor:

    parser = parser if parser is not None else argparse.ArgumentParser()
    parser.add_argument("--mode", help="how to run", default="local", choices=("local", "dask"))
    parser.add_argument("--dask", help="shortcut for --mode dask", dest="mode", action="store_const", const="dask")
    parser.add_argument("-u", "--with-systematics", "--syst", help="enable systematics by default", dest="withSystematics", action="store_const", const=True, default=None)
    parser.add_argument("--stat", "--without-systematics,", help="disabqle systematics by default", dest="withSystematics", action="store_const", const=False, default=None)
    parser.add_argument("-f", "--flush-cache", dest="flushCache", help="flush the cache at the start of the job. Use it once to flush just the plot cache, twice (-ff) to fush also the sums cache", action='count', default=0)
    parser.add_argument("-n", "--nocache", help="skip cache", action="store_true")
    parser.add_argument("-c", "--cluster", help="cluster url / connection (needed if dask is specified)")
    parser.add_argument("-j", "--njobs", type=int, help="number of threads or processes")
    parser.add_argument("-v", "--verbose", action='count', default=0)
    parser.add_argument("-b", "--batch", help="batch mode (don't show progress bars)", default=False, action="store_true")
    args = parser.parse_args()
    executor : Optional[tuple[str, Any]] = None
    if args.mode == "local":
        if args.njobs:
            ROOT.EnableImplicitMT(args.njobs if args.njobs > 0 else 0)
    elif args.mode == "dask":
        Source.useDefinePerSample = False
        from dask.distributed import Client  # type: ignore
        if args.cluster:
            client = Client(args.cluster)
        else:
            print(f"Spawning local cluster with {args.njobs if args.njobs else 'default number'} nodes")
            from dask.distributed import LocalCluster  # type: ignore
            cluster = LocalCluster(n_workers=args.njobs, threads_per_worker=1, processes=True)
            client = Client(cluster)
        faulthandler = "import faulthandler\nfaulthandler.enable()"
        client.run(exec, faulthandler)
        client.run_on_scheduler(exec, faulthandler)
        if args.cluster and args.njobs:
            client.run(exec, f"import  ROOT\nROOT.EnableImplicitMT({args.njobs})")
        executor = (args.mode, client)
    cache = None if args.nocache else SimpleCache(flush=args.flushCache)
    maker = Processor(cache=cache, executor=executor, withUncertainties=args.withSystematics)
    maker.commandlineArgs = args  # type: ignore # in case they're used downstream
    if args.verbose:
        level = [ROOT.Experimental.ELogLevel.kInfo, ROOT.Experimental.ELogLevel.kDebug, ROOT.Experimental.ELogLevel.kDebug + 20][min(args.verbose, 2)]
        maker._rdfVerbosity = ROOT.Experimental.RLogScopedVerbosity(ROOT.Detail.RDF.RDFLogChannel(), level)  # type: ignore
    if args.batch:
        from CMGRDF.data import ProgressBar
        ProgressBar.Disable()
    return maker
