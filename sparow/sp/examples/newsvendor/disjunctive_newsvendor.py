from munch import Munch
import pyomo.environ as pyo
from pyomo.gdp import Disjunct, Disjunction
from sparow.sp import stochastic_program

#
# Data for a newsvendor example with a fixed ordering cost
#
#   c - unit purchase cost
#   b - unit backorder (shortage) cost
#   h - unit holding cost
#   U - maximum order quantity
#
common_data = dict(c=1.0, b=1.5, h=0.1, U=100.0)
scenario_data = {
    "scenarios": [
        dict(ID=1, data={"d": 15}),
        dict(ID=2, data={"d": 60}),
        dict(ID=3, data={"d": 72}),
        dict(ID=4, data={"d": 78}),
        dict(ID=5, data={"d": 82}),
    ],
}


#
# Function that constructs a newsvendor model with a disjunctive
# first-stage ordering decision
#
def builder(data, args):
    """
    Newsvendor model where the vendor first decides whether to place an order.

    The first stage includes a disjunction:

      * ``order``:    an order of size 0 <= x <= U is placed, with fixed cost K
      * ``no_order``: no order is placed (x == 0)

    The second-stage cost is the same polyhedral newsvendor cost used in
    newsvendor.py.  The disjunction is reformulated with the Big-M
    transformation so the model can be solved with a MIP solver.  The
    ``order`` disjunct is declared as a first-stage variable, which sparow
    maps to ``order.binary_indicator_var``.
    """
    b = data["b"]
    c = data["c"]
    h = data["h"]
    d = data["d"]
    U = data["U"]
    K = data["K"]

    M = pyo.ConcreteModel(data["ID"])

    M.x = pyo.Var(bounds=(0, U))

    M.order = Disjunct()
    M.order.capacity = pyo.Constraint(expr=M.x <= U)

    M.no_order = Disjunct()
    M.no_order.zero = pyo.Constraint(expr=M.x <= 0)

    M.order_decision = Disjunction(expr=[M.order, M.no_order])

    M.y = pyo.Var()
    M.greater = pyo.Constraint(expr=M.y >= (c - b) * M.x + b * d)
    M.less = pyo.Constraint(expr=M.y >= (c + h) * M.x - h * d)

    M.o = pyo.Objective(expr=K * M.order.binary_indicator_var + M.y)

    pyo.TransformationFactory("gdp.bigm").apply_to(M)

    return M


def _disjunctive_newsvendor(K):
    sp = stochastic_program(first_stage_variables=["x", "order"])
    sp.configure(common_data=dict(common_data, K=K))
    sp.add_scenarios(data=scenario_data, scenario_builder=builder)
    return sp


def disjunctive_newsvendor():
    """
    Disjunctive newsvendor where ordering is optimal.

    With x = 60 the expected newsvendor cost is 76.5 (see simple_newsvendor),
    so ordering costs 76.5 + K = 86.5.  Not ordering costs E[b*d] = 92.1.
    """
    return Munch(
        sp=_disjunctive_newsvendor(K=10.0),
        objective_value=86.5,
        unique_solution=True,
        solution_values={"x": 60.0, "order.binary_indicator_var": 1.0},
    )


def disjunctive_newsvendor_no_order():
    """
    Disjunctive newsvendor where not ordering is optimal.

    Ordering costs 76.5 + K = 96.5, which exceeds the cost of not
    ordering, E[b*d] = 92.1.
    """
    return Munch(
        sp=_disjunctive_newsvendor(K=20.0),
        objective_value=92.1,
        unique_solution=True,
        solution_values={"x": 0.0, "order.binary_indicator_var": 0.0},
    )
