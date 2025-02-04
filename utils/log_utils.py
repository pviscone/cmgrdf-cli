import os

from CMGRDF import Cut, MultiKey
from hist.intervals import ratio_uncertainty
from rich.console import Console
from rich.table import Table

from utils.folders import folders

import __main__

main_dir = os.path.dirname(__main__.__file__)  # Path to dp-ee-main folder
accessed_files = []  # List to store the paths of .py files


# Trace all the imported py files
def trace_calls(frame, event, arg):
    if event != "call":
        return
    filename = frame.f_globals.get("__file__", None)
    if filename and filename.endswith(".py"):
        abs_path = os.path.abspath(filename)
        if (
            abs_path not in accessed_files
            and abs_path.startswith(main_dir)
            and not abs_path.startswith(os.path.join(main_dir, "cmgrdf-prototype"))
        ):
            accessed_files.append(abs_path)
    return trace_calls


def write_log(command, cachepath):
    if cachepath is None:
        cachestring = "--cachepath ../zcache"
    elif isinstance(cachepath, str):
        # Strip cachepath from command
        command = command.replace(f" --cachepath {cachepath}", "")
        # get asbolute path
        cachepath = os.path.abspath(cachepath)
        cachestring = f"--cachepath {cachepath}"
    else:
        cachestring = ""
    # Write the command string to file
    os.makedirs(folders.log, exist_ok=True)
    os.system(
        f"cp {os.path.join(main_dir, 'utils/command_template.sh')} {os.path.join(folders.log, 'command.sh')}"
    )
    os.system(fr'echo "python {command} {cachestring}" >> {os.path.join(folders.log, "command.sh")}')

    # Write cmgrdf commit hash and, eventually, git diff to cmdrdf_commit.txt
    os.system(
        f"cd {os.environ['CMGRDF']} && git describe --match=NeVeRmAtCh --always --abbrev=40 --dirty > {os.path.join(folders.log, 'cmgrdf_commit.txt')}"
    )
    os.system(f"cd {os.environ['CMGRDF']} && git diff >> {os.path.join(folders.log, 'cmgrdf_commit.txt')}")

    # Write dp-ee-main commit hash and, eventually, git diff to dp-ee-main_commit.txt
    os.system(
        f"cd {os.environ['ANALYSIS_DIR']} && git describe --match=NeVeRmAtCh --always --abbrev=40 --dirty > {os.path.join(folders.log, 'dpeemain_commit.txt')}"
    )
    os.system(f"cd {os.environ['ANALYSIS_DIR']} && git diff >> {os.path.join(folders.log, 'dpeemain_commit.txt')}")
    # Copy setup.sh to log folder
    os.system(f"cp -r --force {os.path.join(main_dir, 'setup.sh')} {folders.log}")
    # Copy requirements.txt to log folder
    os.system(f"cp -r --force {os.path.join(main_dir, 'requirements.txt')} {folders.log}")

    # Copy all the accessed files to the log folder
    copy_imports()
    # Always copy the cpp functions
    os.system(f"cp -r --force {os.path.join(main_dir, 'cpp_functions')} {folders.log}")
    # Always copy the command template
    os.makedirs(os.path.join(folders.log, "utils"), exist_ok=True)
    os.system(
        f"cp -r --force {os.path.join(main_dir, 'utils/command_template.sh')} {os.path.join(folders.log, 'utils')}"
    )
    # Always copy the CLI file
    os.system(f"cp -r --force {os.path.join(main_dir, 'run_analysis.py')} {folders.log}")
    # Always copy the flow.SFs module
    os.makedirs(os.path.join(folders.log, "flows"), exist_ok=True)
    os.system(f"cp -r --force {os.path.join(main_dir, 'flows/SFs')} {os.path.join(folders.log, 'flows/')}")
    #Always copy the scripts folder
    os.system(f"cp -r --force {os.path.join(main_dir, 'scripts')} {folders.log}")
    return


def copy_imports():
    for file_path in accessed_files:
        relative_path = file_path.split(main_dir)[1]
        if relative_path.startswith("/"):
            relative_path = relative_path[1:]
        newpath = os.path.join(folders.log, f"{os.path.dirname(relative_path)}")
        os.makedirs(newpath, exist_ok=True)
        os.system(f"cp -r --force {file_path} {newpath}")


def print_configs(
    console,
    ncpu,
    nevents,
    nocache,
    cachepath,
    datacards,
    snapshot,
    eras,
    era_paths_Data,
    era_paths_MC,
    PFs,
    PMCs,
):
    console.print()
    config_table = Table(title="Configurations", show_header=True, header_style="bold black")
    config_table.add_column("Key", style="bold red")
    config_table.add_column("Value")
    config_table.add_row("ncpu", str(ncpu))
    config_table.add_row("nevents", str(nevents))
    config_table.add_row("outfolder", folders.outfolder)
    config_table.add_row("Cache", str(not nocache))
    config_table.add_row("Datacards", str(datacards))
    config_table.add_row("Snapshot", str(snapshot))
    if nocache is False:
        config_table.add_row(
            "Cache Path", str(cachepath) if cachepath is not None else folders.cache
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


def print_dataset(console, processtable, datatable, MCtable, eras):
    console.print("[bold red]---------------------- DATASETS ----------------------[/bold red]")
    console.print(f"Running eras: {eras}")
    console.print(processtable)
    console.print(datatable)
    console.print(MCtable)


def print_mcc(console, mccFlow):
    console.print("[bold red]---------------------- MCC ----------------------[/bold red]")
    console.print(mccFlow.__str__().replace("\033[1m", "").replace("\033[0m", ""))


def print_flow(console, flow):
    console.print(f"[bold red]--------------------- FLOW: {flow.name} ----------------------[/bold red]")
    console.print(flow.__str__().replace("\033[1m", "").replace("\033[0m", ""))


def print_yields(yields, all_data, flows, eras, mergeEras, console=Console()):
    for proc in all_data:
        for flow in flows:
            print()
            for era in eras:
                suffix = "" if mergeEras else f" ({era})"
                table = Table(title=f"{proc.name} ({flow.name}){suffix}", show_header=True, header_style="bold black", title_style="bold magenta")
                table.add_column("Cut", style="bold red")
                table.add_column("Expr", style="bold red")
                table.add_column("Pass (+- stat.)", justify="center")
                table.add_column("eff. (+- stat.)", justify="center")
                table.add_column("cumulative eff. (+- stat.)", justify="center")
                table.add_column("xsec*eff. (+- stat.) [pb]", justify="center")
                table.add_column("Plot", justify="center")
                started = False
                for cut in flow:
                    if type(cut) != Cut:
                        continue
                    key_dict = {"flow": flow.name, "process": proc.name, "name": cut.name, "era": era}
                    if mergeEras:
                        key_dict.pop("era")
                    y = yields.getByKey(MultiKey(**key_dict))[-1]
                    if not started:
                        started = True
                        if proc.isData:
                            n_events = y.central
                            old_passed = y.central
                        else:
                            n_events = (y.central**2) / (y.stat**2)
                            old_passed = (y.central**2) / (y.stat**2)

                    if proc.isData:
                        passed = y.central
                    else:
                        passed = (y.central**2) / (y.stat**2)

                    eff = passed / old_passed
                    eff_err = ratio_uncertainty(passed, old_passed, uncertainty_type="efficiency")
                    cumulative_eff = passed / n_events
                    cumulative_eff_err = ratio_uncertainty(passed, n_events, uncertainty_type="efficiency")

                    if proc.isData:
                        old_passed = y.central
                    else:
                        old_passed = (y.central**2) / (y.stat**2)

                    subscripts = str.maketrans("0123456789+-.", "₀₁₂₃₄₅₆₇₈₉₊₋.")
                    superscripts = str.maketrans("0123456789+-.", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻˙")

                    eff_err_minus = f"-{(eff_err[0]*100):.3f}".translate(subscripts)
                    eff_err_plus = f"+{(eff_err[1]*100):.3f}".translate(superscripts)
                    cumulative_eff_err_minus = f"-{(cumulative_eff_err[0]*100):.3f}".translate(subscripts)
                    cumulative_eff_err_plus = f"+{(cumulative_eff_err[1]*100):.3f}".translate(superscripts)


                    proc_xsec_err_minus = f"-{(proc.xsec*cumulative_eff_err[0]):.3f}".translate(subscripts) if getattr(proc,"xsec", None) is not None else ""
                    proc_xsec_err_plus = f"+{(proc.xsec*cumulative_eff_err[1]):.3f}".translate(superscripts) if getattr(proc,"xsec", None) is not None else ""
                    table.add_row(
                        cut.name,
                        ' '.join(cut.expr.split()),
                        f"{y.central:.0f} +- {y.stat:.0f}",
                        f"{(eff*100):.3f}{eff_err_minus}{eff_err_plus}%" if started else "",
                        f"{(cumulative_eff*100):.3f}{cumulative_eff_err_minus}{cumulative_eff_err_plus} %" if started else "",
                        f"{cumulative_eff*proc.xsec:.3f}{proc_xsec_err_minus}{proc_xsec_err_plus}" if getattr(proc,"xsec", None) is not None else "",
                        "\u2713" if hasattr(cut, "plot") else ""
                    )

                format_dict = {"era": era, "flow": flow.name}
                if mergeEras: format_dict.pop("era")
                os.makedirs(folders.tables_path.format(**format_dict), exist_ok=True)
                format_dict["name"] = proc.name
                with open(folders.tables.format(**format_dict), "wt") as report_file:
                    flow_console = Console(file=report_file)
                    flow_console.print(table)
                console.print(table)
                console.print("\n")
                if mergeEras:
                    break
        if not mergeEras:
            console.print(
                f"        [bold magenta]------------------------- END FLOW {flow.name} -----------------------------[/bold magenta]"
            )
            console.print("\n")
    console.print(
        f"[bold green]----------------------------------END PROC {proc.name}------------------------------------[/bold green]"
    )
    console.print("\n")



def print_snapshot(console, report, columnSel, columnVeto, MCpattern, flowPattern):
    console.print("[bold red]---------------------- SNAPSHOTS ----------------------[/bold red]")
    console.print(f"columnSel: {columnSel.split(',') if columnSel is not None else []}")
    console.print(f"columnVeto: {columnVeto.split(',') if columnVeto is not None else []}")
    console.print(f"MCpattern: {MCpattern if MCpattern is not None else []}")
    console.print(f"flowPattern: {flowPattern if flowPattern is not None else []}")
    snapshot_table = Table(title="Snapshots", show_header=True, header_style="bold black")
    snapshot_table.add_column("Flow", style="bold red")
    snapshot_table.add_column("Process")
    snapshot_table.add_column("Sample")
    snapshot_table.add_column("Era")
    snapshot_table.add_column("Entries")
    snapshot_table.add_column("Size")
    snapshot_table.add_column("Path")
    for key, snap in report:
        snapshot_table.add_row(
            key.flow, key.process, key.sample, key.era, f"{snap.entries}", f"{(snap.size/(1024.**3)):9.3f} GB", snap.fname
        )
    console.print(snapshot_table)
