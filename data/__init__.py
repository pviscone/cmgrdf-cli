import os
import re

from CMGRDF import Data, DataSample, MCSample, Process, Cut
from CMGRDF.modifiers import Prepend

all_data = []


def AddData(data_dict, friends, era_paths, mccFlow=None):
    if mccFlow is None:
        mcc_steps = []
    else:
        mcc_steps = mccFlow.steps
    for era, samples in data_dict.items():
        P0, samples_path, friends_path = era_paths[era]
        samples_path = os.path.join(P0, samples_path)
        friends_path = os.path.join(P0, friends_path)
        data_datasets = []
        for sample in samples:
            sample_name, suberas, triggers = sample

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
        for sample in samples:
            sample_name, xsec = sample if isinstance(sample, tuple | list) else (sample, "xsec")
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
                if "cut" in process: hook_steps.append(Cut("Selection",process["cut"]))
                hook = Prepend(*hook_steps)
                if "eras" in process:
                    if era not in process["eras"]:
                        continue
                try:
                    process_samples.append(
                        MCSample(
                            sample_name,
                            samples_path,
                            friends=[
                                friends_path.format(folder=friend, name="{name}", era="{era}") for friend in friends
                            ],
                            xsec=xsec,
                            eras=[era],
                            hooks=[hook],
                        )
                    )
                except Exception:
                    print(f"MCSample {sample_name} not found for era {era}")
        all_data.append(
            Process(
                process_name,
                process_samples,
                label=label,
                fillColor=color,
            )
        )
