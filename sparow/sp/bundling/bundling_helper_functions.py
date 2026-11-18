import warnings

"""
* specify which bundling scheme (function) is used via "bundle_scheme" in sp.py

* bundle is a dictionary of dictionaries
    - keys are names of bundles
    - each key corresponds to a dictionary, with keys:
        - 'scenarios' (i.e., which scenarios are in the bundle)
            - 'scenarios' is itself a dictionary containing keys: (model fidelity, scenario name) pairs,
               and values: model fidelity weight (if model_weight=True) or scenario probability otherwise
        - 'Probability' (the bundle probability)

* example of a multi-fidelity bundle:
    {
    "bundle_0": {
                "scenarios": {
                    ("HF", "scen_0"): 0.6,
                    ("LF", "scen_2"): 0.25,
                    ("LF", "scen_3"): 0.15,
                },
                "Probability": 0.4,
            },
    "bundle_1": {"scenarios": {
                    ("HF", "scen_1"): 0.7
                    ("LF", "scen_4"): 0.3,
                }, 
                "Probability": 0.6
            },
    }

* it is assumed that the data containing the scenario information is a dictionary
    - keys are model names (e.g., 'HF', 'LF')
    - values are themselves dictionaries
        - keys are scenario names (e.g., 'scen_0', 'scen_1')
        - values are themselves dictionaries with keys:
            - 'data': a dictionary whose keys are scenario information labels
              (e.g., 'Demand') and whose values are numerical values or lists
            - 'probability' (optional): the scenario probability

# example of data dictionary:
    {
        "HF": {
            "scen_1": {"data": {"Demand": [3, 2]}, "probability": 0.4},
            "scen_0": {"data": {"Demand": [1, 1]}, "probability": 0.6},
        },
        "LF": {
            "scen_3": {"data": {"Demand": [4, 4]}, "probability": 0.2},
            "scen_2": {"data": {"Demand": [2, 2]}, "probability": 0.8},
        },
    }
"""


"""
******************* HELPER FUNCTIONS *******************
"""


# The key used to specify scenario probabilities
PKEY = "probability"


def scen_name(model, scenario):
    if model is None:
        return f"{scenario}"
    return f"{model}_{scenario}"


def scen_key(model, scenario):
    return (model, scenario)


def check_data_dict_keys(data, model0, bundle_args, dkey_required=False):
    """
    Returns the tuple (dkey, pkey), where dkey is the scenario data key used
    by the bundling scheme (specified with the 'data_key' bundle argument) and
    pkey is the key used to specify scenario probabilities.

    Scenario probabilities are specified with the 'probability' key in each
    scenario.  If no scenarios specify a probability, then pkey is None.
    """
    dkey = None
    if bundle_args:
        dkey = bundle_args.get("data_key", None)
        if "probability_key" in bundle_args:
            raise RuntimeError(
                "The 'probability_key' bundle argument is no longer supported.  "
                "Scenario probabilities are specified with the 'probability' key "
                "of each scenario."
            )

    if dkey is None and dkey_required == True:
        raise RuntimeError(f"Specify data_key in bundle_args")

    if any(PKEY in sdata for mdata in data.values() for sdata in mdata.values()):
        pkey = PKEY
    else:
        pkey = None
        warnings.warn(
            "No scenario probabilities are given; assuming uniform distribution.",
            UserWarning,
        )

    return dkey, pkey
