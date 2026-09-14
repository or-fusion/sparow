"""Option-level tests for BendersSolver abs_tol / rel_tol / bound_checking.

Drop into sparow/tests next to test_benders_transforms.py
(or merge the class into that file).
"""

import pytest
import pyomo.opt

from sparow.benders import BendersSolver

_available_solvers = list(pyomo.opt.check_available_solvers("highs"))
if not _available_solvers:
    _available_solvers = list(pyomo.opt.check_available_solvers("glpk"))
if not _available_solvers:
    _available_solvers = list(pyomo.opt.check_available_solvers("gurobi"))


def _solver_name():
    return _available_solvers[0]


def _solver():
    name = _solver_name()
    s = BendersSolver()
    s.set_options(solver=name, subproblem_solver=name)
    return s


@pytest.mark.skipif(
    not _available_solvers,
    reason="No MIP solver available (tried highs, glpk, gurobi)",
)
class TestBendersUtilities:
    # This is mostly bound testing, but is kept as a more general file
    def test_default_bound_checking_off(self):
        s = BendersSolver()
        assert s.abs_tol is None
        assert s.rel_tol is None
        assert s.bound_checking is False

    def test_set_options_without_tols_leaves_bound_checking_off(self):
        s = _solver()
        assert s.bound_checking is False
        assert s.abs_tol is None
        assert s.rel_tol is None

    def test_abs_tol_enables_bound_checking(self):
        s = BendersSolver()
        name = _solver_name()
        s.set_options(solver=name, subproblem_solver=name, abs_tol=1e-3)
        assert s.abs_tol == 1e-3
        assert s.rel_tol is None
        assert s.bound_checking is True

    def test_rel_tol_enables_bound_checking(self):
        s = BendersSolver()
        name = _solver_name()
        s.set_options(solver=name, subproblem_solver=name, rel_tol=0.01)
        assert s.rel_tol == 0.01
        assert s.abs_tol is None
        assert s.bound_checking is True

    def test_both_tols_enable_bound_checking(self):
        s = BendersSolver()
        name = _solver_name()
        s.set_options(
            solver=name,
            subproblem_solver=name,
            abs_tol=1.0,
            rel_tol=0.05,
        )
        assert s.bound_checking is True

    def test_zero_abs_tol_is_accepted(self):
        s = BendersSolver()
        name = _solver_name()
        s.set_options(solver=name, subproblem_solver=name, abs_tol=0)
        assert s.abs_tol == 0
        assert s.bound_checking is True

    def test_zero_rel_tol_is_accepted(self):
        s = BendersSolver()
        name = _solver_name()
        s.set_options(solver=name, subproblem_solver=name, rel_tol=0)
        assert s.rel_tol == 0
        assert s.bound_checking is True

    def test_set_options_rejects_negative_abs_tol(self):
        s = BendersSolver()
        name = _solver_name()
        with pytest.raises(ValueError, match="abs_tol"):
            s.set_options(solver=name, subproblem_solver=name, abs_tol=-1e-6)

    def test_set_options_rejects_negative_rel_tol(self):
        s = BendersSolver()
        name = _solver_name()
        with pytest.raises(ValueError, match="rel_tol"):
            s.set_options(solver=name, subproblem_solver=name, rel_tol=-0.01)

    def test_negative_abs_tol_does_not_enable_bound_checking(self):
        s = BendersSolver()
        name = _solver_name()
        with pytest.raises(ValueError):
            s.set_options(solver=name, subproblem_solver=name, abs_tol=-1)
        assert s.bound_checking is False
        assert s.abs_tol is None

    def test_default_smoothing_tol_is_positive(self):
        s = BendersSolver()
        assert s.bound_smoothing_tol > 0

    def test_zero_smoothing_tol_is_accepted(self):
        s = BendersSolver()
        name = _solver_name()
        s.set_options(
            solver=name,
            subproblem_solver=name,
            abs_tol=0,
            bound_smoothing_tol=0,
        )
        assert s.bound_smoothing_tol == 0
        assert s.bound_checking is True

    def test_set_options_rejects_negative_smoothing_tol(self):
        s = BendersSolver()
        name = _solver_name()
        with pytest.raises(ValueError, match="bound_smoothing_tol"):
            s.set_options(
                solver=name,
                subproblem_solver=name,
                bound_smoothing_tol=-1e-12,
            )
