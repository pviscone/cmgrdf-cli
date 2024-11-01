import os
import ast

from CMGRDF import Cut, MultiKey
from hist.intervals import ratio_uncertainty
from rich.console import Console
from rich.table import Table

def get_imports_from_module(module):
    if not isinstance(module, str):
        module=module.__file__
    with open(module, "r") as file:
        tree = ast.parse(file.read(), filename=module)

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module if node.module else ""
            for alias in node.names:
                imports.append(f"{module}/{alias.name}")

    return imports

# I know, I know, paths should not be handled in this horrible way, but it's midnight.
# I get it, Mr. Clean Code. I will polish this later. I promise. Maybe.

# Recursively look for imports and copy the modules
def get_imports_and_copy(module, outfolder):
    main_dir=os.environ['CMGRDF'].rsplit("/", 1)[0]
    imports = get_imports_from_module(module)

    blacklist=["CMGRDF", "ROOT", "typing", "types", "importlib", "ast", "os", "sys", "typer"]
    for mod in imports:
        skip=False
        for black in blacklist:
            if black in mod:
                skip=True
                break
        if skip: continue
        mod=mod.replace('.','/')
        if "/" in mod:
            os.makedirs(f"{outfolder}/configs/{mod.rsplit('/',1)[0]}", exist_ok=True)
        os.system(f"cp -r --force {main_dir}/{mod}.py {outfolder}/configs/{mod}.py")
        get_imports_and_copy(f"{outfolder}/configs/{mod}.py", outfolder)


def write_log(outfolder, command, modules=[]):
    os.makedirs(f"{outfolder}/configs", exist_ok=True)
    with open(f"{outfolder}/configs/command.log", "w") as f:
        f.write(command)

    main_dir=os.environ['CMGRDF'].rsplit("/", 1)[0]
    for module in modules:
        if module is None: continue
        module_relative_path = module.__file__.split(main_dir)[1]
        module_dirpath, module_filename = module_relative_path.rsplit('/',1)
        os.makedirs(f"{outfolder}/configs/{module_dirpath}", exist_ok=True)
        os.system(f"cp -r --force {module.__file__} {outfolder}/configs/{module_dirpath}/{module_filename}")
        get_imports_and_copy(module, outfolder)
    return


def print_yields(yields, all_data, flow, console = Console()):
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
