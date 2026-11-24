"""
Driver for test_ph_mpi.py.  Run under MPI, e.g.

    mpiexec -n 3 python run_ph_mpi.py highs output.json

Solves newsvendor problems using ProgressiveHedgingSolver_MPI and, on rank 0,
also with the serial ProgressiveHedgingSolver, then writes both results to a
JSON file for comparison.  Several configurations are exercised; the JSON file
maps each configuration name to its {"mpi": ..., "serial": ...} results.
"""

import json
import sys

from mpi4py import MPI

from sparow.ph import ProgressiveHedgingSolver, ProgressiveHedgingSolver_MPI
from sparow.sp.examples import HF_newsvendor, MFrandom_newsvendor, simple_newsvendor


def summarize(results):
    soln = results.last_solution
    return dict(
        objective=soln.objective().value,
        xbar=[v.value for v in soln.variables()],
    )


# A harmless (non-binding) option for each supported solver, used to check that
# solver_options are passed through to both the search and finalize solves.
TIME_LIMIT_OPTION = {
    "gurobi": {"TimeLimit": 100},
    "highs": {"time_limit": 100.0},
}


def simple_problem():
    """
    The simple newsvendor problem (5 bundles), used for both search and
    finalization.  Returns the arguments for solve().
    """
    return dict(sp_finalize=simple_newsvendor().sp)


def multifidelity_problem():
    """
    Search with a bundled multi-fidelity newsvendor model, and finalize with
    the high-fidelity model, whose bundles differ from the search bundles.
    Returns the arguments for solve().
    """
    return dict(
        sp_finalize=HF_newsvendor().sp,
        mf_sp=MFrandom_newsvendor(with_bundles=True).sp,
    )


def configurations(solver):
    """
    Returns a dictionary that maps configuration names to (problem, options)
    tuples, where problem() returns the arguments for solve().
    """
    base = dict(max_iterations=10, solver=solver, loglevel="WARN")
    return {
        # Finalize only the last PH iterate (one parallel evaluation)
        "default": (simple_problem, dict(base)),
        # Finalize every PH iterate (one parallel evaluation per iteration).
        # Fewer iterations keep the serial finalization affordable.
        "finalize_all_xbar": (
            simple_problem,
            dict(base, max_iterations=10, finalize_all_xbar=True),
        ),
        # Pass solver options to the subproblem solves
        "solver_options": (
            simple_problem,
            dict(base, solver_options=TIME_LIMIT_OPTION[solver]),
        ),
        # Search with a multi-fidelity model (mf_sp), and finalize with a
        # different model
        "mf_sp": (multifidelity_problem, dict(base)),
    }


def main(solver, outfile):
    rank = MPI.COMM_WORLD.Get_rank()
    output = {}
    for name, (problem, options) in configurations(solver).items():
        mpi_results = ProgressiveHedgingSolver_MPI().solve(**problem(), **options)

        if rank == 0:
            serial_results = ProgressiveHedgingSolver().solve(**problem(), **options)
            output[name] = dict(
                mpi=summarize(mpi_results), serial=summarize(serial_results)
            )
        else:
            assert mpi_results is None

    if rank == 0:
        with open(outfile, "w") as OUTPUT:
            json.dump(output, OUTPUT)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
