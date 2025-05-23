#!/usr/bin/env python
#%%
import os
import sys

import uproot
import glob
from cmgrdf_cli.plots.plotters import TEfficiency, set_palette, ggplot_palette
from cmgrdf_cli.utils.cli_utils import copy_file_to_subdirectories
import concurrent
import typer
from typing_extensions import Annotated
from typing import Tuple
import yaml

set_palette(ggplot_palette)

app = typer.Typer(pretty_exceptions_show_locals=False, rich_markup_mode="rich", add_completion=False)

def eff_plot(args):
    return _eff_plot(*args)

def _eff_plot(inputfolder, outfolder, denom, effplot_name, nums_dict, variable, teff_kwargs, noReplace):
    #Create effplot folder
    if "_vs_" in variable:
        return
    if not os.path.exists(os.path.join(inputfolder,f'{denom}/{variable}.root')):
        print(f"################################# Skipping variable {variable} for denominator {denom}")
        return
    os.makedirs(os.path.join(inputfolder,f'{outfolder}/{variable}/{denom}/{effplot_name}'), exist_ok=True)
    denom_file = uproot.open(os.path.join(inputfolder, f'{denom}/{variable}.root'))
    samples = [s.split(";")[0] for s in denom_file.keys() if "_total" not in s and "_stack" not in s and "_canvas" not in s and not s.startswith("data")]
    for sample in samples:
        if noReplace and f"{os.path.join(inputfolder,f'{outfolder}/{variable}/{denom}/{effplot_name}/{sample}')}.png" in glob.glob(f"{os.path.join(inputfolder,f'{outfolder}/{variable}/{denom}/{effplot_name}')}/*"):
            continue
        denom_h = denom_file[sample].to_hist()
        varlabel = denom_h.axes[0].label
        sample_label = denom_h.name
        eff = TEfficiency(xlabel=varlabel, lumitext=f"{sample_label} ({effplot_name})", **teff_kwargs)
        eff.add_line(y=1, linewidth=1, color="red", linestyle="--", alpha=0.3)
        eff.add_line(y=0.8, linewidth=1, color="red", linestyle="--", alpha=0.3)
        for num, num_label in nums_dict.items():
            if not os.path.exists(os.path.join(inputfolder, f'{num}/{variable}.root')):
                print(f"################################# Skipping numerator {num} for denominator {denom}")
                continue
            num_h = uproot.open(os.path.join(inputfolder, f'{num}/{variable}.root'))
            if sample not in num_h:
                print(f"################################# Skipping sample {sample} in numerator {num} for denominator {denom}")
                continue
            num_h = num_h[sample].to_hist()
            eff.add(num_h, denom_h, label=num_label)
        eff.save(f"{os.path.join(inputfolder,f'{outfolder}/{variable}/{denom}/{effplot_name}/{sample}')}.png")
        eff.save(f"{os.path.join(inputfolder,f'{outfolder}/{variable}/{denom}/{effplot_name}/{sample}')}.pdf")

_ncpu = os.cpu_count()
@app.command()
def plot_efficiency(
    #! ---------------------- Configs ---------------------- #
    inputfolder    : Annotated[str , typer.Option("-i", "--in", help="Path of the cmgrdf outfolder (containing all the flow_name/root_files)", rich_help_panel="Configs")],
    cfgfile        : Annotated[str , typer.Option("-c", "--cfg", help="Path of the yaml config file", rich_help_panel="Configs")],
    outfolder      : str  = typer.Option("zeff", "-o", "--out", help="Output folder", rich_help_panel="Configs"),
    allvars        : bool = typer.Option(False, "-a", "--all", help="Plot all variables", rich_help_panel="Configs"),
    ncpu           : int  = typer.Option(_ncpu, "-j", "--ncpu", help="Number of cpus", rich_help_panel="Configs"),
    noReplace      : bool = typer.Option(False, "-n", "--noReplace", help="Do not replace existing plots", rich_help_panel="Configs"),
    allEras        : bool = typer.Option(False, "-e", "--allEras", help="Plot all eras", rich_help_panel="Configs"),

    #! ---------------------- Plot arguments ---------------------- #
    rebin          : int  = typer.Option(1, "-r", "--rebin", help="rebin factor", rich_help_panel="Plot"),
    ylim           : Tuple[float, float] = typer.Option([0,1.2], "-y", "--ylim", help="Y axis limits", rich_help_panel="Plot"),
    cmsloc         : int  = typer.Option(1, "--cmsloc", help="CMS location", rich_help_panel="Plot"),
    cmstext        : str  = typer.Option("Preliminary", "--cmstext", help="CMS text", rich_help_panel="Plot"),
    grid           : bool = typer.Option(False, "--grid", help="Grid", rich_help_panel="Plot"),


    #! ---------------------- Legend arguments ---------------------- #
    bbox_to_anchor : Tuple[float, float] = typer.Option((0.5, -0.25), "-b", "--bbox", help="bbox_to_anchor", rich_help_panel="Legend"),
    loc            : str   = typer.Option("lower center", "-l", "--loc", help="loc", rich_help_panel="Legend"),
    ncol           : int   = typer.Option(3, "--ncol", help="ncol", rich_help_panel="Legend"),
    fontsize       : float = typer.Option(15, "-f", "--fontsize", help="fontsize", rich_help_panel="Legend"),
):
    if allEras:
        inputfolders = glob.glob(os.path.join(os.path.abspath(inputfolder), "era*"))
    else:
        inputfolders = [os.path.abspath(inputfolder)]

    for inputfolder in inputfolders:
        print(f"Processing {inputfolder}")
        yaml_cfg = yaml.safe_load(open(cfgfile))

        denom_nums = yaml_cfg["denom_nums"]
        variables = yaml_cfg.get("vars", None) if not allvars else None

        legend_kwargs = dict(bbox_to_anchor=bbox_to_anchor, loc=loc, ncol=ncol, fontsize=fontsize)

        pool_data=[]
        os.makedirs(os.path.join(inputfolder, outfolder), exist_ok=True)

        for denom, eff_dict in denom_nums.items():
            for effplot_name, nums_dict in eff_dict.items():
                if variables is None:
                    variables = glob.glob(os.path.join(inputfolder, f'{denom}/*.root'))
                    variables = [v.split("/")[-1].split(".root")[0] for v in variables]
                for variable in variables:
                    kw = variables[variable]
                    teff_kwargs = dict(rebin=rebin, ylim=ylim, legend_kwargs=legend_kwargs, cmsloc=cmsloc, cmstext=cmstext, grid=grid)
                    if kw is not None:
                        teff_kwargs.update(kw)
                    pool_data.append((inputfolder, outfolder, denom, effplot_name, nums_dict, variable, teff_kwargs, noReplace))

        if ncpu > 1:
            with concurrent.futures.ProcessPoolExecutor(ncpu) as executor:
                chunksize = len(pool_data)//ncpu if len(pool_data)//ncpu > 0 else 1
                list(executor.map(eff_plot, pool_data, chunksize = chunksize))
        elif ncpu == 1:
            for data in pool_data:
                eff_plot(data)
        else:
            raise ValueError("Number of cpus must be greater than 0")

        os.makedirs(os.path.join(inputfolder, outfolder, "scripts"), exist_ok=True)
        os.makedirs(os.path.join(inputfolder, outfolder, "scripts", "eff_cfg"), exist_ok=True)
        os.system(f"cp {os.environ['CMGRDF_CLI']}/scripts/efficiencyPlots.py {os.path.join(inputfolder, outfolder, 'scripts')}")
        os.system(f"cp {os.path.abspath(cfgfile)} {os.path.join(inputfolder, outfolder, 'scripts', 'eff_cfg')}")

        command = " ".join(sys.argv).replace('"', r'\\\"')
        os.system(fr'echo "python {command}" > {os.path.join(inputfolder, outfolder, "command.sh")}')
        os.system(f"chmod +x {os.path.join(inputfolder, outfolder, 'command.sh')}")
        copy_file_to_subdirectories(os.path.join(os.environ["CMGRDF"], "externals/index.php"), os.path.join(inputfolder, outfolder))

if __name__ == "__main__":
    app()
