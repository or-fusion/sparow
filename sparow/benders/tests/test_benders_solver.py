import pytest
import pyomo.environ as pyo

from sparow.sp.examples import (
    LF_newsvendor,
    HF_newsvendor,
    MFrandom_newsvendor,
    simple_newsvendor,
    single_scenario_newsvendor,
    simple_absolute_value,
    adjustable_absolute_value,
    AMPL_facilityloc,
    AMPL_facilityloc_Benders_Test,
)
from sparow.ef import ExtensiveFormSolver

from pyomo.common.dependencies import attempt_import

from sparow.benders import BendersSolver

import pyomo.opt
from pyomo.common import unittest

parameterized, param_available = attempt_import("parameterized")
if not param_available:
    raise unittest.SkipTest("Parameterized is not available.")
parameterized = parameterized.parameterized


open_source_solver = set(pyomo.opt.check_available_solvers("highs"))
if len(open_source_solver) == 0:
    open_source_solver = set(pyomo.opt.check_available_solvers("glpk"))
# solvers = set(pyomo.opt.check_available_solvers("gurobi")) | open_source_solver
solvers = set(pyomo.opt.check_available_solvers("gurobi"))

persistent_mip_solvers = list(
    pyomo.opt.check_available_solvers(
        # "appsi_highs",
        # "appsi_gurobi",
        "gurobi_persistent",
    )
)


@unittest.pytest.mark.parametrize("mip_solver", solvers)
class TestBenders_NonPersistent:

    def test_abs(self, mip_solver):
        app = simple_absolute_value()
        solver = BendersSolver()
        solver.set_options(solver=mip_solver, subproblem_solver=mip_solver)

        default_lower_eta = -1_000
        eta_bounds_map = {s: (default_lower_eta, None) for s in app.sp.bundles}
        results = solver.solve(app.sp, eta_bounds_map)
        results_dict = results.to_dict()
        soln = next(iter(results_dict["solutions"].values()))

        obj_val = soln["objectives"][0]["value"]
        assert obj_val == pytest.approx(app.objective_value)
        assert app.unique_solution
        x = soln["variables"][0]["value"]
        assert x == pytest.approx(app.solution_values["x"])

    def test_shifted_abs(self, mip_solver):
        solver = BendersSolver()
        solver.set_options(
            solver=mip_solver,
            subproblem_solver=mip_solver,
            #    loglevel="DEBUG",
        )
        a_val = 1
        model_data = {
            "scenarios": [
                {"ID": 1, "LB": None, "UB": None},
            ],
        }
        app_data = dict(a=a_val, c=0, L=1, R=1)
        app = adjustable_absolute_value(
            local_app_data=app_data, local_model_data=model_data
        )

        default_lower_eta = -1_000
        eta_bounds_map = {s: (default_lower_eta, None) for s in app.sp.bundles}
        results = solver.solve(app.sp, eta_bounds_map)
        results_dict = results.to_dict()
        soln = next(iter(results_dict["solutions"].values()))

        obj_val = soln["objectives"][0]["value"]
        assert obj_val == pytest.approx(app.objective_value)
        assert app.unique_solution
        x = soln["variables"][0]["value"]
        assert x == pytest.approx(a_val)

    def test_shifted_abs_2(self, mip_solver):
        solver = BendersSolver()
        solver.set_options(solver=mip_solver, subproblem_solver=mip_solver)
        a_vals = [1, -1, 3, 4]
        for a_val in a_vals:
            model_data = {
                "scenarios": [
                    {"ID": 1, "LB": None, "UB": None},
                ],
            }
            app_data = dict(a=a_val, c=0, L=1, R=1)
            app = adjustable_absolute_value(
                local_app_data=app_data, local_model_data=model_data
            )

            default_lower_eta = -1_000
            eta_bounds_map = {s: (default_lower_eta, None) for s in app.sp.bundles}
            results = solver.solve(app.sp, eta_bounds_map)
            results_dict = results.to_dict()
            soln = next(iter(results_dict["solutions"].values()))

            obj_val = soln["objectives"][0]["value"]
            assert obj_val == pytest.approx(app.objective_value)
            assert app.unique_solution
            x = soln["variables"][0]["value"]
            assert x == pytest.approx(a_val)

    def test_single_scenario_newsvendor(self, mip_solver):
        app = single_scenario_newsvendor()
        solver = BendersSolver()
        solver.set_options(
            solver=mip_solver,
            subproblem_solver=mip_solver,
            #    loglevel="DEBUG",
        )

        default_lower_eta = -1_000
        eta_bounds_map = {s: (default_lower_eta, None) for s in app.sp.bundles}
        results = solver.solve(app.sp, eta_bounds_map)
        results_dict = results.to_dict()
        soln = next(iter(results_dict["solutions"].values()))

        assert app.unique_solution
        obj_val = soln["objectives"][0]["value"]
        x = soln["variables"][0]["value"]
        print(f"{x=}, {obj_val=}")
        assert obj_val == pytest.approx(app.objective_value)
        assert x == pytest.approx(app.solution_values["x"])

    def test_simple_newsvendor(self, mip_solver):
        app = simple_newsvendor()
        solver = BendersSolver()
        solver.set_options(
            solver=mip_solver,
            subproblem_solver=mip_solver,
            #    loglevel= "DEBUG",
        )

        default_lower_eta = -1_000
        eta_bounds_map = {s: (default_lower_eta, None) for s in app.sp.bundles}
        print(eta_bounds_map.keys())
        results = solver.solve(app.sp, eta_bounds_map)
        results_dict = results.to_dict()
        soln = next(iter(results_dict["solutions"].values()))

        assert app.unique_solution
        x = soln["variables"][0]["value"]
        assert x == pytest.approx(app.solution_values["x"])
        obj_val = soln["objectives"][0]["value"]
        assert obj_val == pytest.approx(app.objective_value)

    def Xtest_facilityloc(self, mip_solver):
        app = AMPL_facilityloc()
        # solver = BendersSolver()
        # solver.set_options(solver=mip_solver,
        #                    subproblem_solver=mip_solver,
        #                    loglevel= "DEBUG",
        #                    )
        # default_lower_eta = -1_000
        # #not sure the s values here map to what the bundles actually expect
        # eta_bounds_map = {s: (default_lower_eta, None) for s in app.sp.bundles}
        # #app.sp.bundles are {'HF_High', 'HF_Low', 'HF_Medium'}
        # #so the eta's are getting those names

        # #the scenario keys for s are of the style ('HF', 'Low') as a tuple
        # #for each of the scenario models, we get a block definition like:
        # #s : Size=1, Index={('HF', 'High')}, Active=True
        # #so there appears to be a mismatch between bundles and scenario keys

        # #first iteration of subproblems is giving infeasible/unbounded error code
        # #need to print out first master solve results, master model, and subproblem model
        # results = solver.solve(app.sp, eta_bounds_map)
        # results_dict = results.to_dict()
        # obj_val = results_dict["solutions"][0]["objectives"][0]["value"]

        # assert obj_val == pytest.approx(app.objective_value)

        solver = BendersSolver()
        solver.set_options(
            solver=mip_solver,
            subproblem_solver=mip_solver,
            custom_b_upper="High",
            #    loglevel= "INFO",
            # loglevel="DEBUG",
        )
        default_lower_eta = -100_000
        eta_bounds_map = {s: (default_lower_eta, None) for s in app.sp.bundles}
        results = solver.solve(app.sp, eta_bounds_map)
        results_dict = results.to_dict()
        obj_val = results_dict["solutions"][0]["objectives"][0]["value"]

        assert obj_val == pytest.approx(app.objective_value)

    def test_facilityloc_benders_test(self, mip_solver):
        app = AMPL_facilityloc_Benders_Test()
        solver = BendersSolver()
        solver.set_options(
            solver=mip_solver,
            subproblem_solver=mip_solver,
            custom_b_upper="High",
            #    loglevel= "INFO",
            # loglevel="DEBUG",
        )
        default_lower_eta = -100_000
        eta_bounds_map = {s: (default_lower_eta, None) for s in app.sp.bundles}
        results = solver.solve(app.sp, eta_bounds_map)
        results_dict = results.to_dict()
        obj_val = results_dict["solutions"][0]["objectives"][0]["value"]

        assert obj_val == pytest.approx(app.objective_value)

    def _abs_problem(self, mip_solver, **opts):
        app = simple_absolute_value()
        solver = BendersSolver()
        solver.set_options(solver=mip_solver, subproblem_solver=mip_solver, **opts)
        eta_bounds_map = {s: (-1_000, None) for s in app.sp.bundles}
        return app, solver, eta_bounds_map

    def test_abs_bound_checking_off_no_cuts(self, mip_solver):
        app, solver, eta = self._abs_problem(mip_solver)
        assert solver.bound_checking is False
        out = solver.solve_and_return_model(app.sp, eta)
        assert "No Cuts Added" in out.solutions.metadata.termination_condition
        soln = next(iter(out.solutions.to_dict()["solutions"].values()))
        assert soln["objectives"][0]["value"] == pytest.approx(app.objective_value)
        # Tracking is always on; bound_checking only controls gap exit.
        assert out.best_lb is not None
        assert out.best_ub is not None
        assert out.best_ub + solver.bound_smoothing_tol >= out.best_lb
        assert out.best_ub == pytest.approx(app.objective_value, abs=1e-4)
        assert out.best_lb == pytest.approx(app.objective_value, abs=1e-4)
        assert out.solutions.metadata.best_lb == out.best_lb
        assert out.solutions.metadata.best_ub == out.best_ub

    def test_abs_loose_abs_tol_stops_on_gap(self, mip_solver):
        app, solver, eta = self._abs_problem(mip_solver, abs_tol=1e6, max_iterations=50)
        assert solver.bound_checking is True
        out = solver.solve_and_return_model(app.sp, eta)
        term = out.solutions.metadata.termination_condition
        assert "abs_tol" in term
        assert out.solutions.metadata.iterations < 50
        assert out.best_ub is not None
        assert out.best_ub - out.best_lb <= 1e6 + solver.bound_smoothing_tol

    def test_abs_loose_rel_tol_stops_on_gap(self, mip_solver):
        app, solver, eta = self._abs_problem(
            mip_solver, rel_tol=10.0, max_iterations=50
        )
        out = solver.solve_and_return_model(app.sp, eta)
        assert "rel_tol" in out.solutions.metadata.termination_condition
        assert out.solutions.metadata.iterations < 50
        assert out.best_ub - out.best_lb <= (
            10.0 * abs(out.best_lb) + solver.bound_smoothing_tol
        )

    def test_abs_either_or_abs_wins(self, mip_solver):
        app, solver, eta = self._abs_problem(
            mip_solver, abs_tol=1e6, rel_tol=1e-16, max_iterations=50
        )
        out = solver.solve_and_return_model(app.sp, eta)
        assert "abs_tol" in out.solutions.metadata.termination_condition

    def test_abs_either_or_rel_wins(self, mip_solver):
        app, solver, eta = self._abs_problem(
            mip_solver, abs_tol=1e-16, rel_tol=10.0, max_iterations=50
        )
        out = solver.solve_and_return_model(app.sp, eta)
        assert "rel_tol" in out.solutions.metadata.termination_condition

    def test_abs_return_and_metadata_carry_bounds(self, mip_solver):
        app, solver, eta = self._abs_problem(mip_solver, abs_tol=1e6, max_iterations=50)
        out = solver.solve_and_return_model(app.sp, eta)
        meta = out.solutions.metadata
        assert out.best_lb == meta.best_lb
        assert out.best_ub == meta.best_ub
        assert meta.abs_tol == 1e6
        assert meta.bound_checking is True

    def test_abs_zero_abs_tol_reaches_known_obj(self, mip_solver):
        app, solver, eta = self._abs_problem(mip_solver, abs_tol=0, max_iterations=50)
        out = solver.solve_and_return_model(app.sp, eta)
        soln = next(iter(out.solutions.to_dict()["solutions"].values()))
        assert soln["objectives"][0]["value"] == pytest.approx(app.objective_value)
        assert out.best_ub is not None
        assert out.best_ub - out.best_lb <= solver.bound_smoothing_tol

    def test_abs_collect_off_returns_no_iterate_pool(self, mip_solver):
        app, solver, eta = self._abs_problem(mip_solver)
        out = solver.solve_and_return_model(app.sp, eta)
        assert out.feasible_iterate_pool is None
        assert out.best_lb is not None
        assert out.best_ub is not None

    def test_abs_collect_on_archives_lower_bounding_iterates(self, mip_solver):
        from or_topas.solnpool import PoolPolicy

        app, solver, eta = self._abs_problem(mip_solver, collect_feasible_iterates=True)
        out = solver.solve_and_return_model(app.sp, eta)
        pool = out.feasible_iterate_pool
        assert pool is not None
        assert len(pool) >= 1
        assert pool.policy == PoolPolicy.keep_all
        assert pool.name == "feasible_benders_iterates"
        for sol in pool:
            assert sol.objective(0).name == "L_k"
            assert sol.objective(1).name == "U_k"
            assert (
                sol.objective(1).value + solver.bound_smoothing_tol
                >= sol.objective(0).value
            )
            assert len(sol.variables()) >= 2
        first = next(iter(pool))
        # First master on this model sits on the eta lower bound.
        assert first.objective(0).value == pytest.approx(-1000, abs=1.0)

    def test_abs_collect_stores_eta_k_not_Q_after_optimality_cut(self, mip_solver):
        app, solver, eta = self._abs_problem(mip_solver, collect_feasible_iterates=True)
        first = {}

        def _on_iteration(data):
            if first:
                return
            benders = data.upper_model.benders
            if not benders.last_iterate_is_feasible():
                return
            q_list = benders.last_subproblem_etas()
            if q_list is None or any(q is None for q in q_list):
                return
            first["eta_k"] = list(data.eta_k)
            first["Q"] = list(q_list)
            first["n_root"] = len(benders.root_vars)
            first["cuts"] = list(data.cuts_added)

        out = solver.solve_and_return_model(app.sp, eta, on_iteration=_on_iteration)
        assert first, "expected a feasible first iterate with finite Q_s"
        assert first["cuts"], "expected an optimality cut on the first iterate"
        assert first["eta_k"] != first["Q"]
        sol = next(iter(out.feasible_iterate_pool))
        stored_etas = [v.value for v in sol.variables()[first["n_root"] :]]
        assert stored_etas == pytest.approx(first["eta_k"])
        assert stored_etas != pytest.approx(first["Q"])

    def test_abs_collect_does_not_change_solve_return_type(self, mip_solver):
        app, solver, eta = self._abs_problem(mip_solver, collect_feasible_iterates=True)
        results = solver.solve(app.sp, eta)
        assert hasattr(results, "to_dict")
        soln = next(iter(results.to_dict()["solutions"].values()))
        assert soln["objectives"][0]["value"] == pytest.approx(app.objective_value)

    def test_abs_user_keep_latest_retains_one(self, mip_solver):
        from or_topas.solnpool import PyomoPoolManager, PoolPolicy

        app = simple_absolute_value()
        pool = PyomoPoolManager()
        pool.add_pool(
            name="latest",
            policy=PoolPolicy.keep_latest,
            max_pool_size=1,
        )
        solver = BendersSolver()
        solver.set_options(
            solver=mip_solver,
            subproblem_solver=mip_solver,
            feasible_iterate_pool=pool,
        )
        eta = {s: (-1_000, None) for s in app.sp.bundles}
        out = solver.solve_and_return_model(app.sp, eta)
        assert out.feasible_iterate_pool is pool
        assert len(pool) == 1
        sol = next(iter(pool))
        assert sol.objective(0).name == "L_k"
        assert sol.objective(1).name == "U_k"


class TestBenders_Errors(unittest.TestCase):
    def test_allow_infeasible_subproblems(self):
        app = simple_absolute_value()
        solver = BendersSolver()
        solver.set_options(
            solver="glpk",
            subproblem_solver="glpk",
            is_persistent_solver=False,
            allow_infeasible_subproblems=True,
        )

        default_lower_eta = -1_000
        eta_bounds_map = {s: (default_lower_eta, None) for s in app.sp.bundles}
        assert_text = "Must use a persistent solver to support feasibility cuts"
        with self.assertRaisesRegex(AssertionError, assert_text):
            results = solver.solve(app.sp, eta_bounds_map)


@pytest.mark.skipif(
    len(persistent_mip_solvers) == 0, reason="No persistent solvers available"
)
@unittest.pytest.mark.parametrize("mip_solver", persistent_mip_solvers)
class TestBenders_Persistent:

    def test_abs(self, mip_solver):
        app = simple_absolute_value()
        solver = BendersSolver()
        solver.set_options(
            solver=mip_solver,
            subproblem_solver=mip_solver,
            is_persistent_solver=True,
        )

        default_lower_eta = -1_000
        eta_bounds_map = {s: (default_lower_eta, None) for s in app.sp.bundles}
        results = solver.solve(app.sp, eta_bounds_map)
        results_dict = results.to_dict()
        soln = next(iter(results_dict["solutions"].values()))

        obj_val = soln["objectives"][0]["value"]
        assert obj_val == pytest.approx(app.objective_value)
        assert app.unique_solution
        x = soln["variables"][0]["value"]
        assert x == pytest.approx(app.solution_values["x"])

    def test_shifted_abs(self, mip_solver):
        solver = BendersSolver()
        solver.set_options(
            solver=mip_solver,
            subproblem_solver=mip_solver,
            is_persistent_solver=True,
        )
        a_val = 1
        model_data = {
            "scenarios": [
                {"ID": 1, "LB": None, "UB": None},
            ],
        }
        app_data = dict(a=a_val, c=0, L=1, R=1)
        app = adjustable_absolute_value(
            local_app_data=app_data, local_model_data=model_data
        )

        default_lower_eta = -1_000
        eta_bounds_map = {s: (default_lower_eta, None) for s in app.sp.bundles}
        results = solver.solve(app.sp, eta_bounds_map)
        results_dict = results.to_dict()
        soln = next(iter(results_dict["solutions"].values()))

        obj_val = soln["objectives"][0]["value"]
        assert obj_val == pytest.approx(app.objective_value)
        assert app.unique_solution
        x = soln["variables"][0]["value"]
        assert x == pytest.approx(a_val)

    def test_shifted_abs_2(self, mip_solver):
        solver = BendersSolver()
        solver.set_options(
            solver=mip_solver,
            subproblem_solver=mip_solver,
            is_persistent_solver=True,
        )
        a_vals = [1, -1, 3, 4]
        for a_val in a_vals:
            model_data = {
                "scenarios": [
                    {"ID": 1, "LB": None, "UB": None},
                ],
            }
            app_data = dict(a=a_val, c=0, L=1, R=1)
            app = adjustable_absolute_value(
                local_app_data=app_data, local_model_data=model_data
            )

            default_lower_eta = -1_000
            eta_bounds_map = {s: (default_lower_eta, None) for s in app.sp.bundles}
            results = solver.solve(app.sp, eta_bounds_map)
            results_dict = results.to_dict()
            soln = next(iter(results_dict["solutions"].values()))

            obj_val = soln["objectives"][0]["value"]
            assert obj_val == pytest.approx(app.objective_value)
            assert app.unique_solution
            x = soln["variables"][0]["value"]
            assert x == pytest.approx(a_val)

    def test_single_scenario_newsvendor(self, mip_solver):
        app = single_scenario_newsvendor()
        solver = BendersSolver()
        solver.set_options(
            solver=mip_solver,
            subproblem_solver=mip_solver,
            is_persistent_solver=True,
        )

        default_lower_eta = -1_000
        eta_bounds_map = {s: (default_lower_eta, None) for s in app.sp.bundles}
        results = solver.solve(app.sp, eta_bounds_map)
        results_dict = results.to_dict()
        soln = next(iter(results_dict["solutions"].values()))

        assert app.unique_solution
        obj_val = soln["objectives"][0]["value"]
        x = soln["variables"][0]["value"]
        print(f"{x=}, {obj_val=}")
        assert obj_val == pytest.approx(app.objective_value)
        assert x == pytest.approx(app.solution_values["x"])

    def test_simple_newsvendor(self, mip_solver):
        app = simple_newsvendor()
        solver = BendersSolver()
        solver.set_options(
            solver=mip_solver,
            subproblem_solver=mip_solver,
            is_persistent_solver=True,
        )

        default_lower_eta = -1_000
        eta_bounds_map = {s: (default_lower_eta, None) for s in app.sp.bundles}
        results = solver.solve(app.sp, eta_bounds_map)
        results_dict = results.to_dict()
        soln = next(iter(results_dict["solutions"].values()))

        assert app.unique_solution
        x = soln["variables"][0]["value"]
        assert x == pytest.approx(app.solution_values["x"])
        obj_val = soln["objectives"][0]["value"]
        assert obj_val == pytest.approx(app.objective_value)

    def test_feas_restricted_abs_infeasible_start(self, mip_solver):
        from sparow.sp.examples import feasibility_included_absolute_value

        def _start_x_outside_box(sp, model):
            b = next(iter(sp.int_to_FirstStageVar))
            for var in sp.int_to_FirstStageVar[b].values():
                var.set_value(10.0)  # UB = 5
            return model

        app = feasibility_included_absolute_value()
        solver = BendersSolver()
        solver.set_options(
            solver=mip_solver,
            subproblem_solver=mip_solver,
            is_persistent_solver=True,
            allow_infeasible_subproblems=True,
            abs_tol=0,
            max_iterations=50,
        )
        eta_bounds_map = {s: (-1_000, None) for s in app.sp.bundles}

        feasible_flags = []

        def _on_iteration(data):
            benders = data.upper_model.benders
            feasible_flags.append(benders.last_iterate_is_feasible())

        out = solver.solve_and_return_model(
            app.sp,
            eta_bounds_map,
            master_transforms=[_start_x_outside_box],
            on_iteration=_on_iteration,
        )

        assert feasible_flags, "expected at least one generate_cut"
        assert feasible_flags[0] is False
        assert any(feasible_flags), "expected a later feasible iterate after feas cuts"
        assert out.best_ub is not None
        assert out.best_ub - out.best_lb <= solver.bound_smoothing_tol
        soln = next(iter(out.solutions.to_dict()["solutions"].values()))
        assert soln["objectives"][0]["value"] == pytest.approx(app.objective_value)
        assert soln["variables"][0]["value"] == pytest.approx(app.solution_values["x"])

    def test_feas_restricted_abs_tracks_bounds_without_tols(self, mip_solver):
        from sparow.sp.examples import feasibility_included_absolute_value

        def _start_x_outside_box(sp, model):
            b = next(iter(sp.int_to_FirstStageVar))
            for var in sp.int_to_FirstStageVar[b].values():
                var.set_value(10.0)
            return model

        app = feasibility_included_absolute_value()
        solver = BendersSolver()
        solver.set_options(
            solver=mip_solver,
            subproblem_solver=mip_solver,
            is_persistent_solver=True,
            allow_infeasible_subproblems=True,
            max_iterations=50,
        )
        assert solver.bound_checking is False
        eta_bounds_map = {s: (-1_000, None) for s in app.sp.bundles}
        first_ub = []

        def _on_iteration(data):
            if not first_ub:
                first_ub.append(data.upper_model.benders.last_iterate_is_feasible())

        out = solver.solve_and_return_model(
            app.sp,
            eta_bounds_map,
            master_transforms=[_start_x_outside_box],
            on_iteration=_on_iteration,
        )
        assert first_ub and first_ub[0] is False
        assert out.best_lb is not None
        assert out.best_ub is not None
        assert out.best_ub + solver.bound_smoothing_tol >= out.best_lb
        assert "No Cuts Added" in out.solutions.metadata.termination_condition
        assert out.solutions.metadata.best_lb == out.best_lb
        assert out.solutions.metadata.best_ub == out.best_ub

    def test_feas_restricted_abs_collect_skips_infeasible_start(self, mip_solver):
        from sparow.sp.examples import feasibility_included_absolute_value

        def _start_x_outside_box(sp, model):
            b = next(iter(sp.int_to_FirstStageVar))
            for var in sp.int_to_FirstStageVar[b].values():
                var.set_value(10.0)  # UB = 5
            return model

        app = feasibility_included_absolute_value()
        solver = BendersSolver()
        solver.set_options(
            solver=mip_solver,
            subproblem_solver=mip_solver,
            is_persistent_solver=True,
            allow_infeasible_subproblems=True,
            collect_feasible_iterates=True,
            abs_tol=0,
            max_iterations=50,
        )
        eta_bounds_map = {s: (-1_000, None) for s in app.sp.bundles}

        feasible_flags = []

        def _on_iteration(data):
            benders = data.upper_model.benders
            feasible_flags.append(benders.last_iterate_is_feasible())

        out = solver.solve_and_return_model(
            app.sp,
            eta_bounds_map,
            master_transforms=[_start_x_outside_box],
            on_iteration=_on_iteration,
        )

        assert feasible_flags, "expected at least one generate_cut"
        assert feasible_flags[0] is False
        pool = out.feasible_iterate_pool
        assert pool is not None
        assert len(pool) == sum(1 for flag in feasible_flags if flag)
        assert len(pool) >= 1
        for sol in pool:
            assert sol.objective(0).name == "L_k"
            assert sol.objective(1).name == "U_k"
            # First stored variable is the first-stage x, not the
            # outside-the-box start of 10.
            assert abs(sol.variables()[0].value) <= 5.0 + 1e-6
