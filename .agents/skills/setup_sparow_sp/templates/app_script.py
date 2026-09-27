#
# sparow application definition.
#
# Handed to setup-sparow-sp, which copies it into the generated package (or
# loads it in place with -e) and calls create_sp() with the scenario data:
#
#     setup-sparow-sp this_file.py -n my_sp -s scenarios.json
#
# The command requires create_sp(scenario_data), and must be able to import
# this file on its own, so keep it self-contained: import model directories
# copied with -m or --scenario-models inside functions, not at the top.
#

import pyomo.environ as pyo

from sparow.sp import stochastic_program


#: Parameters constant across every scenario.  Keys must not collide with keys
#: in the scenario file's "data" block or in any scenario entry; the command
#: checks that for you as long as this dict is named APP_DATA.
APP_DATA = {
    "c": 1.0,
    "b": 1.5,
}

#: Pyomo CUID patterns naming the first-stage (non-anticipative) variables.
FIRST_STAGE_VARIABLES = [
    "x",
]


def scenario_builder(data, args):
    """
    Build the Pyomo model for a single scenario.

    Parameters
    ----------
    data : dict
        The merge, in order, of APP_DATA, the scenario file's "data" block, and
        the scenario's own entry.  `data["ID"]` names the scenario.
    args : dict
        Always empty.

    With a model directory copied into the generated package, import it
    relative to that package instead of building the model inline::

        model = importlib.import_module(".model", __package__)         # -m
        model = importlib.import_module("." + data["ID"], __package__)  # --scenario-models
        return model.create_model(alpha=data["alpha"])

    Returns
    -------
    pyomo.ConcreteModel
    """
    M = pyo.ConcreteModel()
    M.x = pyo.Var(within=pyo.NonNegativeReals)
    M.y = pyo.Var(within=pyo.NonNegativeReals)
    M.sold = pyo.Constraint(expr=M.y <= M.x)
    M.limit = pyo.Constraint(expr=M.y <= data["demand"])
    M.cost = pyo.Objective(expr=data["c"] * M.x - data["b"] * M.y, sense=pyo.minimize)
    return M


def create_sp(scenario_data):
    """
    Build the stochastic program.

    Parameters
    ----------
    scenario_data : dict
        The parsed scenario data file, read by the generated package.

    Returns
    -------
    StochasticProgram_Pyomo_NamedBuilder
    """
    sp = stochastic_program(first_stage_variables=FIRST_STAGE_VARIABLES)
    sp.initialize_application(app_data=APP_DATA)
    # Keep the keyword as model_builder=; sparow ignores unknown keywords.
    sp.initialize_model(model_data=scenario_data, model_builder=scenario_builder)
    return sp


# Optional, used only with --scenario-models: called at generate time once per
# scenario, with the working directory set to that scenario's copy of the model
# directory.  `name` is the scenario ID and `data` its entry in the scenario
# file.
#
# def customize_scenario(name, data):
#     with open("params.py", "w") as fp:
#         fp.write(f"DEMAND = {data['demand']!r}\n")
