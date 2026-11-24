from munch import Munch
import pyomo.environ as pyo
from sparow.sp import stochastic_program

#
# Data for a simple newsvendor example
#
common_data = dict(c=1.0, b=1.5, h=0.1)
scenario_data = {
    "HF": {
        "scenarios": [
            dict(ID="1", data={"d": 15}, probability=0.1),
            dict(ID="2", data={"d": 60}, probability=0.2),
            dict(ID="3", data={"d": 72}, probability=0.1),
            dict(ID="4", data={"d": 78}, probability=0.3),
            dict(ID="5", data={"d": 82}, probability=0.3),
        ]
    },
    "LF": {
        "data": {"B": 0.9},
        "scenarios": [
            dict(ID="1", data={"d": 15, "C": 1.4}, probability=0.05),
            dict(ID="2", data={"d": 60, "C": 1.3}, probability=0.4),
            dict(ID="3", data={"d": 72, "C": 1.2}, probability=0.1),
            dict(ID="4", data={"d": 78, "C": 1.1}, probability=0.35),
            dict(ID="5", data={"d": 82, "C": 1.0}, probability=0.1),
        ],
    },
}


#
# Function that constructs a newsvendor model
# including a single second stage
#
def HF_builder(data, args):
    # This builder matches the builder() function used with the simple_newsvendor
    # example.
    #
    # This function creates a polyhedral objective with 2 sections,
    #   which is formed by: greater and less.
    # Since there are two line segments, there can be up to one vertex.
    b = data["b"]
    c = data["c"]
    h = data["h"]
    d = data["d"]

    M = pyo.ConcreteModel(data["ID"])

    M.x = pyo.Var(within=pyo.NonNegativeReals)

    M.y = pyo.Var()
    M.greater = pyo.Constraint(expr=M.y >= (c - b) * M.x + b * d)
    M.less = pyo.Constraint(expr=M.y >= (c + h) * M.x - h * d)

    M.o = pyo.Objective(expr=M.y)

    return M


def LF_builder(data, args):
    # This function creates a polyhedral objective with 3 sections,
    #   which is formed by: greater, greaterX, and less.
    # The constraint greaterX is the new and not in the HF version.
    # Since there are three line segments, there can be up to two vertices.
    # N.B. M.greater and M.greaterX use different constants!
    #
    # Note that the objective is scaled by 2 to illustrate that the
    # low-fidelity model can differ from a high-fidelity model as long as the
    # optimal solutions are "well correlated" with the original model.
    b = data["b"]
    B = data["B"]
    c = data["c"]
    C = data["C"]
    h = data["h"]
    d = data["d"]

    M = pyo.ConcreteModel(data["ID"])

    M.x = pyo.Var(within=pyo.NonNegativeReals)

    M.y = pyo.Var()
    M.greater = pyo.Constraint(expr=M.y >= (c - b) * M.x + b * d)
    M.greaterX = pyo.Constraint(expr=M.y >= (C - B) * M.x + B * d)
    M.less = pyo.Constraint(expr=M.y >= (c + h) * M.x - h * d)

    M.o = pyo.Objective(expr=2 * M.y)

    return M


def HF_newsvendor():
    """
    A 'high fidelity' newsvendor example adapted from

    A Tutorial on Stochastic Programming
    Alexander Shapiro∗ and Andy Philpott†
    March 21, 2007
    https://www.epoc.org.nz/papers/ShapiroTutorialSP.pdf
    """
    sp = stochastic_program(first_stage_variables=["x"])
    sp.configure(common_data=common_data)
    sp.add_scenarios(name="HF", data=scenario_data["HF"], scenario_builder=HF_builder)
    return Munch(
        sp=sp,
        objective_value=80.01,
        unique_solution=True,
        solution_values={"x": 72.0, "s[HF,'1'].x": 15.0, "s[HF,'2'].x": 60.0},
    )


def LF_newsvendor():
    """
    A 'low fidelity' newsvendor example adapted from

    A Tutorial on Stochastic Programming
    Alexander Shapiro∗ and Andy Philpott†
    March 21, 2007
    https://www.epoc.org.nz/papers/ShapiroTutorialSP.pdf

    This model includes one additional constraint, using data values 'B' and 'C'.
    This constraint can change the value of the optimal solution.
    """
    sp = stochastic_program(first_stage_variables=["x"])
    sp.configure(common_data=common_data)
    sp.add_scenarios(name="LF", data=scenario_data["LF"], scenario_builder=LF_builder)
    return Munch(
        sp=sp,
        objective_value=164.67,
        unique_solution=True,
        solution_values={"x": 54.0, "s[LF,'1'].x": 9.0, "s[LF,'2'].x": 40.0},
    )


def MFrandom_newsvendor(with_bundles=False):
    """
    A multi-fidelity newsvendor example.  This example includes both low-
    and high-fidelity scenarios that are bundled using the 'random'
    bundling scheme.
    """
    sp = stochastic_program(first_stage_variables=["x"])
    sp.configure(common_data=common_data)
    sp.add_scenarios(name="HF", data=scenario_data["HF"], scenario_builder=HF_builder)
    sp.add_scenarios(
        name="LF",
        data=scenario_data["LF"],
        scenario_builder=LF_builder,
    )

    if with_bundles:
        sp.initialize_bundles(
            scheme="mf_random",
            LF=2,
            seed=1234567890,
            model_weight={"LF": 2.0, "HF": 1.0},
        )

    # NOTE: This solution is for the EF, without bundles.
    return Munch(sp=sp, objective_value=122.58, unique_solution=False)


def MFpaired_newsvendor(with_bundles=False):
    """
    A multi-fidelity newsvendor example.  This example includes both low-
    and high-fidelity scenarios that are bundled using the 'paired'
    bundling scheme.
    """
    sp = stochastic_program(first_stage_variables=["x"])
    sp.configure(common_data=common_data)
    sp.add_scenarios(name="HF", data=scenario_data["HF"], scenario_builder=HF_builder)
    sp.add_scenarios(
        name="LF",
        data=scenario_data["LF"],
        scenario_builder=LF_builder,
    )

    if with_bundles:
        sp.initialize_bundles(scheme="mf_paired")

    # NOTE: This solution is for the EF, without bundles.
    return Munch(
        sp=sp,
        solution_values={
            "s[LF,'2'].x": 70.0,
            "s[HF,'2'].x": 40.0,
            "s[LF,'2'].y": 70.0,
            "s[HF,'2'].y": 70.0,
        },
    )
