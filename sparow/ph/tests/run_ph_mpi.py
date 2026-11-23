"""
Driver for test_ph_mpi.py.  Run under MPI, e.g.

    mpiexec -n 6 python run_ph_mpi.py highs output.json

Solves a simple newsvendor problem with 5 scenarios, using
ProgressiveHedgingSolver_MPI and, on rank 0, also with the serial
ProgressiveHedgingSolver, then writes both results to a JSON file for
comparison.  Several solver configurations are exercised; the JSON file maps
each configuration name to its {"mpi": ..., "serial": ...} results.
"""

import json
import sys

from mpi4py import MPI

from sparow.ph import ProgressiveHedgingSolver, ProgressiveHedgingSolver_MPI
from sparow.sp.examples import simple_newsvendor


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


def configurations(solver):
    base = dict(max_iterations=1000, solver=solver, loglevel="WARN")
    return {
        # Finalize only the last PH iterate (one parallel evaluation)
        "default": dict(base),
        # Finalize every PH iterate (one parallel evaluation per iteration).
        # Fewer iterations keep the serial finalization affordable.
        "finalize_all_xbar": dict(base, max_iterations=20, finalize_all_xbar=True),
        # Pass solver options to the subproblem solves
        "solver_options": dict(base, solver_options=TIME_LIMIT_OPTION[solver]),
    }


def main(solver, outfile):
    rank = MPI.COMM_WORLD.Get_rank()
    output = {}
    for name, options in configurations(solver).items():
        mpi_results = ProgressiveHedgingSolver_MPI().solve(
            simple_newsvendor().sp, **options
        )

        if rank == 0:
            serial_results = ProgressiveHedgingSolver().solve(
                simple_newsvendor().sp, **options
            )
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
