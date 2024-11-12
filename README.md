[TOC]

**ACHTUNG!!! THIS IS A WORK IN PROGRESS, THINGS WILL CHANGE**

### TODO

https://codimd.web.cern.ch/s/7BImZD6LD#

# Setup

Clone this repository with the `--recursive` option, so `cmgrdf-prototype` is also cloned. While cloning, you will be asked to enter your gitlab user name and password when grabbing the cmg-rdf submodule. After, follow the set-up instructions as described in that repository.

**Note: cmgrdf works both on el8 and el9 machines. But el9 is preferred.**

```bash
git clone --recursive ssh://git@gitlab.cern.ch:7999/darkphoton-ee/dp-ee-main.git
cd dp-ee-main
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

The commmand `run_example.sh` run a simple example


### Debug

The fastest way to debug the code is to put a breakpoint in the code where you want to stop and use pbd in the interact mode.

```python
#code..
breakpoint()
#code..
```
<details>
<summary>Details:</summary>

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


</details>

---


# Configuration files

### cpp_functions
In the `cpp_functions` folder you can define cpp ROOT functions to use if the RDF calls.
All the cpp functions defined in this folder are passed to the ROOT interpreter.


> **Achtung!**
> 1. Put always `#pragma once` at the beginning of the cpp files.
> 2. Some common functions are already defined in cmgrdf `cmgrdf-prototype/include/functions.h`

### CFGs
In the `cfg` folder you can find the configuration files that are used to define the Data/MC sample and their friend paths.

The paths of the samples are defined respectively in `era_paths_MC` and `era_paths_Data` dictionaries.

```python
era_paths_Data={
    era:(base_path, sample_path_suffix, friend_path_suffix),
    ...
}
```
You can use as placeholder for era, sample name and subera the following strings: `{era}`, `{name}`, `{subera}`

### Sample definition

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


### MCC
*Optional*

The MCC is just a **list** of flowstep that are added to each sample as a Prepend hook. They usually contains just a bunch of alias.

The MCC config file must contain a list of flowsteps or a function that return a list of flowstep called `mccFlow`

### Flows
The flow config file contains the analysis flow.
It must contain a Flow object or a function that return a Flow object called `flow`

### Plots
The plot config file contains the list of plots to plot.
Currently only 1D and 2D histograms are supported (e.g. no TEfficiency)

Instead of using `Plot` objects from CMGRDF, you can use `Hist` (for 1D) and `Hist2D` (for 2D).

`from plots import Hist`

They work exactly like CMGRDF `Plots` objects but with Hist you can make advantage of defaults arguments.

In `plots/defaults.py` you can set default arguments for the histogram. You can find 5 dictionaries:
- global_defaults : These arguments are passed to all the histograms
- histo1d_defaults: These arguments are passed to all the 1D histograms
- histo2d_defaults: These arguments are passed to all the 2D histograms
- name1d_defaults : Here you can define a regex pattern as a key and a dictionary for each regex pattern. The first regex pattern that will match the name of a 1D `Hist` object will have the defined arguments applied
- name2d_defaults : Same thing but for 2D Hists **(Not implemented yet)**

Of course, you can ovverride the defalut values just defining a new one in the `Hist` definition
The priority is

` global_defaults < histo1d_defaults < branch_defaults < user defined`


The config file must contain a list of Hists or a function that returns a list of Hists called `plots`

### Corrections and systematics
Here the things are a bit weird.

Since we have to apply different corrections to different eras and there is no way to have access to the era in the `_attach` method of the FlowStep objects, here there are a bunch of workarounds to make everything work.

To fix this, CMGRDF would require a huge refactoring

To define a correction/variation you have to create a class that inherits `from flows.SFs import BaseCorrection`
the class must have an `__init__` and an `init` method.

The `__init__` method is used just to store the name of the branches that you need to compute the variation

For the `init` method let's distinguish between Event weight corrections and branch corrections (e.g. JES)

In the `init(self, era)` method you have to:
1. load the right correctionlib json for the given era (you can define a dictionary)
2. write a string with the cpp code that returns a float (for event weights) or an RVec (for branch corrections)
3. Declare the cpp_code with ROOT.gInterpreter.Declare
4. Branch Corrections: return a `from flows.SFs import BranchCorrection` object
4. Weight Corrections: `if self.doSyst: return AddWeightUncerainty else: return AddWeight`
5. Use these new classes in the flow to apply corrections

You can decide if apply also systematic variations to each correction using the argument `doSyst` (default True).

>**In general Branch corrections are applied at the beginning of the flow (before the object/event selection) while weight corrections at the end of the flow** Also remember to specify if the corrections have to be applied just on MC or also on Data

Please, don't be mad at me for all this :(

Anyway the best way to understand this is look to electron ID corrections in `flows/SFs/electronID` for Event weight corrections and to electron Smearing corrections in `flows/SFs/electronSS` for branch corrections.


# Command Line Interface
To run the analysis you can use the `run_analysis.py` CLI, use --help to see all the options.

Basically the idea is to pass the name of the config files to run the analysis, e.g.

```bash
python run_analysis.py --cfg cfg/cfg_example.py --data data/data_example.py --mc data/MCProcesses_example.py --flow flows/flow_example.py  --plots plots/plots_example.py -o temp --eras 2023
```

The needed arguments are:
- cfg: path to the cfg config file
- data: path to the data config file
- mc: path to the mc config file
- flow: path to the flow config file
- plots: path to the plots config file
- o: output directory
- eras: list of eras to process

If the config file contains a function that return the needed object you can set the arguments of the function with the following syntax  `--option:arg1=value1,arg2=value2` (you can use keyword arguments only)

e.g. `--flow flows/flow.py:region=\"Signal\",Eleptcut=5`

---
The CLI will print on the terminal:
- A table containing the mainm configurations (eras, ncpu, etc.)
- The list of data and MC paths for all the eras (also for friends)
- A table with all the processes, the samples, the cross-sections and the preselection strings
- The list of steps of the MCC
- The list of steps of the Flow
- The RDataFrame logging
- For each process a table with all the cuts with the yields, relative efficiencies and cumulative efficiencies


---
In the outfolder, the CLI will save:
- The CMGRDF output (index.php to visualize plots on webeos, pdf and png plots, txt with yields for each plot, hist saved in root file)
- a cards folder with Combine datacards for each plot and root input files (if runned with `--datacards`)
- A log folder that contains:
    - `cache` folder that contains the cache of the analysis (for rerunning it faster) (enabled by default)
    - `report.txt` A file that contains the terminal output of the CLI
    - `cmgrdf_commit.txt` A file that contains the commit hash of the CMGRDF used to runned the analysis and (if in a dirty state), the git diff
    - All the files needed to rerun the analysis (not all the files in the repo, just the one you need)
    - `command.sh` A bash command that check if you are running with the same CMGRDF version (otherwise it will warn you) and rerun the same analysis


> To visualize correctly `report.txt` on WEBEOS you have to add `AddDefaultCharset utf-8` to your .htaccess