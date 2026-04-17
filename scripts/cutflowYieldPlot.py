#!/usr/bin/env python
# %%
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import re
import glob
from cmgrdf_cli.plots.plotters import set_palette, ggplot_palette
from cmgrdf_cli.utils.cli_utils import copy_file_to_subdirectories
import concurrent
import typer
from typing_extensions import Annotated
from typing import Tuple
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import mplhep

set_palette(ggplot_palette)

app = typer.Typer(
    pretty_exceptions_show_locals=False, rich_markup_mode="rich", add_completion=False
)

color_palette = [
    "#1f77b4",
    "#aec7e8",  # Blues
    "#ff7f0e",
    "#ffbb78",  # Oranges
    "#2ca02c",
    "#98df8a",  # Greens
    "#d62728",
    "#ff9896",  # Reds
    "#9467bd",
    "#c5b0d5",  # Purples
    "#8c564b",
    "#c49c94",  # Browns
    "#e377c2",
    "#f7b6d2",  # Pinks
    "#7f7f7f",
    "#c7c7c7",  # Grays
    "#bcbd22",
    "#dbdb8d",  # Olive/Yellows
    "#17becf",
    "#9edae5",  # Teals
]


def parse_uncertainty_string(s):
    # Mapping for Subscripts (lower error)
    sub_map = str.maketrans("₀₁₂₃₄₅₆₇₈₉₋₊", "0123456789-+")

    # Mapping for Superscripts (upper error)
    # Note: '˙' (U+02D9) is often used as a superscript decimal point
    sup_map = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻˙", "0123456789+-.")

    # 1. Separate the units if necessary
    s = s.replace("%", "").strip()

    # 2. Use regex to find the segments:
    # [Central Value] [Subscript Part] [Superscript Part]
    # This regex looks for a block of standard chars, then a block of subscripts, then superscripts
    pattern = r"([\d\.]+)([₀-₉₋₊\.]+)([⁺⁻].*)"
    match = re.match(pattern, s)

    if match:
        central_raw = match.group(1)
        lower_raw = match.group(2)
        upper_raw = match.group(3)

        # 3. Translate the Unicode characters to standard ASCII
        central = float(central_raw)
        lower_err = float(lower_raw.translate(sub_map))
        upper_err = float(upper_raw.translate(sup_map))

        return {"central": central, "lower_error": lower_err, "upper_error": upper_err}
    return None


@app.command()
def plot_efficiency(
    #! ---------------------- Configs ---------------------- #
    inputfolder: Annotated[
        str,
        typer.Option(
            "-i",
            "--in",
            help="Path of the cmgrdf outfolder (containing all the flow_name/root_files)",
            rich_help_panel="Configs",
        ),
    ],
    outfolder: str = typer.Option(
        "", "-o", "--out", help="Output folder", rich_help_panel="Configs"
    ),
    logeff: bool = typer.Option(
        False,
        "--logeff",
        help="Plot efficiency in log scale",
        rich_help_panel="Configs",
    ),
    logyield: bool = typer.Option(
        False, "--logyield", help="Plot yield in log scale", rich_help_panel="Configs"
    ),
    noReplace: bool = typer.Option(
        False,
        "-n",
        "--noReplace",
        help="Do not replace existing plots",
        rich_help_panel="Configs",
    ),
    allEras: bool = typer.Option(
        False, "-e", "--allEras", help="Plot all eras", rich_help_panel="Configs"
    ),
    #! ---------------------- Legend arguments ---------------------- #
    bbox_to_anchor: Tuple[float, float] = typer.Option(
        (1.2, 0.5), "-b", "--bbox", help="bbox_to_anchor", rich_help_panel="Legend"
    ),
    loc: str = typer.Option(
        "lower center", "-l", "--loc", help="loc", rich_help_panel="Legend"
    ),
    ncol: int = typer.Option(1, "--ncol", help="ncol", rich_help_panel="Legend"),
    fontsize: float = typer.Option(
        15, "-f", "--fontsize", help="fontsize", rich_help_panel="Legend"
    ),
):
    if allEras:
        inputfolders = glob.glob(
            os.path.join(os.path.abspath(inputfolder), "era*/*/csv/")
        )
    else:
        inputfolders = glob.glob(os.path.join(os.path.abspath(inputfolder), "*/csv/"))

    for inputfolder in inputfolders:
        print(f"Processing {inputfolder}")

        legend_kwargs = dict(
            bbox_to_anchor=bbox_to_anchor, loc=loc, ncol=ncol, fontsize=fontsize
        )

        if outfolder:
            os.makedirs(os.path.join(inputfolder, outfolder), exist_ok=True)

        if (
            os.path.exists(os.path.join(inputfolder, outfolder, "yields.png"))
            and noReplace
        ):
            print(f"Yields plot already exists for {inputfolder}, skipping...")
            return

        fig_yields, ax_yields = plt.subplots(figsize=(11, 10))
        fig_eff, ax_eff = plt.subplots(figsize=(11, 10))
        for idx, csvfile in enumerate(glob.glob(os.path.join(inputfolder, "*.csv"))):
            process = csvfile.split("/")[-1].replace(".csv", "")
            df = pd.read_csv(csvfile)
            cuts = df["Cut"].to_list()
            yields = df["Pass (+- stat.)"].to_list()
            effs = df["cumulative eff. (+- stat.)"].to_list()
            ax_yields.errorbar(
                cuts,
                [int(y.split(" +- ")[0]) for y in yields],
                yerr=[int(y.split(" +- ")[1]) for y in yields],
                label=process,
                marker="o",
                linestyle="-",
                color=color_palette[idx % len(color_palette)],
            )
            ax_eff.errorbar(
                cuts,
                [parse_uncertainty_string(e)["central"] / 100 for e in effs],
                yerr=[
                    [
                        np.abs(parse_uncertainty_string(e)["lower_error"]) / 100
                        for e in effs
                    ],
                    [parse_uncertainty_string(e)["upper_error"] / 100 for e in effs],
                ],
                label=process,
                marker="o",
                linestyle="-",
                color=color_palette[idx % len(color_palette)],
            )
        ax_yields.set_ylabel("Yield")
        ax_yields.legend(**legend_kwargs)
        ax_yields.set_xticklabels(cuts, rotation=45, ha="right")
        if logyield:
            ax_yields.set_yscale("log")
        mplhep.cms.text("Preliminary", loc=0, ax=ax_yields)
        fig_yields.savefig(os.path.join(inputfolder, outfolder, "yields.png"))
        fig_yields.savefig(os.path.join(inputfolder, outfolder, "yields.pdf"))

        ax_eff.set_ylim(0, 1.2)
        ax_eff.set_ylabel("Cumulative Efficiency")
        ax_eff.legend(**legend_kwargs)
        ax_eff.set_xticklabels(cuts, rotation=45, ha="right")
        if logeff:
            ax_eff.set_yscale("log")
            ax_eff.set_ylim(1e-3, 2e0)
        mplhep.cms.text("Preliminary", loc=0, ax=ax_eff)
        fig_eff.savefig(os.path.join(inputfolder, outfolder, "efficiency.png"))
        fig_eff.savefig(os.path.join(inputfolder, outfolder, "efficiency.pdf"))


if __name__ == "__main__":
    app()
