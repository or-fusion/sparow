from .sp_pyomo import (
    # StochasticProgram_Pyomo_MultistageBuilder,
    StochasticProgram_Pyomo_NamedBuilder,
)


def stochastic_program(*, first_stage_variables=None):
    """
    Create a stochastic program using the specified modeling framework.

    Parameters
    ----------
    first_stage_variables : list, optional
        A list of strings that denote the first-stage variables in the model.

    Returns
    -------
    StochasticProgram_Pyomo_NamedBuilder
        An instance of the stochastic program builder.

    Raises
    ------
    RuntimeError
        If the specified AML is not supported.
    """
    return StochasticProgram_Pyomo_NamedBuilder(
        first_stage_variables=first_stage_variables
    )
