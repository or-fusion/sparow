"""
Driver for test_ph_mpi.py.  Run under MPI, e.g.

    mpiexec -n 6 python run_ph_mpi.py highs output.json

Solves a simple newsvendor problem with 5 scenarios, using 
ProgressiveHedgingSolver_MPI and, on rank 0, also with the serial
ProgressiveHedgingSolver, then writes both results to a JSON file for
comparison.
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


def main(solver, outfile):
    options = dict(max_iterations=1000, solver=solver, loglevel="INFO")

    mpi_results = ProgressiveHedgingSolver_MPI().solve(simple_newsvendor().sp, **options)

    if MPI.COMM_WORLD.Get_rank() == 0:
        serial_results = ProgressiveHedgingSolver().solve(simple_newsvendor().sp, **options)
        with open(outfile, "w") as OUTPUT:
            json.dump(
                dict(mpi=summarize(mpi_results), serial=summarize(serial_results)), OUTPUT
            )
    else:
        assert mpi_results is None


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
