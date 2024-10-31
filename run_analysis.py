import multiprocessing
import os
import sys

from rich import print as pprint
from rich.console import Console
from rich.table import Table
import typer
from typing import Tuple
from typing_extensions import Annotated

import ROOT
from CMGRDF import Processor, PlotSetPrinter, Flow, Range
from CMGRDF.cms.eras import lumis as lumi

from data import AddMC, AddData, all_data
import cpp_functions
from utils.cli_utils import load_module, parse_function
from utils.log_utils import write_log

app = typer.Typer(pretty_exceptions_show_locals=False, rich_markup_mode="rich", add_completion=False)

@app.command()
def run_analysis(
    #! Configs
    cfg      : Annotated[str , typer.Option("-c", "--cfg", help="The name of the cfg file that contains the [bold red]era_paths_Data, era_paths_MC, PFs and PMCs[/bold red]", rich_help_panel="Configs")],
    eras    : Annotated[str , typer.Option("-e", "--eras", help="Eras to run", rich_help_panel="Configs")],
    plots    : Annotated[str , typer.Option("-p", "--plots", help="The name of the plots file that contains the [bold red]plots[/bold red] list", rich_help_panel="Configs")],
    outfolder: Annotated[str, typer.Option("-o", "--outfolder", help="The name of the output folder", rich_help_panel="Configs")],
    data     : str  = typer.Option([None], "-d", "--data", help="The name of the data file that contains the [bold red]DataDict[/bold red]", rich_help_panel="Configs"),
    mc       : str  = typer.Option([None], "-m", "--mc", help="The name of the mc file that contains the [bold red]all_processes[/bold red] list", rich_help_panel="Configs"),
    flow     : str  = typer.Option([None], "-f", "--flow", help="The name of the flow file that contains the [bold red]flow[/bold red]", rich_help_panel="Configs"),
    mcc      : str  = typer.Option([None], "-mcc", "--mcc", help="The name of the mcc file that contains the [bold red]mccFlow[/bold red]", rich_help_panel="Configs"),

    #! RDF options
    ncpu   : int  = typer.Option(multiprocessing.cpu_count(), "-j", "--ncpu", help="Number of cores to use", rich_help_panel="RDF Options"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable RDF verbosity", rich_help_panel="RDF Options"),

    #! Debug options
    nevents: int = typer.Option(-1, "-n", "--nevents", help="Number of events to process. -1 means all events (nevents != -1 will run on single thread)", rich_help_panel="Debug"),
    disableBreakpoints: bool = typer.Option(False, "--bp", help="Disable breakpoints", rich_help_panel="Debug"),

    #! Plot options
    lumitext     : str         = typer.Option("L = %(lumi).1f fb^{-1} (13 TeV)", "--lumitext", help="Text to display in the top right of the plots", rich_help_panel="Plot Options"),
    ratio        : bool        = typer.Option(True, "--NotRatio", help="Disable the ratio plot", rich_help_panel="Plot Options"),
    stack        : bool        = typer.Option(True, "--NotStack", help="Disable stacked histograms", rich_help_panel="Plot Options"),
    maxratiorange: Tuple[float, float] = typer.Option([0, 2], "--maxRatioRange", help="The range of the ratio plot", rich_help_panel="Plot Options"),
):
    """
    Command line to run the analysis.

    All the options in configs should be path to the python files that contain the objects specifien in the help message or a function that returns the object.

    In case of the function, the arguments should be passed after a colon ":" separated by commas ",".
    e.g. python run_analysis.py --cfg path/to/cfg.py:arg1=1,arg2=2

    The functions should have just keyword arguments with type hints.
    """

    command = " ".join(sys.argv)
    #! ------------------------- Sanity checks -------------------------- !#
    if data is None and mc is None:
        raise typer.BadParameter("You must provide at least one of the data or mc file")

    #! ---------------------- Debug and verbosity ----------------------- !#
    if disableBreakpoints:
        os.environ['PYTHONBREAKPOINT'] = '0'

    if verbose:
        verbosity = ROOT.Experimental.RLogScopedVerbosity(
            ROOT.Detail.RDF.RDFLogChannel(), ROOT.Experimental.ELogLevel.kInfo
        )

    #! -------------------------- RDF CONFIG ---------------------------- !#
    if ncpu > 1 and nevents == -1:
        ROOT.EnableImplicitMT(ncpu)

    cpp_functions.load()
    #! ----------------------== Module imports -------------------------- !#
    eras = eras.split(",")
    cfg_module  , _          = load_module(cfg)
    plots_module, plots_args = load_module(plots)
    data_module , data_args  = load_module(data)
    mc_module   , mc_args    = load_module(mc)
    mcc_module  , mcc_args   = load_module(mcc)
    flow_module , flow_args  = load_module(flow)

    era_paths_Data = parse_function(cfg_module, "era_paths_Data", dict)
    era_paths_MC   = parse_function(cfg_module, "era_paths_MC", dict)
    PFs            = parse_function(cfg_module, "PFs", list)
    PMCs           = parse_function(cfg_module, "PMCs", list)

    DataDict      = parse_function(data_module, "DataDict", dict, args=data_args)
    all_processes = parse_function(mc_module, "all_processes", list, args=mc_args)
    mccFlow       = parse_function(mcc_module, "mccFlow", Flow, args=mcc_args)
    flow          = parse_function(flow_module, "flow", Flow, args=flow_args)
    plots         = parse_function(plots_module, "plots", list, args=plots_args)

    if nevents != -1:
        flow.prepend(Range(nevents))

    #! ---------------------- PRINTING --------------------------- !#
    print()
    table = Table(title="Configurations", show_header=True, header_style="bold black")
    table.add_column("Key", style="bold red")
    table.add_column("Value")
    table.add_row("ncpu", str(ncpu))
    table.add_row("nevents", str(nevents))
    console = Console()
    console.print(table)

    pprint("[bold red]---------------------- MCC ----------------------[/bold red]")
    pprint(mccFlow.__str__().replace("\033[1m","").replace("\033[0m",""))
    pprint("[bold red]--------------------- FLOW ----------------------[/bold red]")
    pprint(flow.__str__().replace("\033[1m","").replace("\033[0m",""))

    #! ---------------------- DATASET BUILDING ----------------------- !#
    AddData(DataDict, era_paths=era_paths_Data, friends=PFs, mccFlow=mccFlow)
    AddMC(all_processes, era_paths=era_paths_MC, friends=PMCs, mccFlow=mccFlow)

    #! ---------------------- RUN THE ANALYSIS ----------------------- !#
    maker = Processor().book(all_data, lumi, flow, plots, eras=eras).runPlots()
    printer = PlotSetPrinter(
        topRightText=lumitext, stack=stack, maxRatioRange=maxratiorange, showRatio=ratio
    ).printSet(maker, outfolder)

    #?ADD Report
    #! ---------------------- WRITE COMMAND LOG ---------------------- !#
    write_log(outfolder, command, modules=[cfg_module, plots_module, data_module, mc_module, mcc_module, flow_module])


if __name__ == "__main__":
    app()
