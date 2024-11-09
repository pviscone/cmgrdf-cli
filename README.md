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

### Sample definition (To review)

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


### MCC, Flows & Plots
ToExplain

### Corrections and systematics
ToExplain


# Command Line Interface

ToExplain
