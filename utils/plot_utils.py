import os
import multiprocessing as mp
import uproot

from utils.plotters import TH1, TH2
from utils import folders

#TODO add data
#TODO add ratioplot
def _drawPyPlots(path, all_processes, plot, plot_lumi, cmstext, lumitext):
    if "{lumi" in lumitext:
        lumitext = lumitext.format(lumi=plot_lumi)
    density = getattr(plot, "density", False)
    log = getattr(plot, "log", "")
    file = uproot.open(path)
    hist_type = str(type(file[list(all_processes.keys())[0]]))
    if "TH1" in hist_type:
        h = TH1(cmstext = cmstext,
                lumitext= lumitext,
                xlabel = plot.xlabel,
                ylabel = "Density" if density else "Events",
                log = log)
        for process_name, process_dict in all_processes.items():
            #TODO handle stack e signal no signal + total shaded uncertainties
            hist = file[process_name].to_hist()
            color = process_dict.get("color", None)
            h.add(hist, label=process_dict["label"], density = density, color = color)
        h.save(f"{path.replace('.root','.png')}")
        h.save(f"{path.replace('.root','.pdf')}")
    elif "TH2" in hist_type:
        for process_name, process_dict in all_processes.items():
            h = TH2(cmstext = cmstext,
                    lumitext= lumitext,
                    xlabel = plot.xlabel,
                    ylabel = plot.ylabel,
                    log = log)
            hist = file[process_name].to_hist()
            h.add(hist, density = density)
            folder = path.replace('.root','')
            folder = folder.rsplit('/',1)[0]+"/2D_"+folder.rsplit('/',1)[1]
            os.makedirs(folder, exist_ok=True)
            os.system(f"cp $CMGRDF/externals/index.php {folder}")
            h.save(os.path.join(folder,f"{process_name}.png"))
            h.save(os.path.join(folder,f"{process_name}.pdf"))


def DrawPyPlots(plots_lumi, flow_plots, all_processes, cmstext, lumitext, ncpu=16):
    paths=[f"{folders.outfolder}/{flow}/{plot.name}.root" for (flow, plots) in flow_plots for plot in plots]
    plots = [plot for (_, plots) in flow_plots for plot in plots]
    pool_data=[(path, all_processes, plot, plot_lumi, cmstext, lumitext) for path, plot, plot_lumi in zip(paths, plots, plots_lumi)]
    p=mp.Pool(ncpu)
    p.starmap(_drawPyPlots, pool_data)