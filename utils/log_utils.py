import os

from CMGRDF import Cut, MultiKey
from hist.intervals import ratio_uncertainty
from rich.console import Console
from rich.table import Table

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


def write_log(outfolder, command, cachepath):
    if cachepath is None:
        cachestring = "--cachepath ../cache"
    elif isinstance(cachepath, str):
        # Strip cachepath from command
        command = command.replace(f" --cachepath {cachepath}", "")
        # get asbolute path
        cachepath = os.path.abspath(cachepath)
        cachestring = f"--cachepath {cachepath}"
    else:
        cachestring = ""
    # Write the command string to file
    os.makedirs(f"{outfolder}/log", exist_ok=True)
    os.system(
        f"cp -r --force {os.path.join(main_dir, 'utils/command_template.sh')} {os.path.join(outfolder, 'log/command.sh')}"
    )
    os.system(f'echo "python {command} {cachestring}" >> {os.path.join(outfolder, "log/command.sh")}')
    #get abs path to outfolder
    abs_outfolder = os.path.abspath(outfolder)

    # Write cmgrdf commit hash and, eventually, git diff to cmdrdf_commit.txt
    os.system(
        f"cd {os.environ['CMGRDF']} && git describe --match=NeVeRmAtCh --always --abbrev=40 --dirty > {os.path.join(abs_outfolder, 'log/cmgrdf_commit.txt')}"
    )
    os.system(f"cd {os.environ['CMGRDF']} && git diff >> {os.path.join(abs_outfolder, 'log/cmgrdf_commit.txt')}")

    # Copy all the accessed files to the log folder
    copy_imports(outfolder)
    # Always copy the cpp functions
    os.system(f"cp -r --force {os.path.join(main_dir, 'cpp_functions')} {os.path.join(outfolder, 'log')}")
    # Always copy the command template
    os.makedirs(os.path.join(outfolder, "log/utils"), exist_ok=True)
    os.system(
        f"cp -r --force {os.path.join(main_dir, 'utils/command_template.sh')} {os.path.join(outfolder, 'log/utils')}"
    )
    # Always copy the CLI file
    os.system(f"cp -r --force {os.path.join(main_dir, 'run_analysis.py')} {os.path.join(outfolder, 'log')}")
    return


def copy_imports(outfolder):
    for file_path in accessed_files:
        relative_path = file_path.split(main_dir)[1]
        newpath = os.path.join(outfolder, f"log/{os.path.dirname(relative_path)}")
        os.makedirs(newpath, exist_ok=True)
        os.system(f"cp -r --force {file_path} {newpath}")


def print_yields(yields, all_data, flow, console=Console()):
    console.print("[bold red]---------------------- YIELDS -----------------------[/bold red]")
    console.print(f"CutFlow: [bold magenta]{flow.name}[/bold magenta]")
    for proc in all_data:
        print()
        table = Table(title=proc.name, show_header=True, header_style="bold black", title_style="bold magenta")
        table.add_column("Cut", style="bold red")
        table.add_column("Expr", style="bold red")
        table.add_column("Pass (+- stat.)", justify="center")
        table.add_column("eff. (+- stat.)", justify="center")
        table.add_column("cumulative eff. (+- stat.)", justify="center")

        started = False
        for cut in flow:
            if type(cut) != Cut:
                continue
            y = yields.getByKey(MultiKey(flow=flow.name, process=proc.name, name=cut.name))[-1]
            if not started:
                nMC_events = (y.central**2) / (y.stat**2)
                oldMC_passed = (y.central**2) / (y.stat**2)

            mc_passed = (y.central**2) / (y.stat**2)
            eff = mc_passed / oldMC_passed
            eff_err = ratio_uncertainty(mc_passed, oldMC_passed, uncertainty_type="efficiency")
            cumulative_eff = mc_passed / nMC_events
            cumulative_eff_err = ratio_uncertainty(mc_passed, nMC_events, uncertainty_type="efficiency")
            oldMC_passed = (y.central**2) / (y.stat**2)

            subscripts = str.maketrans("0123456789+-.", "₀₁₂₃₄₅₆₇₈₉₊₋.")
            superscripts = str.maketrans("0123456789+-.", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻˙")

            eff_err_minus = f"-{(eff_err[0]*100):.3f}".translate(subscripts)
            eff_err_plus = f"+{(eff_err[1]*100):.3f}".translate(superscripts)
            cumulative_eff_err_minus = f"-{(cumulative_eff_err[0]*100):.3f}".translate(subscripts)
            cumulative_eff_err_plus = f"+{(cumulative_eff_err[1]*100):.3f}".translate(superscripts)

            table.add_row(
                cut.name,
                cut.expr,
                f"{y.central:.0f} +- {y.stat:.0f}",
                f"{(eff*100):.3f}{eff_err_minus}{eff_err_plus}%" if started else "",
                f"{(cumulative_eff*100):.3f}{cumulative_eff_err_minus}{cumulative_eff_err_plus} %"  if started else "",
            )
            started = True
        console.print(table)
    console.print("[bold magenta]------------------------------------------------------------------------------------------------------[/bold magenta]")
