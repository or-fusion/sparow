"""
An MPI-parallel progressive hedging solver.

The PH algorithm runs on rank 0 (the master), which computes xbar, w, rho and
the convergence metrics, archives solutions and finalizes the results.  The
subproblem solves (during search) and the evaluations of candidate
first-stage points (during finalization) are executed in parallel on ranks
1, ..., size-1 by a ParallelWorker, which implements an asynchronous
master-worker scheme with dynamic load balancing.  See
sparow.ph.parallel_worker for details.

Any number of processes can be used.  Fewer workers than bundles is fine
(each worker simply solves several subproblems per iteration), and with a
single process the master executes all tasks itself.

The solver is used in SPMD style: every rank executes the same script, builds
the same stochastic program and calls ``solve()``.  For example:

    mpiexec -n 4 python my_script.py

``solve()`` returns the solution pool on rank 0 and ``None`` on all other ranks.
"""

import munch

import sparow.logs
from sparow.ph.ph import ProgressiveHedgingSolverBase
from sparow.ph.parallel_worker import ParallelWorker

logger = sparow.logs.logger


class ProgressiveHedgingSolver_MPI(ProgressiveHedgingSolverBase):
    """
    A progressive hedging solver that solves the bundle subproblems in
    parallel using mpi4py, with an asynchronous master-worker scheme.

    The algorithm (and all options) are identical to ProgressiveHedgingSolver;
    both are implemented by ProgressiveHedgingSolverBase, and only the location
    of the subproblem solves changes.  The parallel execution is delegated to
    a ParallelWorker.

    ``solve()`` must be called collectively on all ranks of the communicator.
    It returns the solution pool manager on rank 0, and None on all other
    ranks.

    In addition to the options of ProgressiveHedgingSolver, set_options()
    and solve() accept:

    worker_loglevel : str, optional
        The logging level on the worker ranks (default is "WARNING").  The
        ``loglevel`` option applies to the master.

    Parameters
    ----------
    comm : mpi4py.MPI.Comm, optional
        The communicator to use (default is MPI.COMM_WORLD).
    """

    def __init__(self, comm=None):
        super().__init__()
        self.parallel = ParallelWorker(comm)
        self.comm = self.parallel.comm
        self.rank = self.parallel.rank
        self.size = self.parallel.size
        self.worker_loglevel = "WARNING"

    def set_options(self, *, worker_loglevel=None, **options):
        """
        Set the options for the solver.  See ProgressiveHedgingSolver for
        the common options.

        Parameters
        ----------
        worker_loglevel : str, optional
            The logging level on the worker ranks.
        **options : dict
            The options of ProgressiveHedgingSolverBase.set_options().
        """
        if worker_loglevel is not None:
            self.worker_loglevel = worker_loglevel
        super().set_options(**options)

    #
    # Hooks for ProgressiveHedgingSolverBase
    #

    def _solve(self, sp_finalize, mf_sp, sp):
        """
        Set up the parallel execution, then run the PH algorithm on the
        master (rank 0) while the workers execute tasks on request.
        """
        parallel = self.parallel
        parallel.setup(
            sp,
            sp_finalize,
            check_finalize=mf_sp is not None,
            cached_model_generation=self.cached_model_generation,
            solver_options=self.solver_options,
            worker_loglevel=self.worker_loglevel,
        )

        if not parallel.is_master:
            parallel.worker_loop()
            return None

        try:
            return self._run_ph(sp_finalize, mf_sp, sp, list(sp.bundles))
        finally:
            # Release the workers, whether we finished normally or raised.
            parallel.stop()

    def _setup_search(self, sp, bundle_ids):
        #
        # The master usually doesn't solve subproblems during search, but it
        # needs the first-stage variable metadata (indices, names,
        # integrality), which is initialized when a subproblem is created.
        # Build one (unsolved).
        #
        sp.create_subproblem(bundle_ids[0], cached=self.cached_model_generation)

    def _solve_subproblems(self, sp, bundle_ids, *, iteration, w=None, xbar=None):
        """
        Solve the subproblems for all bundles on the workers.  Returns
        (obj_value, xvals) dictionaries indexed by bundle.
        """
        rho = self.rho if xbar is not None else None
        try:
            results = self.parallel.solve_subproblems(
                bundle_ids, w=w, xbar=xbar, rho=rho
            )
        except RuntimeError as e:
            raise RuntimeError(
                f"ERROR solving subproblems in iteration {iteration}:\n{e}"
            ) from None

        obj_value = {}
        xvals = {}
        expected = set(sp.shared_variables())
        for b, reply in results.items():
            if set(reply["x"].keys()) != expected:
                raise RuntimeError(
                    f"ProgressiveHedgingSolver_MPI: bundle {b} reported first-stage "
                    f"variables {sorted(reply['x'].keys())}, expected {sorted(expected)}"
                )
            obj_value[b] = reply["obj_value"]
            xvals[b] = reply["x"]
        return obj_value, xvals

    def _prepare_finalize(self, sp_finalize, mf_sp):
        if mf_sp is not None:
            # The master needs the first-stage variable metadata of
            # sp_finalize (e.g. integrality, for rounding), which is
            # initialized when a subproblem is created.  Build one (unsolved).
            sp_finalize.create_subproblem(
                self.parallel.finalize_ids[0], cached=self.cached_model_generation
            )

        def evaluate(x, solver_options=None):
            return self._parallel_evaluate(sp_finalize, x, solver_options)

        return evaluate

    def _parallel_evaluate(self, sp, x, solver_options):
        """
        A parallel drop-in replacement for sp.evaluate(x, solver_options): the
        point x is evaluated on each finalization bundle by the workers.
        """
        x = list(x)
        try:
            results = self.parallel.evaluate(x, solver_options)
        except RuntimeError as e:
            raise RuntimeError(f"ERROR evaluating a candidate solution:\n{e}") from None

        # Report the first infeasible bundle (in bundle order)
        finalize_ids = self.parallel.finalize_ids
        for b in finalize_ids:
            if b in results and results[b]["obj_value"] is None:
                logger.debug(f"Error evaluating solution for bundle {b}")
                return munch.Munch(feasible=False, bundle=b)

        obj = sum(
            sp.bundles[b].probability * results[b]["obj_value"] for b in finalize_ids
        )
        # The first-stage variables are fixed to x in every bundle
        variables = {sp.get_variable_name(i): x[i] for i in sp.shared_variables()}
        return munch.Munch(feasible=True, objective=obj, variables=variables)

    def _extra_metadata(self):
        return dict(mpi_processes=self.size)
