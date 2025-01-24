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
from utils.cli_utils import load_module, parse_function
from utils.log_utils import write_log, trace_calls, print_configs, print_dataset, print_and_parse_flow, print_mcc, print_flow, print_yields, print_snapshot

app = typer.Typer(pretty_exceptions_show_locals=False, rich_markup_mode="rich", add_completion=False)
console = Console(record=True)

@app.command()
def run_analysis(
    #! Configs
    cfg      : Annotated[str , typer.Option("-c", "--cfg", help="The name of the cfg file that contains the [bold red]era_paths_Data, era_paths_MC, PFs and PMCs[/bold red]", rich_help_panel="Configs")],
    eras     : Annotated[str , typer.Option("-e", "--eras", help="Eras to run (comma separated)", rich_help_panel="Configs")],
    outfolder: Annotated[str, typer.Option("-o", "--outfolder", help="The name of the output folder", rich_help_panel="Configs")],
    flow     : str  = typer.Option(None, "-f", "--flow", help="The name of the flow file that contains the [bold red]flow[/bold red] object. Multiple flow at once can be runned", rich_help_panel="Configs"),
    plots    : str  = typer.Option(None, "-p", "--plots", help="The name of the plots file that contains the [bold red]plots[/bold red] list", rich_help_panel="Configs"),
    data     : str  = typer.Option(None, "-d", "--data", help="The name of the data file that contains the [bold red]DataDict[/bold red]", rich_help_panel="Configs"),
    mc       : str  = typer.Option(None, "-m", "--mc", help="The name of the mc file that contains the [bold red]all_processes[/bold red] dict", rich_help_panel="Configs"),
    mcc      : str  = typer.Option(None, "-mcc", "--mcc", help="The name of the mcc file that contains the [bold red]mccFlow[/bold red]", rich_help_panel="Configs"),
    noSyst   : bool = typer.Option(False, "--noSyst", help="Disable systematics", rich_help_panel="Configs"),

    #! RDF options
    ncpu     : int  = typer.Option(multiprocessing.cpu_count(), "-j", "--ncpu", help="Number of cores to use", rich_help_panel="RDF Options"),
    verbose  : int  = typer.Option(0, "-v", "--verbose", help="Enable RDF verbosity (1 info, 2 debug + 18)", rich_help_panel="RDF Options"),
    nocache  : bool = typer.Option(False, "--noCache", help="Disable caching", rich_help_panel="RDF Options"),
    cachepath: str  = typer.Option(None, "--cachepath", help="Path to the cache folder (Default is outfolder/cache)", rich_help_panel="RDF Options"),

    #! Debug options
    nevents : int = typer.Option(-1, "-n", "--nevents", help="Number of events to process for each file. -1 means all events (nevents != -1 will run on single thread) NB! The genEventSumw is not recomputed, is the one of the full sample", rich_help_panel="Debug"),
    disableBreakpoints: bool = typer.Option(False, "--bp", help="Disable breakpoints", rich_help_panel="Debug"),

    #! Plot options
    lumitext     : str         = typer.Option("L = %(lumi).1f fb^{-1} (13.6 TeV)", "--lumitext", help="Text to display in the top right of the plots", rich_help_panel="Plot Options"),
    noRatio      : bool        = typer.Option(False, "--noRatio", help="Disable the ratio plot", rich_help_panel="Plot Options"),
    noStack      : bool        = typer.Option(False, "--noStack", help="Disable stacked histograms", rich_help_panel="Plot Options"),
    maxratiorange: Tuple[float, float] = typer.Option([0, 2], "--maxRatioRange", help="The range of the ratio plot", rich_help_panel="Plot Options"),
    mergeEras    : bool        = typer.Option(False, "--mergeEras", help="Merge the eras in the plots (and datacards)", rich_help_panel="Plot Options"),

    #! Datacard options
    datacards        : bool = typer.Option(False, "--datacards", help="Create datacards", rich_help_panel="Datacard Options"),
    asimov          : str  = typer.Option(None, "--asimov", help="Use an Asimov dataset of the specified kind: including signal ('signal','s','sig','s+b') or background-only ('background','bkg','b','b-only')", rich_help_panel="Datacard Options"),
    autoMCStats     : bool = typer.Option(False, "--autoMCStats", help="Use autoMCStats", rich_help_panel="Datacard Options"),
    autoMCstatsThreshold: int  = typer.Option(10, "--autoMCStatsThreshold", help="Threshold to put on autoMCStats", rich_help_panel="Datacard Options"),
    threshold       : int  = typer.Option(0.0, "--threshold", help="Minimum event yield to consider processes", rich_help_panel="Datacard Options"),
    regularize      : bool = typer.Option(False, "--regularize", help="Regularize templates", rich_help_panel="Datacard Options"),

    #! Snapshot options
    snapshot   : bool = typer.Option(False, "--snapshot", help="Save snapshots in outfolder/snap/{name}_{era}_{flow}.root", rich_help_panel="Snapshot Options"),
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

    if data is None:
        noRatio = True

    #! ---------------------- Debug and verbosity ----------------------- !#
    if disableBreakpoints:
        os.environ["PYTHONBREAKPOINT"] = "0"

    if verbose==1:
        ROOT.Experimental.RLogScopedVerbosity(
            ROOT.Detail.RDF.RDFLogChannel(), ROOT.Experimental.ELogLevel.kInfo
        )
    elif verbose==2:
        ROOT.Experimental.RLogScopedVerbosity(
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
        plots     = parse_function(plots_module, "plots", list, kwargs=plots_kwargs)
    except ValueError:
        plots     = parse_function(plots_module, "plots", dict, kwargs=plots_kwargs)

    #! ---------------------- PRINT CONFIG --------------------------- !#
    print_configs(console, ncpu, nevents, outfolder, nocache, cachepath, datacards, snapshot, eras, era_paths_Data, era_paths_MC, PFs, PMCs)

    #! ---------------------- DATASET BUILDING ----------------------- !#
    AddData(DataDict, era_paths=era_paths_Data, friends=PFs, mccFlow=mccFlow, eras = eras)
    AddMC(all_processes, era_paths=era_paths_MC, friends=PMCs, mccFlow=mccFlow, eras = eras)
    print_dataset(console, processtable, datatable, MCtable, eras)

    #! -------------- Print flows table and parse flows -------------------- !#
    flow_list = print_and_parse_flow(console, flow)

    #If plots is a single list, make a list of list to make the same plots at each plotting step
    if plots and isinstance(plots, list) and not isinstance(plots[0], list):
        plots = [plots]*len(flow_list)
    if plots and isinstance(plots, list):
        assert len(plots) == len(flow_list), "The number of plots (list) should be the same as the number of flows"

    #! ---------------------- Print MCCs -------------------------- !#
    print_mcc(console, mccFlow)

    #! ---------------------- Create processor -------------------------- !#
    if nocache is False and cachepath is None:
        os.makedirs(os.path.join(outfolder, "cache"), exist_ok=True)
        cache = SimpleCache(os.path.join(outfolder, "cache"))
    elif nocache is False:
        cache = SimpleCache(cachepath)
    else:
        cachepath = -1
        cache = None
    maker = Processor(cache=cache)

    #! ---------------------- PRINT THE FLOW ----------------------- !#
    print_flow(console, flow_list[-1])

    #! ---------------------- LOOP ON FLOWS -------------------------- !#
    for _i, flow in enumerate(flow_list):

        if nevents != -1:
            flow.prepend(Range(nevents))

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
        pprint(f"[bold red]---------------------- Booking flow {flow.name}----------------------[/bold red]")
        maker.bookCutFlow(all_data, lumi, flow, eras=eras)

        if plots:
            if isinstance(plots, dict):
                plot = [*plots.get(flow.name.split("_")[-1], []), *plots.get("main", [])]
            else:
                plot = plots[_i]
            maker.book(all_data, lumi, flow, plot, eras=eras, withUncertainties=True)

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
                maker.book(snap_list, lumi, flow, Snapshot(outfolder + "/snap/{name}_{era}_{flow}.root".replace("{flow}", flow.name), columnSel=columnSel.split(",") if columnSel is not None else None, columnVeto=columnVeto.split(",") if columnVeto is not None else None, compression=None), eras = eras)

    #!---------------------- PRINT Plots ---------------------- !#
    pprint("[bold red]---------------------- RUNNING ----------------------[/bold red]")
    if plots:
        plotter = maker.runPlots(mergeEras=mergeEras)
        PlotSetPrinter(
            topRightText=lumitext, stack=not noStack, maxRatioRange=maxratiorange, showRatio=not noRatio, noStackSignals=True, showErrors=True
        ).printSet(plotter, outfolder + "/flow_{flow}/")

    yields = maker.runYields(mergeEras=True)
    #!---------------------- PRINT YIELDS ---------------------- !#
    console.print("[bold red]###################################################### YIELDS ######################################################[/bold red]")
    print_yields(yields, all_data, flow_list, outfolder, console=console)
    write_log(outfolder, command, cachepath)
    for flow in flow_list:
        os.system(fr'grep -Fxqs "python {command.replace(f" --cachepath {cachepath}", "")}" {os.path.join(outfolder, f"flow_{flow.name}/command.sh")} || echo "python {command.replace(f" --cachepath {cachepath}", "")}" >> {os.path.join(outfolder, f"flow_{flow.name}/command.sh")}')

    #!------------------- CREATE DATACARDS ---------------------- !#
    if datacards:
        pprint("[bold red]---------------------- Saving datacards ----------------------[/bold red]")
        if plots is None:
            raise ValueError("You need to provide the plots file to create the datacards")
        cardMaker = DatacardWriter(regularize=regularize, autoMCStats=autoMCStats, autoMCStatsThreshold=autoMCstatsThreshold, threshold=threshold, asimov=asimov)
        card_path = outfolder+"/cards/{name}_{era}_{flow}.txt"
        if mergeEras:
            card_path = card_path.replace("{era}", "allEras")
        cardMaker.makeCards(plotter, MultiKey(), card_path)
        os.system(f"cp $CMGRDF/externals/index.php {outfolder}/cards/index.php")

    #!------------------- SAVE SNAPSHOT ---------------------- !#
    if snapshot:
        report = maker.runSnapshots()
        print_snapshot(console, report, columnSel, columnVeto, MCpattern, flowPattern)
        os.system(f"cp $CMGRDF/externals/index.php {outfolder}/snap/index.php")

    sys.settrace(None)
    console.save_text(os.path.join(outfolder, "log/report.txt"))
    for flow in flow_list:
        os.system(f'cp {os.path.join(outfolder, "log/report.txt")} {os.path.join(outfolder, f"flow_{flow.name}/report.txt")}')

if __name__ == "__main__":
    app()
