import copy
import multiprocessing
import os
import re
import sys

from rich.console import Console
from rich import print as pprint
import typer
from typing import Tuple
from typing_extensions import Annotated

import ROOT
from CMGRDF import Processor, PlotSetPrinter, Flow, Range, SimpleCache, MultiKey, Snapshot
from CMGRDF.cms.eras import lumis as lumi
from CMGRDF.stat import DatacardWriter

from data import AddMC, AddData, all_data, processtable, datatable, MCtable
from flows.SFs import BranchCorrection
import cpp_functions
from utils.cli_utils import load_module, parse_function, copy_file_to_subdirectories, center_header
from utils.log_utils import write_log, trace_calls, print_configs, print_dataset, print_mcc, print_flow, print_yields, print_snapshot, accessed_files
from utils.flow_utils import parse_flows, clean_commons, disable_plotflag
from utils.plot_utils import DrawPyPlots
from utils.folders import folders

app = typer.Typer(pretty_exceptions_show_locals=False, rich_markup_mode="rich", add_completion=False)
console = Console(record=True)

@app.command()
def run_analysis(
    #! Configs
    cfg      : Annotated[str , typer.Option("-c", "--cfg", help="The name of the cfg file that contains the [bold red]era_paths_Data, era_paths_MC, PFs and PMCs[/bold red]", rich_help_panel="Configs")],
    eras     : Annotated[str , typer.Option("-e", "--eras", help="Eras to run (comma separated)", rich_help_panel="Configs")],
    outfolder: Annotated[str, typer.Option("-o", "--outfolder", help="The name of the output folder", rich_help_panel="Configs")],
    flow     : str  = typer.Option(None, "-f", "--flow", help="The name of the flow file that contains the [bold red]flow[/bold red] or [bold red]Tree[/bold red] object.", rich_help_panel="Configs"),
    plots    : str  = typer.Option(None, "-p", "--plots", help="The name of the plots file that contains the [bold red]plots[/bold red] dict/list", rich_help_panel="Configs"),
    data     : str  = typer.Option(None, "-d", "--data", help="The name of the data file that contains the [bold red]DataDict[/bold red]", rich_help_panel="Configs"),
    mc       : str  = typer.Option(None, "-m", "--mc", help="The name of the mc file that contains the [bold red]all_processes[/bold red] dict", rich_help_panel="Configs"),
    mcc      : str  = typer.Option(None, "-mcc", "--mcc", help="The name of the mcc file that contains the [bold red]mccFlow[/bold red]", rich_help_panel="Configs"),
    processPattern: str = typer.Option(None, "--processPattern", help="Regex patterns to select processes mathcing the process name", rich_help_panel="Configs"),
    noSyst   : bool = typer.Option(False, "--noSyst", help="Disable systematics", rich_help_panel="Configs"),
    noXsec   : bool = typer.Option(False, "--noXsec", help="Ignore all the cross-sections and assign unitary weight to all the events", rich_help_panel="Configs"),
    plotFormats: str = typer.Option("root", "--plotFormats", help="Formats to save the plots. Available root,txt (comma separated)", rich_help_panel="Configs"),

    #! RDF options
    ncpu     : int  = typer.Option(multiprocessing.cpu_count(), "-j", "--ncpu", help="Number of cores to use", rich_help_panel="RDF Options"),
    verbose  : int  = typer.Option(0, "-v", "--verbose", help="Enable RDF verbosity (1 info, 2 debug + 18)", rich_help_panel="RDF Options"),
    cache    : bool = typer.Option(False, "--cache", help="Enable caching", rich_help_panel="RDF Options"),
    cachepath: str  = typer.Option(None, "--cachepath", help=f"Path to the cache folder (Default is outfolder/{folders.cache})", rich_help_panel="RDF Options"),

    #! Debug options
    nevents : int = typer.Option(-1, "-n", "--nevents", help="Number of events to process for each file. -1 means all events (nevents != -1 will run on single thread) NB! The genEventSumw is not recomputed, is the one of the full sample", rich_help_panel="Debug"),
    disableBreakpoints: bool = typer.Option(False, "--bp", help="Disable breakpoints", rich_help_panel="Debug"),

    #! Flow options
    disableRegions: str  = typer.Option("", "--disableRegions", help="Regions to disable (regex patterns comma separated). Work on flow Trees", rich_help_panel="Flow Options"),
    enableRegions : str  = typer.Option("", "--enableRegions", help="Regions to enable (regex patterns comma separated). Work on flow Trees", rich_help_panel="Flow Options"),
    noPlotsteps   : bool = typer.Option(False, "--noPlotsteps", help="Do not plot the steps in the middle of the flow", rich_help_panel="Flow Options"),

    #! Plot options
    noPyplots    : bool        = typer.Option(False, "--noPyplots", help="Do not plot figures, just save THx root files", rich_help_panel="Plot Options"),
    lumitext     : str         = typer.Option("{lumi:.1f} $fb^{{-1}}$ (13.6 TeV)", "--lumitext", help="Text to display in the top right of the plots", rich_help_panel="Plot Options"),
    cmstext      : str         = typer.Option("Preliminary", "--cmstext", help="Text to display in the top left of the plots", rich_help_panel="Plot Options"),
    noRatio      : bool        = typer.Option(False, "--noRatio", help="Enable ratio plot (data/bkg). need stacks and data", rich_help_panel="Plot Options"),
    ratiotype    : str         = typer.Option("split_ratio", "--ratiotype", help="Type of ratio plot (ratio, split_ratio, pull, efficiency, asymmetry, difference, relative_difference)", rich_help_panel="Plot Options"),
    ratiorange   : Tuple[float, float] = typer.Option(None, "--ratioRange", help="The range of the ratio plot", rich_help_panel="Plot Options"),
    noStack      : bool        = typer.Option(False, "--noStack", help="Disable stacked histograms for backgrounds", rich_help_panel="Plot Options"),
    stackSignal  : bool        = typer.Option(False, "--stackSignal", help="Add signal processes to stacked histograms together with the bkg", rich_help_panel="Plot Options"),
    mergeEras    : bool        = typer.Option(False, "--mergeEras", help="Merge the eras in the plots (and datacards)", rich_help_panel="Plot Options"),
    grid         : bool        = typer.Option(False, "--grid", help="Enable grid", rich_help_panel="Plot Options"),

    #! Yields options
    noYields       : bool = typer.Option(False, "--noYields", help="Disable the yields", rich_help_panel="Yields Options"),
    mergeErasYields: bool = typer.Option(False, "--mergeErasYields", help="Merge the eras in the yields", rich_help_panel="Yields Options"),

    #! Datacard options #
    datacards       : bool = typer.Option(False, "--datacards", help="Create datacards", rich_help_panel="Datacard Options"),
    asimov          : str  = typer.Option(None, "--asimov", help="Use an Asimov dataset of the specified kind: including signal ('signal','s','sig','s+b') or background-only ('background','bkg','b','b-only')", rich_help_panel="Datacard Options"),
    autoMCStats     : bool = typer.Option(False, "--autoMCStats", help="Use autoMCStats", rich_help_panel="Datacard Options"),
    autoMCstatsThreshold: int  = typer.Option(10, "--autoMCStatsThreshold", help="Threshold to put on autoMCStats", rich_help_panel="Datacard Options"),
    threshold       : int  = typer.Option(0.0, "--threshold", help="Minimum event yield to consider processes", rich_help_panel="Datacard Options"),
    regularize      : bool = typer.Option(False, "--regularize", help="Regularize templates", rich_help_panel="Datacard Options"),

    #! Snapshot options
    snapshot   : bool = typer.Option(False, "--snapshot", help=f"Save snapshots in outfolder/{folders.snap}", rich_help_panel="Snapshot Options"),
    columnSel  : str = typer.Option(None, "--columnSel", help="Columns to select (regex pattern). Comma separated", rich_help_panel="Snapshot Options"),
    columnVeto : str = typer.Option(None, "--columnVeto", help="Columns to veto (regex pattern). Comma separated", rich_help_panel="Snapshot Options"),
    noMC       : bool = typer.Option(False, "--noMC", help="Do not snapshot MC samples", rich_help_panel="Snapshot Options"),
    noData     : bool = typer.Option(False, "--noData", help="Do not snapshot data samples", rich_help_panel="Snapshot Options"),
    MCpattern  : str = typer.Option(None, "--MCpattern", help="Regex patterns to select MC samples mathcing the process name (comma separated)", rich_help_panel="Snapshot Options"),
    flowPattern: str = typer.Option(None, "--flowPattern", help="Regex patterns to select flows mathcing the flow name (comma separated)", rich_help_panel="Snapshot Options"),
):
    """
    Command line to run the analysis.

    All the options in configs should be path to the python files that contain the objects specifien in the help message or a function that returns the object.

    In case of the function, the arguments should be passed after a colon ":" separated by commas ",".
    e.g. python run_analysis.py --cfg path/to/cfg.py:arg1=1,arg2=2

    The functions should have just keyword arguments.
    """

    sys.settrace(trace_calls)
    command = " ".join(sys.argv).replace('"', r'\\\"')

    #! ------------------------- Sanity checks -------------------------- !#
    if data is None and mc is None:
        raise typer.BadParameter("You must provide at least one of the data or mc file")

    if data is None or noStack:
        noRatio = True

    if noXsec and lumitext=="{lumi:.1f} $fb^{{-1}}$ (13.6 TeV)":
        lumitext = "(13.6 TeV)"

    assert ratiotype in ["ratio", "split_ratio", "pull", "efficiency", "asymmetry", "difference", "relative_difference"], "ratiotype should be one of 'ratio', 'split_ratio', 'pull', 'efficiency', 'asymmetry', 'difference', 'relative_difference'"

    if datacards:
        assert plots is not None, "You need to provide the plots file to create the datacards"

    if columnVeto:
        columnVeto += ",mcSampleWeight"
    else:
        columnVeto = "mcSampleWeight"

    nocache = not cache

    #! ------------------------- Set Folders -------------------------- !#
    folders.init(mergeEras=mergeEras, mergeErasYields=mergeErasYields)
    folders.outfolder = os.path.abspath(outfolder)
    for attr in dir(folders):
        if not attr.startswith("__") and attr != "init":
            setattr(folders, attr, os.path.join(folders.outfolder, getattr(folders, attr)))

    os.makedirs(folders.log, exist_ok=True)

    #! ---------------------- Debug and verbosity ----------------------- !#
    if disableBreakpoints:
        os.environ["PYTHONBREAKPOINT"] = "0"

    #Do not remove verbosity. If RLogScopedVerbosity is not saved in a variable, it will be deleted and the verbosity will not be set
    if verbose==1:
        verbosity=ROOT.Experimental.RLogScopedVerbosity(
            ROOT.Detail.RDF.RDFLogChannel(), ROOT.Experimental.ELogLevel.kInfo
        )
    elif verbose==2:
        verbosity=ROOT.Experimental.RLogScopedVerbosity(
            ROOT.Detail.RDF.RDFLogChannel(), ROOT.Experimental.ELogLevel.kDebug+18
        )

    #! -------------------------- RDF CONFIG ---------------------------- !#
    if ncpu > 1 and nevents == -1:
        ROOT.EnableImplicitMT(ncpu)

    cpp_functions.load()
    #! ----------------------== Module imports -------------------------- !#
    eras        = eras.split(",")
    cfg_module  , _          = load_module(cfg)
    plots_module, plots_kwargs = load_module(plots)
    data_module , data_kwargs  = load_module(data)
    mc_module   , mc_kwargs    = load_module(mc)
    mcc_module  , mcc_kwargs   = load_module(mcc)

    era_paths_Data = parse_function(cfg_module, "era_paths_Data", dict)
    era_paths_MC   = parse_function(cfg_module, "era_paths_MC", dict)
    PFs            = parse_function(cfg_module, "PFs", list)
    PMCs           = parse_function(cfg_module, "PMCs", list)

    DataDict      = parse_function(data_module, "DataDict", dict, kwargs=data_kwargs)
    all_processes = parse_function(mc_module, "all_processes", dict, kwargs=mc_kwargs)
    mccFlow       = parse_function(mcc_module, "mccFlow", Flow, kwargs=mcc_kwargs)
    try:
        plots     = parse_function(plots_module, "plots", dict, kwargs=plots_kwargs)
    except ValueError:
        plots     = parse_function(plots_module, "plots", list, kwargs=plots_kwargs)
        plots     = {"main" : plots} if plots != [] else {}

    #! ---------------------- PRINT CONFIG --------------------------- !#
    print_configs(console, ncpu, nevents, nocache, cachepath, datacards, snapshot, eras, era_paths_Data, era_paths_MC, PFs, PMCs)
    os.makedirs(folders.outfolder, exist_ok=True)

    #! ---------------------- DATASET BUILDING ----------------------- !#
    AddData(DataDict, era_paths=era_paths_Data, friends=PFs, mccFlow=mccFlow, eras = eras)
    AddMC(all_processes, era_paths=era_paths_MC, friends=PMCs, mccFlow=mccFlow, eras = eras, noXsec=noXsec, processPattern=processPattern)
    print_dataset(console, processtable, datatable, MCtable, eras)

    #! ---------------------- Print MCCs -------------------------- !#
    print_mcc(console, mccFlow)

    #! ---------------------- Create processor -------------------------- !#
    if nocache is False and cachepath is None:
        os.makedirs(folders.cache, exist_ok=True)
        cache = SimpleCache(folders.cache)
    elif nocache is False:
        cache = SimpleCache(cachepath)
    else:
        cachepath = -1
        cache = None
    maker = Processor(cache=cache)

    #! -------------- Print flows table and parse flows -------------------- !#
    #list of list of flows. [i][j] i is leaf, j is plotstep. bool if tree contains a branch
    region_flows, region_plots, isBranched = parse_flows(console, flow, plots, enable=enableRegions.split(","), disable=disableRegions.split(","), noPlotsteps=noPlotsteps)
    if noPlotsteps:
        region_flows = [[r[-1]] for r in region_flows]
        region_plots = [[p[-1]] for p in region_plots]
        disable_plotflag(region_flows)
    if isBranched and not noPlotsteps:
        region_flows, region_plots = clean_commons(region_flows, region_plots)
    region_plots = [region_plots[idx] for idx in range(len(region_flows)) if region_flows[idx]] #remove plot elements associated to empty flow_list
    region_flows = [flow_list for flow_list in region_flows if flow_list] #remove empty flow_list
    flow_plots = []
    for flow_list, plot_list in zip(region_flows, region_plots):
        #! ---------------------- PRINT THE FLOW ----------------------- !#
        if not re.search("(\d+)common.*", flow_list[-1].name): #Do not print common flows
            print_flow(console, flow_list[-1])

        #! ---------------------- LOOP ON FLOWS -------------------------- !#
        for _i, (flow, plot) in enumerate(zip(flow_list, plot_list)):

            if nevents != -1:
                flow.prepend(Range(int(nevents)))

            #! ------------------ Corrections handling ------------------------ !#
            # Dirty workaround to handle corrections

            for idx, step in enumerate(flow):
                if hasattr(step, "_isCorrection") and step.era is None and hasattr(step, "init"):
                    new_steps = []
                    for era in eras:
                        copy_step = copy.deepcopy(step)
                        if noSyst:
                            copy_step.doSyst  = False
                        new_steps.append(copy_step.init(era=era))
                        new_steps[-1]._init = True
                        new_steps[-1].era   = era
                        new_steps[-1].eras  = [era]
                        new_steps[-1].nuisName = type(step).__name__
                        if isinstance(new_steps[-1], BranchCorrection):
                            new_steps[-1].doSyst = copy_step.doSyst
                    if len(eras)>1:
                        flow.steps[idx:idx+1]=new_steps
                    else:
                        flow.steps[idx]=new_steps[0]

            #! ---------------------- BOOK Plots and cutflow ----------------------- !#
            pprint(f"[bold red]{center_header(f'Booking flow {flow.name}')}[/bold red]")
            maker.bookCutFlow(all_data, lumi, flow, eras=eras)

            if plots:
                maker.book(all_data, lumi, flow, plot, eras=eras, withUncertainties=True)
                flow_plots.append((flow.name, plot))

            #! ---------------------- BOOK SNAPSHOT ----------------------!#
            if snapshot:
                snap_list = []
                for dat in all_data:
                    if dat.isData and noData:
                        continue
                    if not dat.isData and noMC:
                        continue
                    if not dat.isData and MCpattern is not None and not any([bool(re.search(pattern, dat.name)) for pattern in MCpattern.split(",")]):
                        continue
                    snap_list.append(dat)
                if (flowPattern is not None and any([bool(re.search(fpattern, flow.name)) for fpattern in flowPattern.split(",")])) or flowPattern is None:
                    maker.book(snap_list, lumi, flow, Snapshot(folders.snap.replace("{flow}", flow.name), columnSel=columnSel.split(",") if columnSel is not None else None, columnVeto=columnVeto.split(",") if columnVeto is not None else None, compression=None), eras = eras)

    #!---------------------- Save Plots ---------------------- !#
    pprint(f"[bold red]{center_header('RUNNING')}[/bold red]")
    if plots:
        plotter = maker.runPlots(mergeEras=mergeEras)
        PlotSetPrinter(
            stack= not noStack, noStackSignals=not stackSignal, plotFormats=plotFormats,
        ).printSet(plotter, folders.plots_path)

        #!---------------------- Draw Plots ---------------------- !#
        if not noPyplots:
            sys.settrace(None) #to be faster
            plot_lumi = [plotter._items[i][1].lumi for i in range(len(plotter._items))]
            DrawPyPlots(plot_lumi, eras, mergeEras, flow_plots, all_processes, cmstext, lumitext, noStack, not noRatio, ratiorange, ratiotype, grid=grid, ncpu=ncpu, stackSignal=stackSignal)
            accessed_files.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "plot_utils.py"))
            accessed_files.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "plotters.py"))
            sys.settrace(trace_calls)

    #!---------------------- PRINT YIELDS ---------------------- !#
    if not noYields:
        yields = maker.runYields(mergeEras=mergeErasYields)
        console.print(f"[bold red]{center_header('YIELDS', s='#')}[/bold red]")
        for flow_list in region_flows:
            if len(region_flows)>1 and re.search("(\d+)common.*", flow_list[-1].name):
                continue
            print_yields(yields, all_data, [flow_list[-1]], eras, mergeErasYields, console=console)

    #!------------------- CREATE DATACARDS ---------------------- !#
    if datacards:
        pprint(f"[bold red]{center_header('Saving datacards')}[/bold red]")
        cardMaker = DatacardWriter(regularize=regularize, autoMCStats=autoMCStats, autoMCStatsThreshold=autoMCstatsThreshold, threshold=threshold, asimov=asimov)
        cardMaker.makeCards(plotter, MultiKey(), folders.cards)

    #!------------------- SAVE SNAPSHOT ---------------------- !#
    if snapshot:
        report = maker.runSnapshots()
        print_snapshot(console, report, columnSel, columnVeto, MCpattern, flowPattern)

    #!--------------------- SAVE LOGS ---------------------- !#
    write_log(command, cachepath)
    sys.settrace(None)
    console.save_text(os.path.join(folders.log, "report.txt"))
    copy_file_to_subdirectories(os.path.join(os.environ["CMGRDF"], "externals/index.php"), folders.outfolder, ignore=[folders.cache, folders.log])

if __name__ == "__main__":
    app()
