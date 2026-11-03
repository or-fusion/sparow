"""
This file contains a concrete implementation of a finite scenario population object.
The scenario population object is intended to satisfy:
  - ScenarioPopulationProtocol
  - ScenarioEncodingProtocol

This object stores:
  - the full dictionary of scenarios (keyed by scenario ID),
  - the required scenario keys according to native SPAROW scenario format,
  - and optional encode/decode logic for scenario vectors.
"""

from __future__ import annotations

import numpy as np
from typing import Any, Dict, List, Optional, Sequence


class FiniteScenarioPopulation:
    """
    Concrete representation of a finite population of scenarios to sample from.

    Scenarios are specified in the native SPAROW format: a dictionary that
    maps scenario IDs to scenario specifications, where each scenario
    specification is a dictionary with keys:
      - 'data': a dictionary of scenario data
      - 'probability': the scenario probability

    For example:

        {
            "s0": {"data": {"Demand": [1.0, 2.0]}, "probability": 0.5},
            "s1": {"data": {"Demand": [3.0, 4.0]}, "probability": 0.5},
        }

    This object stores:
      - the full dictionary of scenarios,
      - the required scenario data keys,
      - optional encode/decode logic for scenario vectors,
      - optional fixed metadata that is required for the given problem instance.
        These fields are not part of the uncertain scenario vector, but they
        are required when rebuilding native SPAROW scenario data.

    It is designed to be reusable across different stochastic programs.
    """

    def __init__(
        self,
        scenarios: Dict[Any, Dict[str, Any]],
        required_scenario_keys: Optional[List[str]] = None,
        scenario_vector_keys: Optional[List[str]] = None,
        fixed_metadata: Optional[Dict[str, Any]] = None,
    ):
        self._scenarios = scenarios
        self._required_scenario_keys = (
            [] if required_scenario_keys is None else list(required_scenario_keys)
        )
        self._scenario_vector_keys = (
            [] if scenario_vector_keys is None else list(scenario_vector_keys)
        )

        # These are non-random fields that are not encoded into the scenario
        # vector, but must be reattached to the scenario data when decoding
        # vectors back into native SPAROW scenarios.
        self._fixed_metadata = {} if fixed_metadata is None else dict(fixed_metadata)

        self.validate(self._scenarios)

    def scenarios(self) -> Dict[Any, Dict[str, Any]]:
        """
        Return the full finite scenario population.
        """
        return self._scenarios

    def required_scenario_keys(self) -> List[str]:
        """
        Return required scenario data keys.
        This is usually the string name identifier for uncertain problem data.
        """
        return self._required_scenario_keys

    def fixed_metadata(self) -> Dict[str, Any]:
        """
        Return the fixed metadata to be restored on decode.

        These fields are not part of the uncertain scenario vector, but they
        are required when rebuilding native SPAROW scenario data.
        """
        return dict(self._fixed_metadata)

    def validate(self, scenarios: Optional[Dict[Any, Dict[str, Any]]] = None) -> None:
        """
        Validate either the provided scenarios or the stored full population.

        The scenarios must be a dictionary mapping scenario IDs to scenario
        specifications.  Every scenario specification must be a dictionary
        containing:
          - 'probability'
          - 'data', which is a dictionary containing any user-specified
            required keys
        """
        if scenarios is None:
            scenarios = self._scenarios

        if not isinstance(scenarios, dict):
            raise RuntimeError(
                "Scenario population must be a dictionary that maps scenario "
                "IDs to scenario specifications."
            )

        for sid, scen in scenarios.items():
            if not isinstance(scen, dict):
                raise RuntimeError(f"Scenario '{sid}' is not a dictionary.")

            missing = [key for key in ("data", "probability") if key not in scen]
            if missing:
                raise RuntimeError(
                    f"Scenario '{sid}' is missing required key(s): {missing}"
                )

            data = scen["data"]
            if not isinstance(data, dict):
                raise RuntimeError(
                    f"The data for scenario '{sid}' is not a dictionary."
                )

            missing = [key for key in self._required_scenario_keys if key not in data]
            if missing:
                raise RuntimeError(
                    f"Scenario '{sid}' is missing required data key(s): {missing}"
                )

    def scenario_vector_keys(self) -> List[str]:
        """
        Return the scenario data fields used for vector encoding.

        These keys identify the uncertain scenario data fields.
        """
        return self._scenario_vector_keys

    def encode_scenario_vector(self, scenario: Dict[str, Any]) -> List[float]:
        """
        Convert one scenario specification into a flat numeric vector.

        This implementation works when the uncertain data fields listed in
        scenario_vector_keys() are numeric scalars or flat lists.
        """
        vec: List[float] = []

        for key in self.scenario_vector_keys():
            value = scenario["data"][key]

            if np.isscalar(value):
                vec.append(float(value))
            else:
                vec.extend([float(v) for v in value])

        return vec

    def decode_scenario_vector(self, vector: Sequence[float]) -> Dict[str, Any]:
        """
        Convert a flat vector back into a scenario specification.

        Note that this will contain the 'data' field, but not the
        'probability' field.  Batch-construction logic assigns the scenario
        ID and probability weight later.

        So the decoded scenario data contains:
          - the uncertain fields reconstructed from the vector,
          - any fixed metadata needed by the specific problem instance/ application.
        """
        ref = next(iter(self._scenarios.values()))["data"]

        data = dict(self._fixed_metadata)

        cursor = 0
        for key in self.scenario_vector_keys():
            ref_value = ref[key]

            if np.isscalar(ref_value):
                data[key] = float(vector[cursor])
                cursor += 1
            else:
                length = len(ref_value)
                data[key] = [float(v) for v in vector[cursor : cursor + length]]
                cursor += length

        return {"data": data}

    def scenario_vector_dim(self) -> int:
        """
        Return the dimension of one encoded scenario vector.
        """
        return len(self.encode_scenario_vector(next(iter(self._scenarios.values()))))
