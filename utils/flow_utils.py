from rich.table import Table
from CMGRDF import Flow, Cut
from CMGRDF.flow import FlowStep
from utils.cli_utils import load_module, parse_function
from flows import Tree


def split_at_plot(flow_obj):
    flow_list = []
    plotted_steps = 0
    for step_idx, flow_step in enumerate(flow_obj):
        if (
            isinstance(flow_step, FlowStep)
            and hasattr(flow_step, "plot")
            and flow_step.plot
        ):
            flow_name = flow_obj.name + f"_{plotted_steps}"
            if isinstance(flow_step.plot, str):
                flow_name += f"_{flow_step.plot}"
            plotted_steps += 1
            flow_list.append(Flow(flow_name, flow_obj[: step_idx + 1]))
    if plotted_steps == 0:
        flow_list.append(flow_obj)
    elif len(flow_list[-1].steps) < len(flow_obj.steps):
        flow_list.append(Flow(f"{flow_obj.name}_{plotted_steps}_full", flow_obj.steps))
    return flow_list


def parse_flows(console, flow_config, outfolder, enable=[""], disable=[""]):
    flow_table = Table(title="Flows", show_header=True, header_style="bold black")
    flow_table.add_column("Configs", style="bold red")
    flow_table.add_column("Name")
    if flow_config is not None:
        flow_module, flow_kwargs = load_module(flow_config)
        try:
            flow_obj = parse_function(flow_module, "flow", Tree, kwargs=flow_kwargs)
            flows_dict = flow_obj.to_dict()
            if enable!=[""]:
                flows_dict = {k: v for k, v in flows_dict.items() if k in enable}
            if disable!=[""]:
                flows_dict = {k: v for k, v in flows_dict.items() if k not in disable}
            for name in flows_dict:
                flow_table.add_row(flow_config, name)
            flow_obj.graphviz(f"{outfolder}/tree")
            return [
                split_at_plot(Flow(name, steps)) for name, steps in flows_dict.items()
            ]
        except ValueError:
            flow_obj = parse_function(flow_module, "flow", Flow, kwargs=flow_kwargs)
            flow_table.add_row(flow_config, flow_obj.name)
        console.print(flow_table)
        return [flow_obj]
    else:
        flow_obj = Flow("empty", Cut("empty", "1"))
        return [split_at_plot(flow_obj)]

def clean_commons(region_flows):
    nmin = min([len(l) for l in region_flows])
    common_flows = []
    for i in range(nmin):
        flow_i = [region[i].steps for region in region_flows]
        if all(x==flow_i[0] for x in flow_i):
            name = region_flows[0][i].name
            common_flows.append(Flow(f"0common_{name.split('_',1)[1]}", flow_i[0]))
        else:
            break
    region_flows = [region[i:] for region in region_flows]
    region_flows = [common_flows, *region_flows]
    return region_flows
