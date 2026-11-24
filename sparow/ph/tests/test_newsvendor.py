import pytest

from sparow.sp.examples import (
    LF_newsvendor,
    HF_newsvendor,
    MFrandom_newsvendor,
    simple_newsvendor,
)
from sparow.ph import ProgressiveHedgingSolver

import pyomo.opt
from pyomo.common import unittest

solvers = set(pyomo.opt.check_available_solvers("gurobi_direct", "highs"))
# solvers = []  # Ignore these tests for now


@unittest.pytest.mark.parametrize("mip_solver", solvers)
class TestPHNewsvendor:

    def test_simple(self, mip_solver):
        app = simple_newsvendor()
        solver = ProgressiveHedgingSolver()
        solver.set_options(solver=mip_solver)
        results = solver.solve(app.sp)
        results_dict = results.to_dict()
        soln = next(iter(results_dict["solutions"].values()))

        x = soln["variables"][0]["value"]
        assert x == pytest.approx(app.solution_values["x"], 0.01)
        obj_val = soln["objectives"][0]["value"]
        assert obj_val == pytest.approx(app.objective_value, 0.01)

    def test_resolve_same_sp(self, mip_solver):
        #
        # Solving twice with the same stochastic program must give the same
        # results.  Finalization constructs uncached models in which the
        # first-stage variables are fixed; the cached subproblems used in the
        # next solve must not read their values from those models.
        #
        app = simple_newsvendor()

        def solve():
            solver = ProgressiveHedgingSolver()
            solver.set_options(solver=mip_solver)
            soln = solver.solve(app.sp).last_solution
            return soln.objective().value, [v.value for v in soln.variables()]

        first = solve()
        for b in app.sp.bundles:
            app.sp.create_subproblem(b, cached=True)
            assert not any(v.fixed for v in app.sp.int_to_FirstStageVar[b].values())
        second = solve()

        assert second[0] == pytest.approx(first[0])
        assert second[1] == pytest.approx(first[1])

    def test_HF(self, mip_solver):
        app = HF_newsvendor()
        solver = ProgressiveHedgingSolver()
        solver.set_options(solver=mip_solver)
        solver.set_options(max_iterations=1000)
        results = solver.solve(app.sp)
        results_dict = results.to_dict()
        soln = next(iter(results_dict["solutions"].values()))

        x = soln["variables"][0]["value"]
        assert x == pytest.approx(app.solution_values["x"], 0.01)
        obj_val = soln["objectives"][0]["value"]
        assert obj_val == pytest.approx(app.objective_value, 0.01)

    def test_LF(self, mip_solver):
        app = LF_newsvendor()
        solver = ProgressiveHedgingSolver()
        solver.set_options(solver=mip_solver)
        results = solver.solve(app.sp)
        results_dict = results.to_dict()
        soln = next(iter(results_dict["solutions"].values()))

        x = soln["variables"][0]["value"]
        assert x == pytest.approx(app.solution_values["x"], 0.01)
        obj_val = soln["objectives"][0]["value"]
        assert obj_val == pytest.approx(app.objective_value, 0.01)

    def test_MFrandom(self, mip_solver):
        app = MFrandom_newsvendor()
        solver = ProgressiveHedgingSolver()
        solver.set_options(solver=mip_solver)
        solver.set_options(max_iterations=1000)
        results = solver.solve(app.sp)
        results_dict = results.to_dict()
        soln = next(iter(results_dict["solutions"].values()))

        obj_val = soln["objectives"][0]["value"]
        assert obj_val == pytest.approx(app.objective_value, 0.1)

    def test_MFrandom_with_mf_sp(self, mip_solver):
        hf_app = HF_newsvendor()
        app = MFrandom_newsvendor()
        solver = ProgressiveHedgingSolver()
        solver.set_options(solver=mip_solver)
        solver.set_options(max_iterations=1000)
        results = solver.solve(hf_app.sp, mf_sp=app.sp)
        results_dict = results.to_dict()
        soln = next(iter(results_dict["solutions"].values()))

        obj_val = soln["objectives"][0]["value"]
        assert obj_val == pytest.approx(hf_app.objective_value, 0.1)

    def test_MFrandom_with_mf_sp_with_bundling(self, mip_solver):
        hf_app = HF_newsvendor()
        app = MFrandom_newsvendor(with_bundles=True)
        solver = ProgressiveHedgingSolver()
        solver.set_options(solver=mip_solver)
        solver.set_options(max_iterations=1000)
        results = solver.solve(hf_app.sp, mf_sp=app.sp)
        results_dict = results.to_dict()
        soln = next(iter(results_dict["solutions"].values()))

        obj_val = soln["objectives"][0]["value"]
        assert obj_val == pytest.approx(hf_app.objective_value, 0.1)
