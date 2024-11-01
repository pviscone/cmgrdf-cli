import os

from CMGRDF import Cut, MultiKey
from hist.intervals import ratio_uncertainty
from rich.console import Console
from rich.table import Table

main_dir = os.path.dirname(os.environ["CMGRDF"])  # Path to dp-ee-main folder
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
            and not abs_path.startswith(os.environ["CMGRDF"])
        ):
            accessed_files.append(abs_path)
    return trace_calls


def write_log(outfolder, command, cachepath, modules=[]):
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

    # Write cmgrdf commit hash and, eventually, git diff to cmdrdf_commit.txt
    os.system(
        f"cd {os.environ['CMGRDF']} && git describe --match=NeVeRmAtCh --always --abbrev=40 --dirty > ../{os.path.join(outfolder, 'log/cmgrdf_commit.txt')}"
    )
    os.system(f"cd {os.environ['CMGRDF']} && git diff >> ../{os.path.join(outfolder, 'log/cmgrdf_commit.txt')}")

    # Copy imported modules to log folder
    for module in modules:
        if module is None:
            continue
        module_relative_dirpath = os.path.dirname(module.__file__.split(main_dir)[1])
        module_newpath = os.path.join(outfolder, f"log/{module_relative_dirpath}")
        os.makedirs(module_newpath, exist_ok=True)
        module_dirpath = os.path.dirname(module.__file__)
        # Check if there is __init__.py file in the module_dirpath directory
        if os.path.exists(os.path.join(module_dirpath, f"__init__.py")):
            os.system(f"cp -r --force {os.path.join(module_dirpath, '__init__.py')} {module_newpath}")
        # Copy the module file in a log sub folder
        os.system(f"cp -r --force {module.__file__} {module_newpath}")
        # Always copy the cpp functions
        os.system(f"cp -r --force {os.path.join(main_dir, 'cpp_functions')} {os.path.join(outfolder, 'log')}")
        # Copy the CLI file
        os.system(f"cp -r --force {os.path.join(main_dir, 'run_analysis.py')} {os.path.join(outfolder, 'log')}")
        copy_imports(outfolder)
    return


def copy_imports(outfolder):
    for file_path in accessed_files:
        relative_path = file_path.split(main_dir)[1]
        newpath = os.path.join(outfolder, f"log/{os.path.dirname(relative_path)}")
        os.makedirs(newpath, exist_ok=True)
        os.system(f"cp -r --force {file_path} {newpath}")


def print_yields(yields, all_data, flow, console=Console()):
    console.print("[bold red]---------------------- YIELDS -----------------------[/bold red]")
    for proc in all_data:
        print()
        table = Table(title=proc.name, show_header=True, header_style="bold black", title_style="bold magenta")
        table.add_column("Cut", style="bold red")
        table.add_column("Expr", style="bold red")
        table.add_column("Pass (+- stat.)", justify="center")
        table.add_column("eff. (+- stat.)", justify="center")
        table.add_column("cumulative eff. (+- stat.)", justify="center")

        nMC_events = None
        for cut in flow:
            if type(cut) != Cut:
                continue
            y = yields.getByKey(MultiKey(flow=flow.name, process=proc.name, name=cut.name))[-1]
            if nMC_events is None:
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
                f"{(eff*100):.3f}{eff_err_minus}{eff_err_plus}%",
                f"{(cumulative_eff*100):.3f}{cumulative_eff_err_minus}{cumulative_eff_err_plus} %",
            )
        console.print(table)
