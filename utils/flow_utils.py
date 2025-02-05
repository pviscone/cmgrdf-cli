from rich.table import Table
from CMGRDF import Flow, Cut
from CMGRDF.flow import FlowStep
from utils.cli_utils import load_module, parse_function
from utils.folders import folders
from flows import Tree
import copy
import re


def split_at_plot(flow_obj, plots_dict):
    flow_list = []

    plotted_steps = 0
    for step_idx, flow_step in enumerate(flow_obj):
        if getattr(flow_step, "plot", False):
            assert isinstance(flow_step.plot, str)
            flow_name = flow_obj.name + f"_{plotted_steps}"
            flow_name += f"_{flow_step.plot}"
            plotted_steps += 1
            flow_list.append(Flow(flow_name, flow_obj[: step_idx + 1]))
    if plotted_steps == 0: #if there are no plotsteps append all
        flow_list.append(flow_obj)
    elif len(flow_list[-1].steps) < len(flow_obj.steps): #append the rest of the steps il last flowstep does not have plot argument
        flow_list.append(Flow(f"{flow_obj.name}_{plotted_steps}_full", flow_obj.steps))
    plot_list = [[] for _ in range(len(flow_list))]
    for idx in range(len(flow_list)):
        rematch = re.match("(.*)_(\d+)_(.*)", flow_list[idx].name)
        if idx == 0 and "main" in plots_dict:
            plot_list[idx]=copy.deepcopy(plots_dict["main"])
        elif idx>0:
            plot_list[idx] = copy.deepcopy(plot_list[idx-1])
        if bool(rematch) and rematch.group(3) in plots_dict:
            plot_list[idx]+=plots_dict[rematch.group(3)]
    return flow_list, plot_list #single leaf. list of flow for each plotstep. list of list of Plot to plot at each plotstep


def parse_flows(console, flow_config, plots_dict, enable=[""], disable=[""], noPlotsteps=False):
    assert enable==[""] or disable==[""], "Cannot enable and disable at the same time"

    isBranched=False
    flow_table = Table(title="Flows", show_header=True, header_style="bold black")
    flow_table.add_column("Configs", style="bold red")
    flow_table.add_column("Name")
    if flow_config is not None:
        flow_module, flow_kwargs = load_module(flow_config)
        try:
            flow_obj = parse_function(flow_module, "flow", Flow, kwargs=flow_kwargs)
            t = Tree()
            t.add("base", flow_obj.steps)
            flow_obj=t
        except ValueError:
            flow_obj = parse_function(flow_module, "flow", Tree, kwargs=flow_kwargs)

        isBranched = True if any([len(s.children)>1 for _, s in flow_obj.segments.items()]) else False
        flows_dict = flow_obj.to_dict() # leaf:steps
        if enable!=[""] or disable!=[""]:
            new_flows_dict = {}
            for name in flows_dict:
                if enable!=[""]:
                    for en_pattern in enable:
                        if re.search(en_pattern, name):
                            new_flows_dict[name] = flows_dict[name]
                if disable!=[""]:
                    for dis_pattern in disable:
                        if not re.search(dis_pattern, name):
                            new_flows_dict[name] = flows_dict[name]
            flows_dict = new_flows_dict
        for name in flows_dict:
            flow_table.add_row(flow_config, name)
        flow_obj.graphviz(f"{folders.outfolder}/verbose_tree")
        flow_obj.graphviz(f"{folders.outfolder}/tree", clean_fn=lambda x : re.sub(r"\n\tonMC.*(True|False)","", x))     #Remove onData/onMC/onDataDriven info
        flow_obj.graphviz(f"{folders.outfolder}/cut_tree", clean_fn=lambda x : x.split("\n")[0]+"\n\n"+"\n\n".join([b for b in re.sub(r"\n\tonMC.*(True|False)","", x).split("\n\n") if bool(re.search("(.|\t)\d+\. Cut\(.*(.|\n)",b))])) #Cuts only
        console.print(flow_table)

        #list of list of flows. [i][j] i is leaf, j is plotstep
        region_flows=[]
        region_plots=[]
        for name, steps in flows_dict.items():
            flow_list, p_list = split_at_plot(Flow(name, steps), plots_dict)
            region_flows.append(flow_list)
            region_plots.append(p_list)
        return region_flows, region_plots, isBranched
    else:
        return [[Flow("empty", Cut("empty", "1"))]], [[]], isBranched


def get_identical_elem_idxs(region_flows):
    index_map = {}
    nleafs = len(region_flows)
    for row_index  in range(nleafs):
        nplotsteps = len(region_flows[row_index])
        for col_index  in range(nplotsteps):
            key = (region_flows[row_index][col_index].steps).__str__()
            if key in index_map:
                index_map[key].append((row_index, col_index))
            else:
                index_map[key] = [(row_index, col_index)]
    return {key: value for key, value in index_map.items() if len(value) > 1}

def _clean_commons(region_obj, elem_idxs, flows=False):
    nleafs = len(region_obj)
    new_region_obj = [[] for _ in range(nleafs)]
    common_idx = 0
    common_idx_dict = {}
    for _, key in enumerate(elem_idxs.keys()):
        idxs = elem_idxs[key]
        common_leafs = tuple([i for i,_ in idxs])
        if common_leafs not in common_idx_dict:
            common_idx_dict[common_leafs]=common_idx
            common_idx +=1
    common_flows = [[] for _ in range(len(common_idx_dict))]
    for _, key in enumerate(elem_idxs.keys()):
        idxs = elem_idxs[key]
        common_leafs = tuple([i for i,_ in idxs])
        common_obj = region_obj[idxs[0][0]][idxs[0][1]]
        if flows:
            name = common_obj.name
            re_match = re.search(r"_(\d+)_", name)
            new_name = f"{common_idx_dict[common_leafs]}common{re_match.group(0)}{name[re_match.end():]}" if re_match else f"{common_idx_dict[common_leafs]}common_{name}"
            common_flows[common_idx_dict[common_leafs]].append(Flow(new_name, common_obj.steps))
        else:
            common_flows[common_idx_dict[common_leafs]].append(common_obj)
    flat_idxs = [elem_idxs[key] for key in elem_idxs.keys()]
    flat_idxs = [j for f in flat_idxs for j in f]
    for reg_idx, reg in enumerate(region_obj):
        for plt_idx, plt in enumerate(reg):
            if (reg_idx, plt_idx) not in flat_idxs:
                new_region_obj[reg_idx].append(region_obj[reg_idx][plt_idx])
    return [*common_flows, *new_region_obj]

def clean_commons(region_flows, region_plots):
    elem_idxs = get_identical_elem_idxs(region_flows)
    region_flows = _clean_commons(region_flows, elem_idxs, flows = True)
    region_plots = _clean_commons(region_plots, elem_idxs, flows = False)
    return region_flows, region_plots

def disable_plotflag(region_flows):
    for leaf_idx in range(len(region_flows)):
        for step_idx in range(len(region_flows[leaf_idx][0].steps)):
            region_flows[leaf_idx][0].steps[step_idx].plot=False
