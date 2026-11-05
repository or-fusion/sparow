import pytest
import pyomo.environ as pyo
from sparow.sp import stochastic_program


@pytest.fixture
def sp0():
    def builder(*args, **kwargs):
        M = pyo.ConcreteModel()
        M.x = pyo.Var()
        M.y = pyo.Var()
        M.o = pyo.Objective(expr=M.x)
        return M

    sp = stochastic_program(first_stage_variables=["x"])
    sp.initialize_model(model_builder=builder)
    sp.initialize_model(model_data=dict(scenarios=[{"ID": 1}]))
    return sp


@pytest.fixture
def sp1():
    def builder(*args, **kwargs):
        M = pyo.ConcreteModel()
        M.x = pyo.Var()
        M.y = pyo.Var()
        M.o = pyo.Objective(expr=M.x)
        return M

    sp = stochastic_program(first_stage_variables=["x"])
    sp.initialize_model(model_builder=builder)
    sp.initialize_model(model_data=dict(scenarios=[{"ID": 1}, {"ID": 2}]))
    return sp


@pytest.fixture
def sp2():
    def builder(*args, **kwargs):
        M = pyo.ConcreteModel()
        M.x = pyo.Var()
        M.y = pyo.Var(within=pyo.Binary)
        M.o = pyo.Objective(expr=M.x)
        return M

    sp = stochastic_program(first_stage_variables=["y", "x"])
    sp.initialize_model(model_builder=builder)
    sp.initialize_model(model_data=dict(scenarios=[{"ID": 1}, {"ID": 2}]))
    return sp


@pytest.fixture
def sp3():
    def builder(*args, **kwargs):
        M = pyo.ConcreteModel()
        M.x = pyo.Var()
        M.b = pyo.Block()
        M.b.y = pyo.Var(within=pyo.Binary)
        M.o = pyo.Objective(expr=M.x)
        return M

    sp = stochastic_program(first_stage_variables=["b.y", "x"])
    sp.initialize_model(model_builder=builder)
    sp.initialize_model(model_data=dict(scenarios=[{"ID": 1}, {"ID": 2}]))
    return sp


class TestSP(object):
    """
    Test variable initialization logic for Pyomo models
    """

    def test_simple0(self, sp0):
        M = sp0.create_subproblem("1")

        assert sp0.varcuid_to_int == {pyo.ComponentUID("x"): 0}
        assert list(sp0.int_to_FirstStageVar["1"].keys()) == [0]
        assert sp0.shared_variables() == [0]
        assert sp0.get_objective_coef(0) == 1.0  # x
        assert sp0.get_variable_name(0) == "x"

    def test_simple1(self, sp1):
        M = sp1.create_subproblem("1")

        assert sp1.varcuid_to_int == {pyo.ComponentUID("x"): 0}
        assert list(sp1.int_to_FirstStageVar["1"].keys()) == [0]
        assert sp1.shared_variables() == [0]
        assert sp1.get_objective_coef(0) == 0.5  # x
        assert sp1.get_variable_name(0) == "x"

    def test_simple2(self, sp2):
        M = sp2.create_subproblem("1")

        assert sp2.varcuid_to_int == {
            pyo.ComponentUID("y"): 1,
            pyo.ComponentUID("x"): 0,
        }
        assert list(sorted(sp2.int_to_FirstStageVar["1"].keys())) == [0, 1]
        assert sp2.shared_variables() == [0, 1]
        assert sp2.get_objective_coef(0) == 0.5  # x
        assert sp2.get_objective_coef(1) == 0  # y
        assert sp2.get_variable_name(0) == "x"
        assert sp2.get_variable_name(1) == "y"

    def test_simple3(self, sp3):
        M = sp3.create_subproblem("1")

        assert sp3.varcuid_to_int == {
            pyo.ComponentUID("b.y"): 0,
            pyo.ComponentUID("x"): 1,
        }
        assert list(sorted(sp3.int_to_FirstStageVar["1"].keys())) == [0, 1]
        assert sp3.shared_variables() == [0, 1]
        assert sp3.get_objective_coef(0) == 0  # y
        assert sp3.get_objective_coef(1) == 0.5  # x
        assert sp3.get_variable_name(0) == "b.y"
        assert sp3.get_variable_name(1) == "x"

    def test_continuous1(self, sp1):
        M = sp1.create_subproblem("1")
        assert sp1.continuous_fsv()
        assert sp1._binary_or_integer_fsv == set()

    def test_continuous2(self, sp2):
        M = sp2.create_subproblem("1")
        assert not sp2.continuous_fsv()
        assert sp2._binary_or_integer_fsv == {1}

    def test_sp0_EF_noncompact(self, sp0):
        M = sp0.create_EF(compact_repn=False)
        assert len(M.non_ant_cons) == 1
        assert len(M.s) == 1
        assert len(M.first_stage_variables) == 1

    def test_sp0_EF_compact(self, sp0):
        M = sp0.create_EF(compact_repn=True)
        assert getattr(M, "non_ant_cons", None) == None
        assert len(M.s) == 1
        assert len(M.first_stage_variables) == 1

    def test_sp1_EF_noncompact(self, sp1):
        M = sp1.create_EF(compact_repn=False)
        assert len(M.non_ant_cons) == 2
        assert len(M.s) == 2
        assert len(M.first_stage_variables) == 1

    def test_sp1_EF_compact(self, sp1):
        M = sp1.create_EF(compact_repn=True)
        assert getattr(M, "non_ant_cons", None) == None
        assert len(M.s) == 2
        assert len(M.first_stage_variables) == 1

    def test_sp1_EF_default(self, sp1):
        M = sp1.create_EF()
        assert getattr(M, "non_ant_cons", None) == None
        assert len(M.s) == 2
        assert len(M.first_stage_variables) == 1

    def test_sp2_EF_noncompact(self, sp2):
        M = sp2.create_EF(compact_repn=False)
        assert len(M.non_ant_cons) == 4
        assert len(M.s) == 2
        assert len(M.first_stage_variables) == 2

    def test_sp2_EF_compact(self, sp2):
        M = sp2.create_EF(compact_repn=True)
        assert getattr(M, "non_ant_cons", None) == None
        assert len(M.s) == 2
        assert len(M.first_stage_variables) == 2

    def test_sp2_EF_default(self, sp2):
        M = sp2.create_EF()
        assert getattr(M, "non_ant_cons", None) == None
        assert len(M.s) == 2
        assert len(M.first_stage_variables) == 2


class TestScenarioFormat(object):

    def test_scenario_data_and_probability(self):
        received = {}

        def builder(data, args):
            received[data["ID"]] = dict(data)
            M = pyo.ConcreteModel()
            M.x = pyo.Var()
            M.o = pyo.Objective(expr=data["d"] * M.x)
            return M

        sp = stochastic_program(first_stage_variables=["x"])
        sp.initialize_application(app_data={"c": 1})
        sp.initialize_model(
            model_data={
                "data": {"m": 2},
                "scenarios": [
                    {"ID": "a", "data": {"d": 3}, "probability": 0.25},
                    {"ID": "b", "data": {"d": 4}, "probability": 0.75},
                ],
            },
            model_builder=builder,
        )
        probs = {b: sp.bundles[b].probability for b in sp.bundles.keys()}
        assert probs == {"a": pytest.approx(0.25), "b": pytest.approx(0.75)}

        sp.create_EF()
        assert received == {
            "a": {"c": 1, "m": 2, "d": 3, "ID": "a"},
            "b": {"c": 1, "m": 2, "d": 4, "ID": "b"},
        }

    def test_scenario_without_data(self):
        sp = stochastic_program(first_stage_variables=["x"])
        sp.initialize_model(model_data={"scenarios": [{"ID": 1, "probability": 1.0}]})
        assert sp.scenario_data[None] == {1: {"data": {}, "probability": 1.0}}

    def test_dict_of_scenarios_is_an_error(self):
        sp = stochastic_program(first_stage_variables=["x"])
        with pytest.raises(TypeError, match="must be specified with a list"):
            sp.initialize_model(model_data={"scenarios": {1: {"data": {"d": 15}}}})

    def test_scenario_order_is_preserved(self):
        sp = stochastic_program(first_stage_variables=["x"])
        sp.initialize_model(
            model_data={"scenarios": [{"ID": "b"}, {"ID": "a"}, {"ID": "c"}]}
        )
        assert list(sp.scenario_data[None].keys()) == ["b", "a", "c"]

    def test_missing_ID_is_an_error(self):
        sp = stochastic_program(first_stage_variables=["x"])
        with pytest.raises(ValueError, match="missing the required 'ID' key"):
            sp.initialize_model(model_data={"scenarios": [{"data": {"d": 15}}]})

    def test_duplicate_ID_is_an_error(self):
        sp = stochastic_program(first_stage_variables=["x"])
        with pytest.raises(ValueError, match="Duplicate scenario ID '1'"):
            sp.initialize_model(model_data={"scenarios": [{"ID": 1}, {"ID": 1}]})

    def test_scenario_must_be_a_dict(self):
        sp = stochastic_program(first_stage_variables=["x"])
        with pytest.raises(ValueError, match="Scenario 0 .* must be a dictionary"):
            sp.initialize_model(model_data={"scenarios": [1]})

    def test_unexpected_scenario_key_is_an_error(self):
        sp = stochastic_program(first_stage_variables=["x"])
        with pytest.raises(ValueError, match="unexpected keys"):
            sp.initialize_model(
                model_data={"scenarios": [{"ID": 1, "d": 15, "Probability": 0.1}]}
            )

    def test_scenario_data_must_be_a_dict(self):
        sp = stochastic_program(first_stage_variables=["x"])
        with pytest.raises(ValueError, match="'data' value .* must be a dictionary"):
            sp.initialize_model(model_data={"scenarios": [{"ID": 1, "data": 15}]})

    def test_ID_is_reserved(self):
        def builder(data, args):
            M = pyo.ConcreteModel()
            M.x = pyo.Var()
            M.o = pyo.Objective(expr=M.x)
            return M

        sp = stochastic_program(first_stage_variables=["x"])
        sp.initialize_model(
            model_data={"scenarios": [{"ID": 1, "data": {"ID": 2}}]},
            model_builder=builder,
        )
        with pytest.raises(AssertionError, match="reserved"):
            sp.create_EF()
