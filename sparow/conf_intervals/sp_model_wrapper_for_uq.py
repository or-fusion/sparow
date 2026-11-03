"""
This class is intended to satisfy StochasticProgramModelProtocol.
Conceptually: the protocol defines the interface, while the SPModelWrapperforUQ class
is a concrete, reusable implementation of that interface.

SPModelWrapperforUQ does not need to import or subclass StochasticProgramModelProtocol in
order to satisfy it. Rather, it needs to implement the required methods with compatible
signatures. The protocol is mainly there so that type checkers and
runtime isinstance(..., ProtocolClass) checks can verify compatibility,
"""

from __future__ import annotations

import itertools
from typing import Any, Dict, List, Optional

from sparow.ef import ExtensiveFormSolver
from sparow.sp import stochastic_program

from sparow.conf_intervals.protocols import (
    ScenarioPopulationProtocol,
    ScenarioSamplerProtocol,
)


class SPModelWrapperforUQ:
    """
    Wrapper for a single SPAROW stochastic-program model to support
    confidence interval estimation and uncertainty quantification.

    This object is not the underlying SPAROW StochasticProgram itself.
    It is a higher-level wrapper that combines:
      - one stochastic-program model builder,
      - one finite scenario population,
      - one scenario sampler,
      - one fidelity label,
      - and the replication-level solve/evaluate logic needed by
        MRP, ACV-MRP, and PyApprox.
    """

    def __init__(
        self,
        sp,
        scenario_population: ScenarioPopulationProtocol,
        scenario_sampler: ScenarioSamplerProtocol,
        fidelity: str = "high",
        name: Optional[str] = None,
    ):
        """
        Parameters
        ----------
        sp : StochasticProgram
            A SPAROW stochastic program, e.g. created with
            ``sparow.sp.stochastic_program()``.  It is used as a template:
            the model name, model builder, application data, model-level
            data and first-stage variables are extracted from it.  Its
            scenarios (if any) are not used; scenarios are drawn from the
            scenario sampler.
        scenario_population : ScenarioPopulationProtocol
            The finite scenario population associated with this model.
        scenario_sampler : ScenarioSamplerProtocol
            The sampler used to draw scenario batches for this model.
        fidelity : str, optional
            The fidelity label, e.g. 'high', 'low' (default is 'high').
        name : str, optional
            The name of the model in ``sp`` to wrap.  Defaults to the
            default model of ``sp``.
        """
        if not isinstance(scenario_population, ScenarioPopulationProtocol):
            raise TypeError(
                "scenario_population must satisfy ScenarioPopulationProtocol."
            )
        if not isinstance(scenario_sampler, ScenarioSamplerProtocol):
            raise TypeError("scenario_sampler must satisfy ScenarioSamplerProtocol.")

        model_builders = getattr(sp, "model_builder", None)
        if not isinstance(model_builders, dict) or not hasattr(
            sp, "first_stage_variables"
        ):
            raise TypeError(
                "sp must be a SPAROW stochastic program created with "
                "sparow.sp.stochastic_program()."
            )

        if name is None:
            name = sp.default_model
        if name not in model_builders:
            raise ValueError(
                f"The stochastic program does not have a model builder for "
                f"model '{name}'.  Call sp.initialize_model(name=..., "
                f"model_builder=...) before creating SPModelWrapperforUQ."
            )

        self._name = name
        self._fidelity = fidelity
        self._scenario_population = scenario_population
        self._scenario_sampler = scenario_sampler
        self._model_builder = model_builders[name]
        self._app_data = dict(sp.app_data)
        self._model_level_data = dict(sp.model_data.get(name, {}))
        self._first_stage_variables = list(sp.first_stage_variables or [])

        # Validate the stored scenario population once at construction time.
        self._scenario_population.validate()

        self._first_stage_variable_order = None

    def X_compute_first_stage_variable_order(self) -> List[str]:
        """
        Build a single-scenario stochastic program from one scenario in the
        population and return the expanded first-stage variable names, in
        the order expected by sp.evaluate(x=...).
        """
        scenarios = self._scenario_population.scenarios()
        if len(scenarios) == 0:
            raise ValueError("Scenario population must be nonempty.")
        sid, scen = next(iter(scenarios.items()))

        sp = self._build_stochastic_program(self.build_model_data({sid: scen}))
        sp.create_subproblem(next(iter(sp.bundles)))
        return [
            sp.int_to_FirstStageVarName[i]
            for i in range(len(sp.int_to_FirstStageVarName))
        ]

    # ------------------------------------------------------------------
    # Basic metadata
    # ------------------------------------------------------------------

    def name(self) -> str:
        """
        Return the model name.
        """
        return self._name

    def fidelity(self) -> str:
        """
        Return the fidelity label, e.g. 'high', 'low', etc..
        """
        return self._fidelity

    def scenario_population(self) -> ScenarioPopulationProtocol:
        """
        Return the finite scenario population associated with this model.
        """
        return self._scenario_population

    def scenario_sampler(self) -> ScenarioSamplerProtocol:
        """
        Return the sampler used to draw scenario batches for this model.
        """
        return self._scenario_sampler

    def model_builder(self):
        """
        Return the underlying SPAROW model-builder function.
        """
        return self._model_builder

    def app_data(self) -> Dict[str, Any]:
        """
        Return the application data dictionary that is used to
        initialize the stochastic program.
        """
        return self._app_data

    def first_stage_variables(self) -> List[str]:
        """
        Return the high-level first-stage variables passed to SPAROW.
        """
        return self._first_stage_variables

    def first_stage_variable_order(self) -> List[str]:
        """
        Return the ordered first-stage variable names used to encode
        the first-stage candidate solution, xhat.  This ordering is
        derived from the stochastic program and matches the ordering
        expected by sp.evaluate(x=...).
        """
        return self._first_stage_variable_order

    # ------------------------------------------------------------------
    # Functions for drawing scenario batches and building model data
    # ------------------------------------------------------------------

    def draw_batch_of_scenarios(
        self,
        n: int,
        replication_id: int,
        nested_sampling: bool = False,
        precomputed_supersets: Optional[Dict[int, Dict[Any, Dict[str, Any]]]] = None,
    ) -> Dict[Any, Dict[str, Any]]:
        """
        Draw one scenario batch of scenarios for a replication. If not using a
        precomputed superset, internally calls to self._scenario_sampler.draw_scenarios
        to actually draw the scenarios.

        Parameters
        ----------
        n : int
            Batch size.
        replication_id : int
            Replication index used for reproducible sampling.
        nested_sampling : bool, optional
            Whether to use a precomputed superset and truncate it to size n.
            This is useful for numerical experiments where we vary/ increment
            batch size n and want to keep the same underlying superset of scenarios for comparability.
        precomputed_supersets : dict, optional
            Mapping from replication id to a precomputed dictionary of scenarios.

        Returns
        -------
        dict
            Native SPAROW representation for a scenario batch, i.e. a
            dictionary that maps scenario IDs to scenario specifications.
        """
        if nested_sampling:

            if precomputed_supersets is None:
                raise RuntimeError(
                    "nested_sampling=True requires precomputed_supersets."
                )
            if replication_id not in precomputed_supersets:
                raise RuntimeError(
                    f"Missing precomputed superset for replication {replication_id}."
                )

            # Nested sampling keeps the same underlying superset and takes
            # its first n scenarios.... so results are comparable across
            # different values.
            sampled_scenarios = dict(
                itertools.islice(precomputed_supersets[replication_id].items(), n)
            )

        else:
            sampled_scenarios = self._scenario_sampler.draw_scenarios(
                n=n,
                replication_id=replication_id,
            )

        self._scenario_population.validate(sampled_scenarios)

        return sampled_scenarios

    def build_model_data(
        self, sampled_scenarios: Dict[Any, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build the model_data dictionary expected by SPAROW.

        Sampled scenarios may contain metadata (e.g. 'Original_ID' and
        'Population_Index'), which is excluded from the SPAROW model data.
        Model-level data from the stochastic program used to construct
        this wrapper is included under the 'data' key.
        """
        scenarios = {
            sid: {k: v for k, v in scen.items() if k in ("data", "probability")}
            for sid, scen in sampled_scenarios.items()
        }
        return {"data": dict(self._model_level_data), "scenarios": scenarios}

    # ------------------------------------------------------------------
    # Solver / evaluation helpers
    # ------------------------------------------------------------------

    def _build_stochastic_program(self, model_data: Dict[str, Any]):
        """
        Build and return a SPAROW stochastic_program object for this model.
        """
        sp = stochastic_program(first_stage_variables=self._first_stage_variables)
        sp.initialize_application(app_data=self._app_data)
        sp.initialize_model(
            name=self._name,
            model_data=model_data,
            model_builder=self._model_builder,
        )
        return sp

    def solve_extensive_form(
        self,
        model_data: Dict[str, Any],
        solver_name: str,
        solver_options: Optional[Dict[str, Any]] = None,
        loglevel: str = "INFO",
    ) -> Dict[str, Any]:
        """
        Solve the Sample Average Approximationextensive form for
        the supplied model data.

        Returns
        -------
        dict
            Solver results converted to dictionary form.
        """
        solver = ExtensiveFormSolver()
        solver_kwargs = {"solver": solver_name, "loglevel": loglevel}

        if solver_options is not None:
            solver_kwargs.update(solver_options)

        solver.set_options(**solver_kwargs)

        sp = self._build_stochastic_program(model_data)
        results = solver.solve(sp)

        self._first_stage_variable_order = list(
            sorted(sp.get_variable_name(i) for i, _ in enumerate(sp.get_variables()))
        )

        return results.to_dict()

    def get_objective_value(self, solved_object: Dict[str, Any]) -> float:
        """
        Extract the objective value from a SPAROW results dictionary.
        """
        try:
            return solved_object["pool_config"]["best_value"]

        except Exception as exc:
            raise RuntimeError(
                "Could not get objective value from solved_object['pool_config']['best_value']."
            ) from exc

    def get_first_stage_solution(
        self, solved_object: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Extract the first-stage candidate solution xhat returned from solver output
        when running candidate generation code.
        """
        try:
            variables = solved_object["solutions"][0]["variables"]
        except Exception as exc:
            raise RuntimeError(
                "Could not find candidate first-stage variables in solved_object['solutions'][0]['variables']."
            ) from exc

        order = self.first_stage_variable_order()
        xhat = {}

        for var in variables:
            name = var["name"]
            if name in order:
                xhat[name] = var["value"]

        missing = [name for name in order if name not in xhat]
        if missing:
            raise RuntimeError(
                f"Could not extract all first-stage vars from solved_object. Missing: {missing}"
            )

        return xhat

    def first_stage_solution_dict_to_vector(
        self, xhat: Dict[str, float]
    ) -> List[float]:
        """
        Convert an xhat dictionary into the ordered vector expected by sp.evaluate(...).
        """
        missing = [
            name for name in self.first_stage_variable_order() if name not in xhat
        ]
        if missing:
            raise RuntimeError(
                f"xhat is missing required first-stage variable(s): {missing}"
            )

        return [xhat[name] for name in self.first_stage_variable_order()]

    def evaluate_first_stage_solution(
        self,
        xhat: Dict[str, float],
        model_data: Dict[str, Any],
        solver_name: str,
        solver_options: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Evaluate a fixed first-stage candidate solution on the supplied model data.

        Returns
        -------
        float
            Objective value of the fixed first-stage candidate solution.
        """
        sp = self._build_stochastic_program(model_data)
        sp.set_solver(solver_name)

        x_vector = self.first_stage_solution_dict_to_vector(xhat)

        eval_result = sp.evaluate(
            x=x_vector,
            solver_options={} if solver_options is None else solver_options,
            cached=False,
        )

        if not eval_result.feasible:
            raise RuntimeError(
                f"Fixed first-stage candidate solution evaluated infeasible on bundle/scenario {eval_result.bundle}."
            )

        return eval_result.objective

    # ------------------------------------------------------------------
    # Replication-level logic
    # ------------------------------------------------------------------

    def solve_saa(
        self,
        sampled_scenarios: Dict[Any, Dict[str, Any]],
        solver_name: str,
        solver_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Solve the SAA problem on one sampled scenario batch.

        This is a convenience wrapper around build_model_data and
        solve_extensive_form.
        """
        model_data = self.build_model_data(sampled_scenarios)
        return self.solve_extensive_form(
            model_data=model_data,
            solver_name=solver_name,
            solver_options=solver_options,
        )

    def evaluate_xhat(
        self,
        xhat: Dict[str, float],
        sampled_scenarios: Dict[Any, Dict[str, Any]],
        solver_name: str,
        solver_options: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Evaluate a fixed first-stage candidate solution on one sampled scenario batch.
        """
        model_data = self.build_model_data(sampled_scenarios)
        return self.evaluate_first_stage_solution(
            xhat=xhat,
            model_data=model_data,
            solver_name=solver_name,
            solver_options=solver_options,
        )

    def replication_gap(
        self,
        xhat: Dict[str, float],
        sampled_scenarios: Dict[Any, Dict[str, Any]],
        solver_name: str,
        solver_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        Compute one replication-level gap estimate on one sampled batch of scenarios.

        Returns
        -------
        dict
            Keys:
              - gap_estimate
              - xhat_value
              - saa_optimal_value
        """
        solved_saa = self.solve_saa(
            sampled_scenarios=sampled_scenarios,
            solver_name=solver_name,
            solver_options=solver_options,
        )
        saa_optimal_value = self.get_objective_value(solved_saa)

        xhat_value = self.evaluate_xhat(
            xhat=xhat,
            sampled_scenarios=sampled_scenarios,
            solver_name=solver_name,
            solver_options=solver_options,
        )

        gap_estimate = xhat_value - saa_optimal_value

        return {
            "gap_estimate": gap_estimate,
            "xhat_value": xhat_value,
            "saa_optimal_value": saa_optimal_value,
        }
