import os
import re

from CMGRDF import Data, DataSample, MCSample, Process, Cut
from CMGRDF.modifiers import Prepend

from rich.table import Table

all_data = []
processtable = Table(title="Processes", show_header=True, header_style="bold black")
processtable.add_column("Process", style="bold red")
processtable.add_column("type", style="bold red")

datatable = Table(title="Data", show_header=True, header_style="bold black")
datatable.add_column("Era", style="bold red")
datatable.add_column("Sample", style="bold red")
datatable.add_column("Suberas", style="bold red")
datatable.add_column("Selections", style="bold red")

MCtable = Table(title="MC Samples", show_header=True, header_style="bold black")
MCtable.add_column("Process", style="bold red")
MCtable.add_column("Samples", style="bold red")
MCtable.add_column("xsec", style="bold red")
MCtable.add_column("Selections", style="bold red")


def AddData(data_dict, friends, era_paths, mccFlow=None):
    if mccFlow is None:
        mcc_steps = []
    else:
        mcc_steps = mccFlow.steps
    for era, samples in data_dict.items():
        datatable.add_row(era, "", "", "")
        P0, samples_path, friends_path = era_paths[era]
        samples_path = os.path.join(P0, samples_path)
        friends_path = os.path.join(P0, friends_path)
        data_datasets = []
        for sample in samples:
            sample_name, suberas, triggers = sample
            processtable.add_row(sample_name, "Data")
            datatable.add_row("", sample_name, str(suberas), triggers)

            filtered_mcc = [step for step in mcc_steps if step.onData]
            hook = Prepend(*[*filtered_mcc, Cut("Trigger", triggers)])
            data_datasets += [
                DataSample(
                    sample_name,
                    samples_path.format(subera=subera, name="{name}", era="{era}"),
                    friends=[
                        friends_path.format(subera=subera, folder=friend, name="{name}", era="{era}")
                        for friend in friends
                    ],
                    eras=[era],
                    era=era,
                    subera=subera,
                    hooks=[hook],
                )
                for subera in suberas
            ]
        datatable.add_section()
        all_data.append(Data(data_datasets))


def AddMC(all_processes, friends, era_paths, mccFlow=None):
    if mccFlow is None:
        mcc_steps = []
    else:
        mcc_steps = mccFlow.steps
    for process in all_processes:
        process_name = process["name"]
        samples = process["samples"]
        label = process["label"]
        color = process["color"]
        process_samples = []
        processtable.add_row(process_name, "MC")
        MCtable.add_row(process_name, "", "", process["cut"] if "cut" in process else "")
        for sample in samples:
            sample_name, xsec = sample if isinstance(sample, tuple | list) else (sample, "xsec")
            MCtable.add_row("", sample_name, str(xsec), "")
            for (
                era,
                paths,
            ) in era_paths.items():
                P0, samples_path, friends_path = paths
                samples_path = os.path.join(P0, samples_path)
                friends_path = os.path.join(P0, friends_path)
                hook_steps = []
                for mcc_step in mcc_steps:
                    if hasattr(mcc_step, "process"):
                        if bool(re.match(mcc_step.process, process_name)):
                            hook_steps.append(mcc_step)
                    else:
                        hook_steps.append(mcc_step)
                if "cut" in process:
                    hook_steps.append(Cut("Selection", process["cut"]))
                hook = Prepend(*hook_steps)
                if "eras" in process:
                    if era not in process["eras"]:
                        continue

                kwargs = {
                    key: value
                    for key, value in process.items()
                    if key not in ["name", "samples", "label", "color", "eras", "cut"]
                }
                process_samples.append(
                    MCSample(
                        sample_name,
                        samples_path,
                        friends=[friends_path.format(folder=friend, name="{name}", era="{era}") for friend in friends],
                        xsec=xsec,
                        eras=[era],
                        hooks=[hook],
                        **kwargs,
                    )
                )
        MCtable.add_section()
        all_data.append(
            Process(
                process_name,
                process_samples,
                label=label,
                fillColor=color,
            )
        )
