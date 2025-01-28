
#%%
import sys
import os
import uproot
import glob
sys.path.append("/afs/.cern.ch/work/p/pviscone/Analysis/dp-ee-main/scripts/utils")
from plotters import TEfficiency, TH1
import multiprocessing as mp

#%%
#! ---------------------- Settings ---------------------- #
folder = "/eos/user/p/pviscone/www/dpee/efficiencyTree/"
php_plots = "/afs/.cern.ch/work/p/pviscone/Analysis/dp-ee-main/cmgrdf-prototype/externals/index.php"
ncpu=16

os.system(f"cp {php_plots} {folder}")

var_labels={"GenEleLead_pt":"Gen $p_T^{lead.}$ [GeV]",
            "GenEleSubLead_pt":"Gen $p_T^{sublead.}$ [GeV]",
            "GenEleLead_eta":"Gen $\eta^{lead.}$",
            "GenEleSubLead_eta":"Gen $\eta^{sublead.}$",
            "GenZd_invMass":"Gen $m_{ee}$ [GeV]",
            "GenZd_invPt":"Gen $p_T^{ee}$ [GeV]",
}

sample_labels = {
    "HAHM_13p6TeV_M5": "ZdM5",
    "HAHM_13p6TeV_M3p1": "ZdM3p1",
    "HAHM_13p6TeV_M1": "ZdM1",
}

replace = True

#%%
#! ---------------------- Efficiency ---------------------- #

denom_nums ={
    "0common_0_NoCut": [
        ("NoCut",{
            "0common_1_GenMatch": "GenMatched",
            "SelPFPF_postSelectionCuts_2_SelPFPF": "PF-PF",
            "SelPFLP_postSelectionCuts_2_SelPFLP": "PF-LP",
            "SelLPLP_postSelectionCuts_2_SelLPLP": "LP-LP",
        }),
        ("NoCutPFPF",{
            "0common_1_GenMatch": "GenMatched",
            "SelPFPF_postSelectionCuts_2_SelPFPF": "PF-PF",
            "SelPFPF_postSelectionCuts_3_dZ": "$dZ \leq 1cm$",
            "SelPFPF_postSelectionCuts_4_QF": "$SV_prov > 1e-5$, $SV_{\chi^2} < 998$",
            "SelPFPF_postSelectionCuts_5_HLT": "HLT OR",
            "SelPFPF_postSelectionCuts_6_TrgObjMatch": "TrgObjMatch",
        }),
        ("NoCutPFLP",{
            "0common_1_GenMatch": "GenMatched",
            "SelPFLP_postSelectionCuts_2_SelPFLP": "PF-LP",
            "SelPFLP_postSelectionCuts_3_dZ": "$dZ \leq 1cm$",
            "SelPFLP_postSelectionCuts_4_QF": "$SV_prov > 1e-5$, $SV_{\chi^2} < 998$",
            "SelPFLP_postSelectionCuts_5_HLT": "HLT OR",
            "SelPFLP_postSelectionCuts_6_TrgObjMatch": "TrgObjMatch",
        }),
        ("NoCutLPLP",{
            "0common_1_GenMatch": "GenMatched",
            "SelLPLP_postSelectionCuts_2_SelLPLP": "LP-LP",
            "SelLPLP_postSelectionCuts_3_dZ": "$dZ \leq 1cm$",
            "SelLPLP_postSelectionCuts_4_QF": "$SV_prov > 1e-5$, $SV_{\chi^2} < 998$",
            "SelLPLP_postSelectionCuts_5_HLT": "HLT OR",
            "SelLPLP_postSelectionCuts_6_TrgObjMatch": "TrgObjMatch",
        })
    ],
    "0common_1_GenMatch": [
        ("GenMatch",{
            "SelPFPF_postSelectionCuts_2_SelPFPF": "PF-PF",
            "SelPFLP_postSelectionCuts_2_SelPFLP": "PF-LP",
            "SelLPLP_postSelectionCuts_2_SelLPLP": "LP-LP",
        }),
        ("GenMatch_PFPF",{
            "SelPFPF_postSelectionCuts_2_SelPFPF": "PF-PF",
            "SelPFPF_postSelectionCuts_3_dZ": "$dZ \leq 1cm$",
            "SelPFPF_postSelectionCuts_4_QF": "$SV_prov > 1e-5$, $SV_{\chi^2} < 998$",
            "SelPFPF_postSelectionCuts_5_HLT": "HLT OR",
            "SelPFPF_postSelectionCuts_6_TrgObjMatch": "TrgObjMatch",
        }),
        ("GenMatch_PFLP",{
            "SelPFLP_postSelectionCuts_2_SelPFLP": "PF-LP",
            "SelPFLP_postSelectionCuts_3_dZ": "$dZ \leq 1cm$",
            "SelPFLP_postSelectionCuts_4_QF": "$SV_prov > 1e-5$, $SV_{\chi^2} < 998$",
            "SelPFLP_postSelectionCuts_5_HLT": "HLT OR",
            "SelPFLP_postSelectionCuts_6_TrgObjMatch": "TrgObjMatch",
        }),
        ("GenMatch_LPLP",{
            "SelLPLP_postSelectionCuts_2_SelLPLP": "LP-LP",
            "SelLPLP_postSelectionCuts_3_dZ": "$dZ \leq 1cm$",
            "SelLPLP_postSelectionCuts_4_QF": "$SV_prov > 1e-5$, $SV_{\chi^2} < 998$",
            "SelLPLP_postSelectionCuts_5_HLT": "HLT OR",
            "SelLPLP_postSelectionCuts_6_TrgObjMatch": "TrgObjMatch",
        })
    ]
}

teff_kwargs = {
    "rebin": 2,
    "ylim": [0,1.1],
    "legend_kwargs": {"bbox_to_anchor":(0.5, -0.225),"loc":"lower center", "ncol":3, "fontsize":15}
}

def eff_plot(data):
    denom, denom_label, num_dict, variable = data
    os.makedirs(os.path.join(folder,f'zeff/{variable}_{denom_label}'), exist_ok=True)
    os.system(f"cp {php_plots} {os.path.join(folder,f'zeff/{variable}_{denom_label}')}")
    var_label = var_labels.get(variable,variable)
    denom_file = uproot.open(f"{folder}{denom}/{variable}.root")
    samples = [s.split(";")[0] for s in denom_file.keys() if "_total" not in s and "_stack" not in s and "_canvas" not in s]
    for sample in samples:
        if not replace and f"{os.path.join(folder,f'zeff/{variable}_{denom_label}/{sample}')}.png" in glob.glob(f"{os.path.join(folder,f'zeff/{variable}_{denom_label}')}/*"):
            continue
        sample_label = sample_labels.get(sample.replace(";1",""),sample.replace(";1",""))
        denom_h = denom_file[sample].to_hist()
        eff = TEfficiency(xlabel=var_label, cmstext="Preliminary", lumitext=f"{sample_label} ({denom_label})", **teff_kwargs)
        for num, num_label in num_dict.items():
            num_h = uproot.open(f"{folder}{num}/{variable}.root")[sample].to_hist()
            eff.add(num_h, denom_h, label=num_label)
        eff.save(f"{os.path.join(folder,f'zeff/{variable}_{denom_label}/{sample}')}.png")
        eff.save(f"{os.path.join(folder,f'zeff/{variable}_{denom_label}/{sample}')}.pdf")

pool_data=[]
os.makedirs(f"{folder}/zeff", exist_ok=True)
for denom, eff_list in denom_nums.items():
    for tup in eff_list:
        denom_label, num_dict = tup
        variables = glob.glob(f"{folder}{denom}/*.root")
        variables = [v.split("/")[-1].split(".root")[0] for v in variables]
        for variable in variables:
            pool_data.append([denom, denom_label, num_dict, variable])

p=mp.Pool(ncpu)
p.map(eff_plot, pool_data)


#%%
#! ---------------------- Replace root plots---------------- #

th_kwargs = {
    "rebin": 1,
    "ylabel": "Events",
}

def replace_plots(path):
    file = uproot.open(path)
    keys = file.keys()
    var_from_path = path.split("/")[-1].split(".root")[0]
    h = TH1(xlabel=var_labels.get(var_from_path, var_from_path), cmstext="Preliminary", **th_kwargs)
    for sample in keys:
        if "_total" not in sample and "_stack" not in sample and "_canvas" not in sample:
            hist = file[sample].to_hist()
            h.add(hist, label=sample_labels.get(sample.split(";")[0], sample.split(";")[0]))
    h.save(f"{path.replace('.root','.png')}")
    h.save(f"{path.replace('.root','.pdf')}")

pool_data=[]
for path in glob.glob(f"{folder}/*/*.root"):
    if not replace and f"{path.replace('.root','.png')}" in glob.glob(f"{path.rsplit('/',1)[0]}/*"):
        continue
    pool_data.append(path)

p=mp.Pool(ncpu)
p.map(replace_plots, pool_data)
# %%

#! ---------------------- Normalized plots ---------------- #

norm_th_kwargs = {
    "rebin": 1,
    "ylabel": "Density",
}

def norm_plot(data):
    path, new_path = data
    file = uproot.open(path)
    keys = file.keys()
    var_from_path = path.split("/")[-1].split(".root")[0]
    h = TH1(xlabel=var_labels.get(var_from_path, var_from_path), cmstext="Preliminary", **norm_th_kwargs)
    for sample in keys:
        if "_total" not in sample and "_stack" not in sample and "_canvas" not in sample:
            hist = file[sample].to_hist()
            h.add(hist, label=sample_labels.get(sample.split(";")[0], sample.split(";")[0]), density=True)

    h.save(f"{new_path.replace('.root','.png')}")
    h.save(f"{new_path.replace('.root','.pdf')}")

pool_data=[]
for path in glob.glob(f"{folder}/*/*.root"):
    norm_path = f"{path.rsplit('/',1)[0]}/normalized/"
    os.makedirs(norm_path, exist_ok=True)
    os.system(f"cp {php_plots} {norm_path}")
    new_path = os.path.join(norm_path, path.rsplit("/",1)[1])
    if not replace and f"{new_path.replace('.root','.png')}" in glob.glob(f"{new_path.rsplit('/',1)[0]}/*"):
        continue
    pool_data.append([path, new_path])

p=mp.Pool(ncpu)
p.map(norm_plot, pool_data)

# %%
#! ---------------------- log plots ---------------- #

norm_th_kwargs = {
    "rebin": 1,
    "ylabel": "Events",
    "log": "y",
}

def log_plot(data):
    path, new_path = data
    file = uproot.open(path)
    keys = file.keys()
    var_from_path = path.split("/")[-1].split(".root")[0]
    h = TH1(xlabel=var_labels.get(var_from_path, var_from_path), cmstext="Preliminary", **norm_th_kwargs)
    for sample in keys:
        if "_total" not in sample and "_stack" not in sample and "_canvas" not in sample:
            hist = file[sample].to_hist()
            h.add(hist, label=sample_labels.get(sample.split(";")[0], sample.split(";")[0]))
    h.save(f"{new_path.replace('.root','.png')}")
    h.save(f"{new_path.replace('.root','.pdf')}")

pool_data=[]
for path in glob.glob(f"{folder}/*/*.root"):
    norm_path = f"{path.rsplit('/',1)[0]}/logscale/"
    os.makedirs(norm_path, exist_ok=True)
    os.system(f"cp {php_plots} {norm_path}")
    new_path = os.path.join(norm_path, path.rsplit("/",1)[1])
    if not replace and f"{new_path.replace('.root','.png')}" in glob.glob(f"{new_path.rsplit('/',1)[0]}/*"):
        continue
    pool_data.append([path, new_path])

p=mp.Pool(ncpu)
p.map(log_plot, pool_data)

# %%
#! ---------------------- Normalized log plots ---------------- #

norm_th_kwargs = {
    "rebin": 1,
    "ylabel": "Density",
    "log": "y",
}

def norm_log(data):
    path, new_path = data
    file = uproot.open(path)
    keys = file.keys()
    var_from_path = path.split("/")[-1].split(".root")[0]
    h = TH1(xlabel=var_labels.get(var_from_path, var_from_path), cmstext="Preliminary", **norm_th_kwargs)
    for sample in keys:
        if "_total" not in sample and "_stack" not in sample and "_canvas" not in sample:
            hist = file[sample].to_hist()
            h.add(hist, label=sample_labels.get(sample.split(";")[0], sample.split(";")[0]), density=True)

    h.save(f"{new_path.replace('.root','.png')}")
    h.save(f"{new_path.replace('.root','.pdf')}")

pool_data=[]
for path in glob.glob(f"{folder}/*/*.root"):
    norm_path = f"{path.rsplit('/',1)[0]}/normalizedlog/"
    os.makedirs(norm_path, exist_ok=True)
    os.system(f"cp {php_plots} {norm_path}")
    new_path = os.path.join(norm_path, path.rsplit("/",1)[1])
    if not replace and f"{new_path.replace('.root','.png')}" in glob.glob(f"{new_path.rsplit('/',1)[0]}/*"):
        continue
    pool_data.append([path,new_path])

p=mp.Pool(ncpu)
p.map(norm_log, pool_data)



