import os
import re

from CMGRDF import Data, DataSample, MCSample, Process, Cut, MCGroup
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
MCtable.add_column("Group", style="bold red")
MCtable.add_column("Samples", style="bold red")
MCtable.add_column("xsec", style="bold red")
MCtable.add_column("Eras", style="bold red")
MCtable.add_column("Selections", style="bold red")


def AddData(data_dict, friends, era_paths, mccFlow=None, eras = []):
    if mccFlow is None:
        mcc_steps = []
    else:
        mcc_steps = mccFlow.steps

    data_datasets = []
    for era, samples in data_dict.items():
        if era not in eras:
            continue
        datatable.add_row(era, "", "", "")
        P0, samples_path, friends_path = era_paths[era]
        samples_path = os.path.join(P0, samples_path)
        friends_path = os.path.join(P0, friends_path)
        for sample in samples:
            sample_name, suberas, triggers = sample
            processtable.add_row(sample_name, "Data")
            datatable.add_row("", sample_name, str(suberas), triggers)
            filtered_mcc = [step for step in mcc_steps if step.onData]
            hook = Prepend(*[*filtered_mcc, Cut("Trigger", triggers)])
            data_datasets += [
                DataSample(
                    f"{sample_name}_Run{era}{subera}", #NEEDED especially for the snapshot (otherwise same filename)
                    samples_path.format(subera=subera, name=sample_name, era="{era}"),
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

#!Add table
def AddMC(all_processes, friends, era_paths, mccFlow=None, eras = []):
    if mccFlow is None:
        mcc_steps = []
    else:
        mcc_steps = mccFlow.steps

    #! Loop over all processes
    process_list = []
    for (process, process_dict) in all_processes.items():
        groups_list = process_dict["groups"]
        label = process_dict["label"]
        color = process_dict["color"]
        mcgroup_samples=[]
        processtable.add_row(process, "MC")
        MCtable.add_row(process, "", "", "", "", "")
        #! Loop over all groups
        for group_dict in groups_list:
            group_name = group_dict["name"]
            samples = group_dict["samples"]
            cut = getattr(group_dict, "cut", "1")
            #If eras is not defined in the group but is defined in the process, inherit it
            if "eras" in process_dict and "eras" not in group_dict:
                group_dict["eras"] = process_dict["eras"]
            MCtable.add_row("", group_name, "", "", str(group_dict.get("eras", eras)) , cut)

            #Create MCGroup hook
            hook_steps = []

            #Attach MCC steps to hooks
            for mcc_step in mcc_steps:
                if hasattr(mcc_step, "process") and hasattr(mcc_step, "group"):
                    raise ValueError("Cannot have both process and group in the same step")
                if hasattr(mcc_step, "process"):
                    if bool(re.match(mcc_step.process, process)):
                        hook_steps.append(mcc_step)
                elif hasattr(mcc_step, "group"):
                    if bool(re.match(mcc_step.group, group_name)):
                        hook_steps.append(mcc_step)
                else:
                    hook_steps.append(mcc_step)

            #Attach group cuts to hooks
            if cut != "1":
                hook_steps.append(Cut("Selection", cut))
            hook = Prepend(*hook_steps)

            #! Loop over all samples
            for sample in samples:
                sample_name, xsec = sample if isinstance(sample, tuple | list) else (sample, "xsec")
                MCtable.add_row("", "", sample_name, str(xsec), "", "")

                #! Loop over all eras
                for (era, paths) in era_paths.items():
                    if era not in eras:
                        continue
                    if "eras" in group_dict and era not in group_dict["eras"]:
                        continue

                    P0, samples_path, friends_path = paths
                    samples_path = os.path.join(P0, samples_path)
                    friends_path = os.path.join(P0, friends_path)

                    group_kwargs = {
                        key: value
                        for key, value in group_dict.items()
                        if key not in ["name", "samples", "eras", "cut"]
                    }
                    mcgroup_samples.append(
                        MCSample(
                        sample_name,
                        samples_path,
                        friends=[friends_path.format(folder=friend, name="{name}", era="{era}") for friend in friends],
                        xsec=xsec,
                        eras=[era],
                        hooks=[hook],
                        **group_kwargs,
                        )
                    )
        MCtable.add_section()
        process_list.append(MCGroup(group_name, mcgroup_samples))
    process_kwargs = {
        key: value
        for key, value in process_dict.items()
        if key not in ["groups", "eras", "label", "color"]
    }
    all_data.append(Process(process, process_list, label=label, fillColor=color, **process_kwargs))