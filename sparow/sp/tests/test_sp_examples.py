import pytest

from sparow.sp.examples import (
    simple_newsvendor,
    LF_newsvendor,
    HF_newsvendor,
    MFrandom_newsvendor,
    MFpaired_newsvendor,
    disjunctive_newsvendor,
)

import pyomo.opt
import pyomo.environ as pyo
from pyomo.common import unittest

solvers = set(pyomo.opt.check_available_solvers("glpk", "gurobi", "highs"))
solvers = ["highs"] if "highs" in solvers else solvers
solvers = ["glpk"] if "glpk" in solvers else solvers


@unittest.pytest.mark.parametrize("mip_solver", solvers)
def test_sp_simple_newsvendor(mip_solver):
    app = simple_newsvendor()
    sp = app.sp

    assert sp.get_objective_coef(0) == 0

    assert set(sp.bundles.keys()) == {"1", "2", "3", "4", "5"}
    assert sp.bundles["1"].probability == 0.2

    #
    # Testing internal data structures
    #
    M1 = sp.create_subproblem("1")
    assert set(sp.int_to_FirstStageVar.keys()) == {"1"}
    # assert set(sp.int_to_FirstStageVar.keys()) == {"1","2","3","4","5"}
    assert sp.varcuid_to_int == {pyo.ComponentUID("x"): 0}

    M2 = sp.create_subproblem("2")
    assert set(sp.int_to_FirstStageVar.keys()) == {"1", "2"}
    assert sp.varcuid_to_int == {pyo.ComponentUID("x"): 0}

    #
    # Test subproblem solver logic
    #
    sp.solve(M1, solver=mip_solver)
    assert pyo.value(M1.s[None, 1].x) == pytest.approx(
        app.solution_values[str(M1.s[None, 1].x)]
    )

    sp.solve(M2, solver=mip_solver)
    assert pyo.value(M2.s[None, 2].x) == pytest.approx(
        app.solution_values[str(M2.s[None, 2].x)]
    )


@unittest.pytest.mark.parametrize("mip_solver", solvers)
def test_sp_disjunctive_newsvendor(mip_solver):
    app = disjunctive_newsvendor()
    sp = app.sp

    #
    # The 'order' disjunct is mapped to its binary indicator variable
    #
    M1 = sp.create_subproblem("1")
    assert sp.varcuid_to_int == {
        pyo.ComponentUID("order.binary_indicator_var"): 0,
        pyo.ComponentUID("x"): 1,
    }
    assert sp.get_variable_name(0) == "order.binary_indicator_var"
    assert sp.get_variable_name(1) == "x"
    assert not sp.continuous_fsv()

    #
    # Test subproblem solver logic (K=10):
    #   d=15: ordering costs K + 15 = 25 > b*d = 22.5, so no order is placed
    #   d=60: ordering costs K + 60 = 70 < b*d = 90, so 60 units are ordered
    #
    sp.solve(M1, solver=mip_solver)
    assert pyo.value(M1.s[None, 1].x) == pytest.approx(0.0)
    assert pyo.value(M1.s[None, 1].order.binary_indicator_var) == pytest.approx(0.0)

    M2 = sp.create_subproblem("2")
    sp.solve(M2, solver=mip_solver)
    assert pyo.value(M2.s[None, 2].x) == pytest.approx(60.0)
    assert pyo.value(M2.s[None, 2].order.binary_indicator_var) == pytest.approx(1.0)


class TestMFNewsVendor:
    """
    Test the multi-fidelity news vendor application

    See https://stoprog.org/sites/default/files/SPTutorial/TutorialSP.pdf
    """


@unittest.pytest.mark.parametrize("mip_solver", solvers)
def test_sp_HF_newsvendor(mip_solver):
    app = HF_newsvendor()
    sp = app.sp

    assert set(sp.bundles.keys()) == {"LF_1", "LF_2", "LF_3", "LF_4", "LF_5"}
    assert sp.bundles["LF_1"].probability == 0.1

    #
    # Testing internal data structures
    #
    M1 = sp.create_subproblem("LF_1")
    assert set(sp.int_to_FirstStageVar.keys()) == {"LF_1"}
    assert sp.varcuid_to_int == {pyo.ComponentUID("x"): 0}

    M2 = sp.create_subproblem("LF_2")
    assert set(sp.int_to_FirstStageVar.keys()) == {"LF_1", "LF_2"}
    assert sp.varcuid_to_int == {pyo.ComponentUID("x"): 0}

    #
    # Test subproblem solver logic
    #
    sp.solve(M1, solver=mip_solver)
    assert pyo.value(M1.s["LF", "1"].x) == pytest.approx(
        app.solution_values[str(M1.s["LF", "1"].x)]
    )

    sp.solve(M2, solver=mip_solver)
    assert pyo.value(M2.s["LF", "2"].x) == pytest.approx(
        app.solution_values[str(M2.s["LF", "2"].x)]
    )


@unittest.pytest.mark.parametrize("mip_solver", solvers)
def test_sp_HF_newsvendor(mip_solver):
    app = HF_newsvendor()
    sp = app.sp

    assert set(sp.bundles.keys()) == {"HF_1", "HF_2", "HF_3", "HF_4", "HF_5"}
    assert sp.bundles["HF_1"].probability == 0.1

    #
    # Testing internal data structures
    #
    M1 = sp.create_subproblem("HF_1")
    assert set(sp.int_to_FirstStageVar.keys()) == {"HF_1"}
    assert sp.varcuid_to_int == {pyo.ComponentUID("x"): 0}

    M2 = sp.create_subproblem("HF_2")
    assert set(sp.int_to_FirstStageVar.keys()) == {"HF_1", "HF_2"}
    assert sp.varcuid_to_int == {pyo.ComponentUID("x"): 0}

    #
    # Test subproblem solver logic
    #
    sp.solve(M1, solver=mip_solver)
    assert pyo.value(M1.s["HF", "1"].x) == pytest.approx(
        app.solution_values[str(M1.s["HF", "1"].x)]
    )

    sp.solve(M2, solver=mip_solver)
    assert pyo.value(M2.s["HF", "2"].x) == pytest.approx(
        app.solution_values[str(M2.s["HF", "2"].x)]
    )


@unittest.pytest.mark.parametrize("mip_solver", solvers)
def test_MFpaired(mip_solver):
    app = MFpaired_newsvendor(with_bundles=True)
    sp = app.sp

    assert set(sp.bundles.keys()) == {"1", "2", "3", "4", "5"}
    assert sp.bundles["1"].probability == 0.2

    #
    # Testing internal data structures
    #
    M1 = sp.create_subproblem("1")
    assert set(sp.int_to_FirstStageVar.keys()) == {"1"}
    assert sp.varcuid_to_int == {pyo.ComponentUID("x"): 0}

    M2 = sp.create_subproblem("2")
    assert set(sp.int_to_FirstStageVar.keys()) == {"1", "2"}
    assert sp.varcuid_to_int == {pyo.ComponentUID("x"): 0}

    #
    # Test subproblem solver logic
    #

    # Subproblem M1 has multiple solutions
    # sp.solve(M1, solver=mip_solver)
    # assert len(M1.s) == 2
    # assert pyo.value(M1.s["HF", 1].x) == pytest.approx(15.0)
    # assert pyo.value(M1.s["LF", 1].x) == pytest.approx(15.0)
    # assert pyo.value(M1.s["HF", 1].y) == pytest.approx(21.0)
    # assert pyo.value(M1.s["LF", 1].y) == pytest.approx(15.0)

    sp.solve(M2, solver=mip_solver)
    assert len(M2.s) == 2
    assert pyo.value(M2.s["HF", "2"].x) == pytest.approx(
        app.solution_values[str(M2.s["HF", "2"].x)]
    )  # 60.0
    # assert pyo.value(M2.s["LF", "2"].x) == pytest.approx(
    #    app.solution_values[str(M2.s["LF", "2"].x)]
    # )  # 60.0
    assert pyo.value(M2.s["HF", "2"].y) == pytest.approx(
        app.solution_values[str(M2.s["HF", "2"].y)]
    )  # 78.0
    assert pyo.value(M2.s["LF", "2"].y) == pytest.approx(
        app.solution_values[str(M2.s["LF", "2"].y)]
    )  # 60.0


@unittest.pytest.mark.parametrize("mip_solver", solvers)
def test_MFrandom(mip_solver):
    app = MFrandom_newsvendor(with_bundles=True)
    sp = app.sp

    assert sp.get_bundles() == {
        "HF_1": {
            "probability": 0.2,
            "scenario_probability": {
                ("HF", "1"): pytest.approx(0.25),
                ("LF", "1"): pytest.approx(0.25),
                ("LF", "3"): pytest.approx(0.5),
            },
            "scenarios": [("HF", "1"), ("LF", "1"), ("LF", "3")],
        },
        "HF_2": {
            "probability": 0.2,
            "scenario_probability": {
                ("HF", "2"): pytest.approx(0.2),
                ("LF", "1"): pytest.approx(0.1),
                ("LF", "4"): pytest.approx(0.7),
            },
            "scenarios": [("HF", "2"), ("LF", "1"), ("LF", "4")],
        },
        "HF_3": {
            "probability": 0.2,
            "scenario_probability": {
                ("HF", "3"): pytest.approx(0.25),
                ("LF", "1"): pytest.approx(0.25),
                ("LF", "3"): pytest.approx(0.5),
            },
            "scenarios": [("HF", "3"), ("LF", "1"), ("LF", "3")],
        },
        "HF_4": {
            "probability": 0.2,
            "scenario_probability": {
                ("HF", "4"): pytest.approx(0.25),
                ("LF", "4"): pytest.approx(0.5833333333333334),
                ("LF", "5"): pytest.approx(0.16666666666666669),
            },
            "scenarios": [("HF", "4"), ("LF", "4"), ("LF", "5")],
        },
        "HF_5": {
            "probability": 0.2,
            "scenario_probability": {
                ("HF", "5"): pytest.approx(0.25),
                ("LF", "4"): pytest.approx(0.5833333333333334),
                ("LF", "5"): pytest.approx(0.16666666666666669),
            },
            "scenarios": [("HF", "5"), ("LF", "4"), ("LF", "5")],
        },
    }

    assert set(sp.bundles.keys()) == {"HF_1", "HF_2", "HF_3", "HF_4", "HF_5"}
    assert sp.bundles["HF_1"].probability == 0.2

    #
    # Testing internal data structures
    #
    M1 = sp.create_subproblem("HF_1")
    assert set(sp.int_to_FirstStageVar.keys()) == {"HF_1"}
    assert sp.varcuid_to_int == {pyo.ComponentUID("x"): 0}

    M2 = sp.create_subproblem("HF_2")
    assert set(sp.int_to_FirstStageVar.keys()) == {"HF_2", "HF_1"}
    assert sp.varcuid_to_int == {pyo.ComponentUID("x"): 0}

    #
    # Test subproblem solver logic
    #

    # Subproblem M1 has multiple solutions
    # sp.solve(M1, solver=mip_solver)
    # assert len(M1.s) == 3
    # assert set(M1.s.keys()) == {("HF", 1), ("LF", 3), ("LF", 4)}
    # assert pyo.value(M1.s["HF", 1].x) == pytest.approx(25.0)
    # assert pyo.value(M1.s["LF", 3].x) == pytest.approx(25.0)
    # assert pyo.value(M1.s["LF", 4].x) == pytest.approx(25.0)
    # assert pyo.value(M1.s["HF", 1].y) == pytest.approx(26.0)
    # assert pyo.value(M1.s["LF", 3].y) == pytest.approx(95.5)
    # assert pyo.value(M1.s["LF", 4].y) == pytest.approx(104.5)

    # sp.solve(M2, solver=mip_solver)
    # assert len(M2.s) == 3
    # assert set(M2.s.keys()) == {("HF", "2"), ("LF", "1"), ("LF", "4")}
    # assert pyo.value(M2.s["HF", "2"].x) == pytest.approx(40.0)
    # assert pyo.value(M2.s["LF", "1"].x) == pytest.approx(40.0)
    # assert pyo.value(M2.s["LF", "4"].x) == pytest.approx(40.0)
    # assert pyo.value(M2.s["HF", "2"].y) == pytest.approx(70.0)
    # assert pyo.value(M2.s["LF", "1"].y) == pytest.approx(42.5)
    # assert pyo.value(M2.s["LF", "4"].y) == pytest.approx(97.0)


def test_cached_subproblem_first_call_uses_ph_values():
    #
    # A cached subproblem whose *first* construction already includes PH
    # values (rho, w, x_bar) must use them.  This happens with parallel PH
    # solvers, where a bundle can first be assigned to a process in a later
    # iteration.  The cached model must match the uncached model.
    #
    w = {0: 2.0}
    x_bar = {0: 3.0}
    rho = {0: 4.0}

    def objective_at_ones(M):
        for var in M.component_data_objects(pyo.Var, descend_into=True):
            var.set_value(1.0)
        return pyo.value(M.obj)

    sp = simple_newsvendor().sp
    M_cached = sp.create_subproblem("1", w=w, x_bar=x_bar, rho=rho, cached=True)
    params = M_cached.sparow_params
    assert pyo.value(params.w[0]) == 2.0
    assert pyo.value(params.x_bar[0]) == 3.0
    assert pyo.value(params.rho[0]) == 4.0
    cached_obj = objective_at_ones(M_cached)

    sp = simple_newsvendor().sp
    M_uncached = sp.create_subproblem("1", w=w, x_bar=x_bar, rho=rho, cached=False)
    assert cached_obj == pytest.approx(objective_at_ones(M_uncached))

    # Without PH values, the cached model is reset to the original objective
    sp = simple_newsvendor().sp
    M_cached = sp.create_subproblem("1", w=w, x_bar=x_bar, rho=rho, cached=True)
    M_cached = sp.create_subproblem("1", cached=True)
    sp = simple_newsvendor().sp
    M_plain = sp.create_subproblem("1", cached=False)
    assert objective_at_ones(M_cached) == pytest.approx(objective_at_ones(M_plain))


def test_cached_subproblem_rebinds_first_stage_variables():
    #
    # Constructing an uncached model for a bundle (as evaluate() does)
    # re-binds the first-stage variable map to that model.  Retrieving the
    # cached model must re-bind it to the cached model, so that
    # get_variable_value() and fix_variable() act on the returned model.
    #
    sp = simple_newsvendor().sp
    M_cached = sp.create_subproblem("1", cached=True)
    sp.int_to_FirstStageVar["1"][0].set_value(5.0)

    sp.create_subproblem("1", cached=False)
    sp.fix_variable("1", 0, 7.0)
    assert sp.get_variable_value("1", 0) == 7.0

    M = sp.create_subproblem("1", cached=True)
    assert M is M_cached
    assert sp.get_variable_value("1", 0) == 5.0
    assert not sp.int_to_FirstStageVar["1"][0].fixed
