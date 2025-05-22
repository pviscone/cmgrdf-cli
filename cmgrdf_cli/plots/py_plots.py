import os
import glob
import concurrent
import traceback
import uproot
import matplotlib.pyplot as plt
from plothist import plot_comparison
from cmgrdf_cli.plots.plotters import TH1, TH2
from cmgrdf_cli.utils.folders import folders

from mplhep import error_estimation
import numpy as np

#!Have to manually compute yerr because mplhep w2method callable is broken
def poisson_interval_ignore_empty(sumw, sumw2):
    #Set to 0 yerr of empty bins
    interval = error_estimation.poisson_interval(sumw, sumw2)
    lo, hi = interval[0,...], interval[1,...]
    to_ignore = np.isnan(lo)
    lo[to_ignore] = 0.0
    hi[to_ignore] = 0.0
    res = np.array([lo,hi])
    return np.abs(res - sumw)

def parse_hist_file(file):
    bkgs = [process_name for process_name, process_dict in all_processes.items() if not process_dict.get("signal", False)]
    signals = [process_name for process_name, process_dict in all_processes.items() if process_dict.get("signal", False)]
    data_hist = file.get("data", False)
    if data_hist:
        data_hist = data_hist.to_hist()
    return data_hist, bkgs, signals

def plot_th1(fig, ax, file, plot, data_hist):
    h = TH1(cmstext = cmstext,
        lumitext= lumitext,
        xlabel = plot.xlabel if not doRatio else None,
        ylabel = "Density" if getattr(plot, "density", False) else "Events",
        log = getattr(plot, "log", ""),
        fig = fig,
        ax = ax[0],
        grid=grid,
        ylim = getattr(plot, "ylim", None),
        xlim = getattr(plot, "xlim", None)
    )

    if data_hist:
        yerr = poisson_interval_ignore_empty(data_hist.values(), data_hist.variances())
        h.add(data_hist, label="Data", density = getattr(plot, "density", False), color = "black", histtype = "errorbar", yerr=yerr)

    for process_name, process_dict in all_processes.items():
        if process_name not in file:
            continue
        hist = file[process_name].to_hist()
        color = process_dict.get("color", None)
        plot_kwargs = process_dict.get("plot_kwargs", {})
        yerr=poisson_interval_ignore_empty(hist.values(), hist.variances())
        h.add(hist, label=process_dict["label"], density = getattr(plot, "density", False), color = color, yerr=yerr, **plot_kwargs)
    return h

def plot_stack(fig, ax, file, plot, data_hist, bkgs, signals):
    h = TH1(cmstext = cmstext,
        lumitext= lumitext,
        xlabel = plot.xlabel if not doRatio else None,
        ylabel = "Density" if getattr(plot, "density", False) else "Events",
        log = getattr(plot, "log", ""),
        fig = fig,
        ax = ax[0],
        grid=grid,
        ylim = getattr(plot, "ylim", None),
        xlim = getattr(plot, "xlim", None)
    )

    if data_hist:
        yerr = poisson_interval_ignore_empty(data_hist.values(), data_hist.variances())
        h.add(data_hist, label="Data", density = getattr(plot, "density", False), color = "black", histtype = "errorbar", yerr=yerr)

    bkg_hist = [file[bkg].to_hist() for bkg in bkgs if bkg in file]
    bkg_labels = [all_processes[bkg]["label"] for bkg in bkgs if bkg in file]
    bkg_colors = [all_processes[bkg].get("color", None) for bkg in bkgs if bkg in file]

    signal_hist = [file[signal].to_hist() for signal in signals if signal in file]
    signal_labels = [all_processes[signal]["label"] for signal in signals if signal in file]
    signal_colors = [all_processes[signal].get("color", None) for signal in signals if signal in file]

    stack_total = sum(bkg_hist)
    if stackSignal:
        stack_total = stack_total + sum(signal_hist)
    h.add(bkg_hist, label=bkg_labels, density = getattr(plot, "density", False), color = bkg_colors, stack = True, histtype = "fill")
    signal_histtype = "step" if not stackSignal else "fill"
    yerr_signal = [poisson_interval_ignore_empty(hist.values(), hist.variances()) for hist in signal_hist]
    h.add(signal_hist, label=signal_labels, density = getattr(plot, "density", False), color = signal_colors, stack = stackSignal, histtype = signal_histtype, yerr=yerr_signal)
    h.add(stack_total, density = getattr(plot, "density", False), color = "black", histtype = "step", yerr=False, linewidth=1)
    yerr_total = poisson_interval_ignore_empty(stack_total.values(), stack_total.variances())
    h.add(stack_total, density = getattr(plot, "density", False), color = "black", histtype = "band", label="Total Unc.", yerr=yerr_total)
    return h, stack_total

def plot_ratio(ax, file, plot, stack_total):
    if "total" in ratio:
        assert stack_total is not None, "stack_total is None, cannot plot ratio"

    if ratio[0]=="total":
        num_ratio = stack_total
    else:
        num_ratio = file[ratio[0]].to_hist()
    if ratio[1]=="total":
        den_ratio = stack_total
    else:
        den_ratio = file[ratio[1]].to_hist()
    if getattr(plot, "density", False):
        num_ratio = num_ratio/num_ratio.integrate(0).value
        den_ratio = den_ratio/den_ratio.integrate(0).value

    plt.setp(ax[0].get_yticklabels()[0], visible=False)
    ax[0].set_xlabel("")
    plot_comparison(
        num_ratio,
        den_ratio,
        xlabel=plot.xlabel,
        comparison=ratiotype,
        ax=ax[1],
        h1_label=ratio[0],
        h2_label=ratio[1],
        comparison_ylim = ratiorange
        )
    return ax

# plot single process
def plot_th2(file, plot, process_name):
    h = TH2(cmstext = cmstext,
            lumitext= lumitext,
            xlabel = plot.xlabel,
            ylabel = plot.ylabel,
            log = getattr(plot, "log", ""),
            xlim = getattr(plot, "xlim", None),
            ylim = getattr(plot, "ylim", None),
            zlim = getattr(plot, "zlim", None),
            grid=grid)
    hist = file[process_name].to_hist()
    h.add(hist, density = getattr(plot, "density", False))
    return h

def save_plot1D(h, path):
    pdf_Path = path.replace('.root','.pdf')
    png_Path = path.replace('.root','')
    h.save(f"{pdf_Path}")
    os.system(f"(pdftocairo {pdf_Path} -png -r 200 {png_Path} & wait; mv {png_Path}-1.png {png_Path}.png) &")

def save_plot2D(h, path, process_name):
    folder = path.replace('.root','')
    folder2D = os.path.join(folder.rsplit('/',1)[0],"2D/")
    folder = os.path.join(folder2D, folder.rsplit('/',1)[1])
    os.makedirs(folder, exist_ok=True)
    h.save(os.path.join(folder,f"{process_name}.pdf"))
    os.system(f"(pdftocairo {os.path.join(folder,f'{process_name}.pdf')} -png -r 200 {os.path.join(folder,f'{process_name}')} & wait; mv {os.path.join(folder,f'{process_name}-1.png')} {os.path.join(folder,f'{process_name}.png')}) &")

def __drawPyPlots(path, plot, plot_lumi):
    global all_processes, lumitext, noStack, doRatio, ratio, era
    try:
        lumitext = original_lumitext.format(lumi=plot_lumi, era=era)
        file = uproot.open(path)
        hist_type = str(type(file[list(all_processes.keys())[0]]))
        if "TH1" in hist_type:
            fig, ax = None ,[None, None]
            data_hist, bkgs, signals = parse_hist_file(file)

            if (doRatio and
                ("data" in ratio and "data" not in file) or
                ("total" in ratio and noStack) or
                (ratio[0] not in file and ratio[0] != "total") or
                (ratio[1] not in file and ratio[1] != "total")
                ):
                doRatio = False

            if doRatio:
                fig, ax =plt.subplots(2, 1, gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.}, sharex=True)

            if noStack or len(bkgs) == 0:
                h = plot_th1(fig, ax, file, plot, data_hist)
                stack_total = None
            else:
                h, stack_total = plot_stack(fig, ax, file, plot, data_hist, bkgs, signals)

            if doRatio:
                ax = plot_ratio(ax, file, plot, stack_total)
            save_plot1D(h, path)

        elif "TH2" in hist_type:
            for process_name, process_dict in all_processes.items():
                if process_name not in file:
                    continue
                h = plot_th2(file, plot, process_name)
                save_plot2D(h, path, process_name)
    except Exception as e:
        print(f"Error in {path}: {e}")
        print(traceback.format_exc())


def _drawPyPlots(args):
    return __drawPyPlots(*args)

def _drawPyPlotsInitializer(all_processes_, cmstext_, lumitext_, noStack_, doRatio_, ratio_, ratiorange_, ratiotype_, grid_, stackSignal_, era_):
    global all_processes, cmstext, original_lumitext, lumitext, noStack, doRatio, ratio, ratiorange, ratiotype, grid, stackSignal, era
    all_processes = all_processes_
    cmstext = cmstext_
    lumitext = lumitext_
    original_lumitext = lumitext_
    noStack = noStack_
    doRatio = doRatio_
    ratio = ratio_
    ratiorange = ratiorange_
    ratiotype = ratiotype_
    grid = grid_
    stackSignal = stackSignal_
    era = era_

def DrawPyPlots(plots_lumi, eras, mergeEras, flow_plots, all_processes, cmstext, lumitext, noStack, doRatio, ratio, ratiorange, ratiotype, grid=False, ncpu=None, stackSignal=False):
    for era in eras:
        format_dict = {"era": era}
        if mergeEras:
            format_dict = {}
            era = eras.__str__()
        paths=[os.path.join(folders.plots_path.format(flow=flow, **format_dict), f"{plot.name}.root") for (flow, plots) in flow_plots for plot in plots]
        plots = [plot for (_, plots) in flow_plots for plot in plots]
        pool_data=[(path, plot, plot_lumi) for path, plot, plot_lumi in zip(paths, plots, plots_lumi)]
        if ncpu>1:
            with concurrent.futures.ProcessPoolExecutor(max_workers=ncpu, initializer = _drawPyPlotsInitializer, initargs=(all_processes, cmstext, lumitext, noStack, doRatio, ratio, ratiorange, ratiotype, grid, stackSignal, era)) as executor:
                chunksize = len(pool_data)//ncpu if len(pool_data)//ncpu > 0 else 1
                list(executor.map(_drawPyPlots, pool_data, chunksize = chunksize))
        elif ncpu==1:
            for data in pool_data:
                _drawPyPlotsInitializer(all_processes, cmstext, lumitext, noStack, doRatio, ratio, ratiorange, ratiotype, grid, stackSignal, era)
                _drawPyPlots(data)
        else:
            raise ValueError("ncpu must be greater than 0")

        for flow,_ in flow_plots:
            if len(glob.glob(os.path.join(folders.plots_path.format(flow=flow, **format_dict), '*_vs_*.root'))) > 0:
                os.system(f"mv {os.path.join(folders.plots_path.format(flow=flow, **format_dict), '*_vs_*.root')} {os.path.join(folders.plots_path.format(flow=flow, **format_dict), '2D/')}")

            if len(glob.glob(os.path.join(folders.plots_path.format(flow=flow, **format_dict), '*_vs_*_vs_*.root'))) > 0:
                os.makedirs(os.path.join(folders.plots_path.format(flow=flow, **format_dict), '3D/'), exist_ok=True)
                os.system(f"mv {os.path.join(folders.plots_path.format(flow=flow, **format_dict), '*_vs_*_vs_*.root')} {os.path.join(folders.plots_path.format(flow=flow, **format_dict), '3D/')}")

        if mergeEras:
            break

