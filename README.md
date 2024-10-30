[TOC]

# ACHTUNG!!! THIS IS A WORK IN PROGRESS, THINGS WILL CHANGE

## TODO

https://codimd.web.cern.ch/s/7BImZD6LD#

# Instructions

Clone this repository with the `--recursive` option, so `cmgrdf-prototype` is also cloned. While cloning, you will be asked to enter your gitlab user name and password when grabbing the cmg-rdf submodule. After, follow the set-up instructions as described in that repository.

**Note: cmgrdf works both on el8 and el9 machines. But el9 is preferred.**

```bash
git clone --recursive ssh://git@gitlab.cern.ch:7999/darkphoton-ee/dp-ee-main.git
cd sos-analysis
```
The setup.sh script will setup everything needed.

The setup.sh command must be sourced everytime you enter the analysis area (like ```cmsenv``` in CMSSW environments).

The first time you run it you have to use the "build" option to build cmgrdf

```bash
source setup.sh build
```

After the first time, you can just run

```bash
source setup.sh
```


>**WARNINGS**
>1. In case you have problems with el8, you can use an el9 container
>```bash
>apptainer shell -B /eos -B /afs -B /cvmfs /cvmfs/unpacked.cern.ch/gitlab-registry.cern.ch/sft/docker/alma9:latest
>```
>2. If you switch from an el8 machine to an el9 machine, you have to rebuild cmgrdf re-running the setup.sh script with the "build" option.
>3. If you use zsh shell, you have to run the setup.sh script with bash shell, so you have to run ```source setup.sh``` in bash and then re-launch zsh. ```bash -c "source setup.sh; zsh"```

More information can be found in the [cmg-rdf](https://gitlab.cern.ch/cms-new-cmgtools/cmgrdf-prototype) repository.


### Examples

Some examples can be found in the [sos_port_beginners branch](https://gitlab.cern.ch/sos-framework/sos-analysis/-/tree/sos_port_beginners?ref_type=heads)


### Debug

The fastest way to debug the code is to put a breakpoint in the code where you want to stop and use pbd in the interact mode.

```python
#code..
breakpoint()
#code..
```

```bash
python -i run_main_script.py
(pbd)> interact
(pbd)> #Do your checks and inspections
```
In the interact mode you can run the code you want as you are in the shell at the point where you put the breakpoint.
To exit the interact mode press CTRL + D.

Outside the interact mode you can use the following commmands to move in the code and between the breakpoints.

**Cheatsheet**

| command | description |
| --- | --- |
`h` | print help
`n` | execute current line of code, go to next line
`s` | execute current line of code; follow execution inside the functions
`c` | continue executing the program until next breakpoint
`l` | print code around the current line
`w` | show a trace of the function call that led to the current line
`p` | print the value of a variable
`q` | leave the debugger
`b [line\|func]` | set a breakpoint at a given line number or function
`cl` | clear a breakpoint
`!` | execute a python command
`<enter>` | repeat last command





# Structure of the repo

## CFGs
In the `cfg` folder you can find the configuration files that are used to define the Data/MC sample and their friend paths.

The paths of the samples are defined respectively in `era_paths_MC` and `era_paths_Data` dictionaries.

```python
era_paths_Data={
    era:(base_path, sample_path_suffix, friend_path_suffix),
    ...
}
```
You can use as placeholder for era, sample name and subera the following strings: `{era}`, `{name}`, `{subera}`

## Sample definition

The definition of the samples is in the `data` directory.

The format of the data dictionary is the following

```python
data={
    era:[
        (name:str, suberas:List, triggers:str),
        ...#other samples
        ],
    ...#other eras
}
```

while for MC samples:

```python
dicts_list=[{
    "name": process_name,
    "samples": [
        nameSample1, #if string, xsec = xsec in friends
        (nameSample2, 87.31484), #if tuple, xsec is the second element
        ...#other samples
        ],
    "label":label,
    "color": root_color,
    "cut":cut_string
    "eras": era_list #OPTIONAL, eras where the sample is present
},
    ...#other processes
]
```
If a group of samples is used often in multiple processes, you can put the `samples` lists in `data/MC/sample_lists.py` and import them to build the process dictionaries.

The processes are defined in the directory `data/MC`. Group of MC samples are imported and grouped in the MCProcesses files in `data`, into the list `all_processes`

```python
from data.MC import l2os_prompt_tt, l2os_prompt_dy, l2os_prompt_vv,#...

all_processes=[
    *l2os_prompt_tt.prompt_tt,
    *l2os_prompt_dy.prompt_dy,
    *l2os_prompt_vv.prompt_vv,
    #...
]
```
> **Note**
> If you have to apply different cuts in the same process is perfectly fine to define multiple dictionaries with the sampe process name and different samples and cuts.
> The only thing is that, when plotting, the color and the label of the process will be taken from the first definition of the process.

### AddData & AddMC
The list that contains all the Data and MC samples is `all_data` defined in the `data` module.
To create the datasets you have to use the `AddData` and `AddMC` methods defined in the `data` module as follows:

```python
from data.data import data
from data.MCProcesses import all_processes #MCProcesses is the chosen MC config
from cfg.cfg_disp import era_paths_Data, era_paths_MC, PFs, PMCs #cfg_disp is the chosen cfg config
from mcc.mcc_disp import mccFlow #mcc_disp is the chosen mcc config

from data import AddMC, AddData, all_data
AddData(data,era_paths=era_paths_Data, friends=PFs, mccFlow=mccFlow)
AddMC(all_processes, era_paths=era_paths_MC,friends=PMCs, mccFlow=mccFlow)
```
---
## MCC
In the `mcc` folder you can find the equivalent of the mcc configs in CMGTools, defined as flows.

The mccFlows have to be passed to the `AddData` and `AddMC` methods defined in `data/__init__.py` that will pass the flow as hooks to the samples, along with the triggers and cuts defined in the samples.

In the flowsteps you can pass also the `process` argument. This is not used internally CMGRDF, but is parsed in AddMC in such a way that the flowstep is added to the sample hooks just if there is a regex match between the process argument and the process name.


## Flows (TBD)
In the `flows` folder you can find the flows that are used to define the analysis and the different regions.

## Plots
In the `plots` folder you can define the plots that you want to produce in the analysis, import in the main script and pass them to the `Processor` class.

> **Warining**
> Define the range of the plots with floats, otherwise CMGRDF will get angry. (Under investigation)

## cpp_functions
In the `cpp_functions` folder you can define cpp ROOT functions to use if the RDF calls.
All the cpp functions defined in this folder are passed to the ROOT interpreter.

To let ROOT load all the functions defined in the cpp_functions folder, you just have to
```python
import cpp_functions
cpp_functions.load()
```
You can also pass to `load` just the name of the files that you want to load or you can pass the `exclude` list argument to load all the files except the ones in the list.

> **Achtung!**
> 1. Put always `#pragma once` at the beginning of the cpp files.
> 2. Some common functions are already defined in cmgrdf `cmgrdf-prototype/include/functions.h`

## Main script
In ther root folder you can find the `run_xxx.py` scripts. These scripts are the main scripts that are used to run the analysis.

In them you can import the flows, combine them, import the plots and run the analysis.

```bash
python run_xxx.py
```

#### Main script template

```python
import ROOT

from CMGRDF import Processor, PlotSetPrinter
from CMGRDF.cms.eras import lumis as lumi
from data import AddMC, AddData, all_data

from data.data import data

#! Load cpp functions (!!!DO IT BEFORE IMPORTING OTHER STUFF!!!)
import cpp_functions
cpp_functions.load()
#! ------------------------- RDF CONFIG -------------------------- !#
verbosity = ROOT.Experimental.RLogScopedVerbosity(
    ROOT.Detail.RDF.RDFLogChannel(), ROOT.Experimental.ELogLevel.kInfo
)
#! Set number of cores (max by default)
ROOT.EnableImplicitMT()

#! ---------------------- IMPORTS TO CHANGE ----------------------- !#
#!Change the `xxx_test` modules with the ones that you want to run
from mcc.mcc_test import mccFlow
from data.MCTest import all_processes
from cfg.cfg_test import era_paths_Data, era_paths_MC, PFs, PMCs
from plots.plots_test import plots
from flows.flow_test import flow

#eras to analyze ["2016APV","2016", "2017", "2018"]
eras=["2018"]
#Output folder
outfolder="temp/plots_{flow}/"
#! ---------------------- DATASET BUILDING ----------------------- !#
#! They create the datasets, adding everything to all_data list
AddData(data,era_paths=era_paths_Data, friends=PFs, mccFlow=mccFlow)
AddMC(all_processes, era_paths=era_paths_MC,friends=PMCs, mccFlow=mccFlow)



#! ---------------------- RUN THE ANALYSIS ----------------------- !#
maker = Processor().book(all_data, lumi, flow, plots, eras=eras).runPlots()
printer = PlotSetPrinter(
    topRightText="L = %(lumi).1f fb^{-1} (13 TeV)", stack=True
).printSet(maker, outfolder)
```
result example: https://pviscone.web.cern.ch/plots_2los_cuts_2018/

# Recap
1. Define the cfgs, MC, mcc, plots, flows creating a new file in the respective folder. Use always the same name for the objects in the files.
2. Import the wanted files in the main script (replace the `xxx_test` modules in the main script template above) (In the future we will implement a CLI to select the wanted files)
3. Run the main script `python run_xxx.py`

