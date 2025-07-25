from cmgrdf_cli.data import cms10

all_processes={
    "InclusiveMinBias" : {
        "groups" : [
            {
            "name": "InclusiveMinBias",
            "samples": {
                "InclusiveMinBias":
                    {
                    "xsec": None,
                    "path" : "backgroundSamples/noskim_allnanoColl/InclusiveDileptonMinBias_TuneCP5Plus_13p6TeV_pythia8/crab_InclusiveDileptonMinBias_noskim_allnano/250416_084854/InclusiveDileptonMinBias_2022_noskim_allnano.root",
                    },
                },
            "genWeightName": None,
            "weight": "1",
            "cut":"1",
            },
        ],
        "signal": True,
        "label": "MinBias",
        "color": cms10[0],
    },
}