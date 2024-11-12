import copy
import multiprocessing
import os
import sys

from rich.console import Console
from rich.table import Table
import typer
from typing import Tuple
from typing_extensions import Annotated

import ROOT
from CMGRDF import Processor, PlotSetPrinter, Flow, Range, Cut, SimpleCache, MultiKey
from CMGRDF.cms.eras import lumis as lumi
from CMGRDF.stat import DatacardWriter

from data import AddMC, AddData, all_data, processtable, datatable, MCtable
import cpp_functions
from utils.cli_utils import load_module, parse_function
from utils.log_utils import write_log, print_yields, trace_calls

app = typer.Typer(pretty_exceptions_show_locals=False, rich_markup_mode="rich", add_completion=False)
console = Console(record=True)

@app.command()
def run_analysis(
    #! Configs
    cfg      : Annotated[str , typer.Option("-c", "--cfg", help="The name of the cfg file that contains the [bold red]era_paths_Data, era_paths_MC, PFs and PMCs[/bold red]", rich_help_panel="Configs")],
    eras     : Annotated[str , typer.Option("-e", "--eras", help="Eras to run (comma separated)", rich_help_panel="Configs")],
    plots    : Annotated[str , typer.Option("-p", "--plots", help="The name of the plots file that contains the [bold red]plots[/bold red] list", rich_help_panel="Configs")],
    outfolder: Annotated[str, typer.Option("-o", "--outfolder", help="The name of the output folder", rich_help_panel="Configs")],
    data     : str  = typer.Option(None, "-d", "--data", help="The name of the data file that contains the [bold red]DataDict[/bold red]", rich_help_panel="Configs"),
    mc       : str  = typer.Option(None, "-m", "--mc", help="The name of the mc file that contains the [bold red]all_processes[/bold red] list", rich_help_panel="Configs"),
    flow     : str  = typer.Option(None, "-f", "--flow", help="The name of the flow file that contains the [bold red]flow[/bold red]", rich_help_panel="Configs"),
    mcc      : str  = typer.Option(None, "-mcc", "--mcc", help="The name of the mcc file that contains the [bold red]mccFlow[/bold red]", rich_help_panel="Configs"),
    noSyst   : bool = typer.Option(False, "--noSyst", help="Disable systematics", rich_help_panel="Configs"),

    #! RDF options
    ncpu     : int  = typer.Option(multiprocessing.cpu_count(), "-j", "--ncpu", help="Number of cores to use", rich_help_panel="RDF Options"),
    verbose  : bool = typer.Option(False, "-v", "--verbose", help="Enable RDF verbosity", rich_help_panel="RDF Options"),
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
    asimov          : str  = typer.Option(None, "--asimov", help="Use an Asimov dataset of the specified kind: including signal ('signal','s','sig','s+b') or background-only ('background','bkg','b','b-only')", rich_help_panel="Datacard Options"),
    autoMCStats     : bool = typer.Option(False, "--autoMCStats", help="Use autoMCStats", rich_help_panel="Datacard Options"),
    autoMCstatsThreshold: int  = typer.Option(10, "--autoMCStatsThreshold", help="Threshold to put on autoMCStats", rich_help_panel="Datacard Options"),
    threshold       : int  = typer.Option(0.0, "--threshold", help="Minimum event yield to consider processes", rich_help_panel="Datacard Options"),
    regularize      : bool = typer.Option(False, "--regularize", help="Regularize templates", rich_help_panel="Datacard Options"),
):
    """
    Command line to run the analysis.

    All the options in configs should be path to the python files that contain the objects specifien in the help message or a function that returns the object.

    In case of the function, the arguments should be passed after a colon ":" separated by commas ",".
    e.g. python run_analysis.py --cfg path/to/cfg.py:arg1=1,arg2=2

    The functions should have just keyword arguments.
    """

    sys.settrace(trace_calls)
    command = " ".join(sys.argv)
    #! ------------------------- Sanity checks -------------------------- !#
    if data is None and mc is None:
        raise typer.BadParameter("You must provide at least one of the data or mc file")

    #! ---------------------- Debug and verbosity ----------------------- !#
    if disableBreakpoints:
        os.environ["PYTHONBREAKPOINT"] = "0"

    if verbose:
        verbosity = ROOT.Experimental.RLogScopedVerbosity(
            ROOT.Detail.RDF.RDFLogChannel(), ROOT.Experimental.ELogLevel.kInfo
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
    flow_module , flow_kwargs  = load_module(flow)

    era_paths_Data = parse_function(cfg_module, "era_paths_Data", dict)
    era_paths_MC   = parse_function(cfg_module, "era_paths_MC", dict)
    PFs            = parse_function(cfg_module, "PFs", list)
    PMCs           = parse_function(cfg_module, "PMCs", list)

    DataDict      = parse_function(data_module, "DataDict", dict, kwargs=data_kwargs)
    all_processes = parse_function(mc_module, "all_processes", list, kwargs=mc_kwargs)
    mccFlow       = parse_function(mcc_module, "mccFlow", Flow, kwargs=mcc_kwargs)
    flow          = parse_function(flow_module, "flow", Flow, kwargs=flow_kwargs)
    plots         = parse_function(plots_module, "plots", list, kwargs=plots_kwargs)

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
            if len(eras)>1:
                flow.steps[idx:idx+1]=new_steps
            else:
                flow.steps[idx]=new_steps[0]

    #! ---------------------- PRINT CONFIG --------------------------- !#
    print()
    config_table = Table(title="Configurations", show_header=True, header_style="bold black")
    config_table.add_column("Key", style="bold red")
    config_table.add_column("Value")
    config_table.add_row("ncpu", str(ncpu))
    config_table.add_row("nevents", str(nevents))
    config_table.add_row("outfolder", outfolder)
    config_table.add_row("Cache", str(not nocache))
    if nocache is False:
        config_table.add_row(
            "Cache Path", str(cachepath) if cachepath is not None else os.path.join(outfolder, "cache")
        )

    config_table.add_row("Eras", str(eras))
    config_table.add_row("Data friends", str(PFs))
    config_table.add_row("MC friends", str(PMCs))

    console.print(config_table)
    console.print("")
    for era in eras:
        console.print(f"Era: {era}")
        console.print(f"\tData path: {os.path.join(era_paths_Data[era][0], era_paths_Data[era][1])}")
        console.print(f"\tMC path: {os.path.join(era_paths_MC[era][0], era_paths_MC[era][1])}")
        console.print(f"\tData friend path: {os.path.join(era_paths_Data[era][0], era_paths_Data[era][2])}")
        console.print(f"\tMC friend path: {os.path.join(era_paths_MC[era][0], era_paths_MC[era][2])}")
    console.print("")

    #! ---------------------- DATASET BUILDING ----------------------- !#
    AddData(DataDict, era_paths=era_paths_Data, friends=PFs, mccFlow=mccFlow)
    AddMC(all_processes, era_paths=era_paths_MC, friends=PMCs, mccFlow=mccFlow)
    console.print("[bold red]---------------------- DATASETS ----------------------[/bold red]")
    console.print(f"Running eras: {eras}")
    console.print(processtable)
    console.print(datatable)
    console.print(MCtable)

    #! ---------------------- PRINT THE FLOW ----------------------- !#
    console.print("[bold red]---------------------- MCC ----------------------[/bold red]")
    console.print(mccFlow.__str__().replace("\033[1m", "").replace("\033[0m", ""))
    console.print("[bold red]--------------------- FLOW ----------------------[/bold red]")
    console.print(flow.__str__().replace("\033[1m", "").replace("\033[0m", ""))

    #! ---------------------- RUN THE ANALYSIS ----------------------- !#
    console.print("[bold red]---------------------- RUNNING ----------------------[/bold red]")
    if nocache is False and cachepath is None:
        os.makedirs(os.path.join(outfolder, "cache"), exist_ok=True)
        cache = SimpleCache(os.path.join(outfolder, "cache"))
    elif nocache is False:
        cache = SimpleCache(cachepath)
    else:
        cachepath = -1
        cache = None
    maker = Processor(cache=cache)
    maker.bookCutFlow(all_data, lumi, flow, eras=eras)
    maker.book(all_data, lumi, flow, plots, eras=eras, withUncertainties=True)
    plotter = maker.runPlots(mergeEras=mergeEras)
    PlotSetPrinter(
        topRightText=lumitext, stack=not noStack, maxRatioRange=maxratiorange, showRatio=not noRatio, noStackSignals=True, showErrors=True
    ).printSet(plotter, outfolder)

    yields = maker.runYields(mergeEras=True)

    #! ---------------------- PRINT YIELDS ---------------------- !#
    print_yields(yields, all_data, flow, console=console)
    sys.settrace(None)
    write_log(outfolder, command, cachepath)
    console.save_text(os.path.join(outfolder, "log/report.txt"))

    cardMaker = DatacardWriter(regularize=regularize, autoMCStats=autoMCStats, autoMCStatsThreshold=autoMCstatsThreshold, threshold=threshold, asimov=asimov)
    cardMaker.makeCards(plotter, MultiKey(), outfolder+"/cards/{name}_{flow}_{era}.txt")


if __name__ == "__main__":
    app()
