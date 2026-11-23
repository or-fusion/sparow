"""
An MPI-parallel variant of ProgressiveHedgingSolver.

Subproblem solves are distributed with mpi4py using a simple coordinator/worker
scheme:

* Rank 0 is the coordinator.  It computes xbar, w, rho and the convergence
  metrics, archives solutions and finalizes the results.
* Rank r (1 <= r <= N) owns bundle r-1 and repeatedly builds and solves that
  single subproblem.
* Ranks > N are idle; they simply participate in the collective calls.

This requires at least N+1 MPI processes, where N is the number of bundles.

The solver is used in SPMD style: every rank executes the same script, builds
the same stochastic program and calls ``solve()``.  For example:

    mpiexec -n 4 python my_script.py      # for a model with 3 bundles

``solve()`` returns the solution pool on rank 0 and ``None`` on all other ranks.
"""

import datetime
import logging
import pprint
import sys
import traceback

from pyomo.common.timing import tic, toc, TicTocTimer
import sparow.logs
from sparow import solnpool
from sparow.ph.ph import ProgressiveHedgingSolver, finalize_ph_results, norm

logger = sparow.logs.logger

_SOLVE = "solve"
_STOP = "stop"


class _GatheredValuesSP(object):
    """
    A thin proxy around a StochasticProgram that answers get_variable_value()
    from first-stage values gathered from the worker ranks.  All other
    attributes are delegated to the wrapped stochastic program.

    This lets the coordinator reuse ProgressiveHedgingSolver.update_rho(),
    which reads variable values through the stochastic program, even though
    the coordinator never solves the subproblems itself.
    """

    def __init__(self, sp, xvals):
        self._sp = sp
        self._xvals = xvals

    def get_variable_value(self, b, v):
        return self._xvals[b][v]

    def __getattr__(self, name):
        return getattr(self._sp, name)


class ProgressiveHedgingSolver_MPI(ProgressiveHedgingSolver):
    """
    A progressive hedging solver that solves the bundle subproblems in
    parallel using mpi4py.

    The algorithm (and all options) are identical to ProgressiveHedgingSolver;
    only the location of the subproblem solves changes.

    Parameters
    ----------
    comm : mpi4py.MPI.Comm, optional
        The communicator to use (default is MPI.COMM_WORLD).
    """

    def __init__(self, comm=None):
        super().__init__()
        if comm is None:
            from mpi4py import MPI

            comm = MPI.COMM_WORLD
        self.comm = comm
        self.rank = comm.Get_rank()
        self.size = comm.Get_size()

    #
    # Setup
    #

    def _synchronize_bundles(self, sp):
        """
        Verify that every rank built identical bundles, and confirm that there
        are enough processes.  Returns the ordered list of bundle ids.

        All ranks reach the same conclusion, so errors are raised consistently
        everywhere (no rank is left blocked in a collective call).
        """
        from mpi4py import MPI

        comm = self.comm
        # Note: sp.bundles is lazily initialized, so touch it on every rank.
        local_ids = list(sp.bundles)
        bundle_ids = comm.bcast(local_ids if self.rank == 0 else None, root=0)
        reference = comm.bcast(sp.get_bundles() if self.rank == 0 else None, root=0)

        local_ok = local_ids == bundle_ids and sp.get_bundles() == reference
        all_ok = comm.allreduce(local_ok, op=MPI.LAND)
        if not all_ok:
            raise RuntimeError(
                "ProgressiveHedgingSolver_MPI: the bundles differ across MPI ranks. "
                "Every rank must construct identical bundles (e.g. seed any "
                "randomized bundling scheme)."
            )

        nbundles = len(bundle_ids)
        if self.size < nbundles + 1:
            raise RuntimeError(
                f"ProgressiveHedgingSolver_MPI requires at least {nbundles + 1} MPI "
                f"processes for {nbundles} bundles (1 coordinator + 1 per bundle), "
                f"but only {self.size} are available."
            )
        return bundle_ids

    #
    # Worker logic
    #

    def _worker_loop(self, sp, bundle_ids):
        """
        Receive work from the coordinator until told to stop.
        """
        comm = self.comm
        b = bundle_ids[self.rank - 1] if self.rank <= len(bundle_ids) else None

        while True:
            msg = comm.scatter(None, root=0)
            if msg["cmd"] == _STOP:
                return

            if b is None:
                # Idle rank
                comm.gather(None, root=0)
                continue

            try:
                M = sp.create_subproblem(
                    b=b,
                    w=msg["w"],
                    x_bar=msg["xbar"],
                    rho=msg["rho"],
                    cached=self.cached_model_generation,
                )
                results = sp.solve(M, solver_options=self.solver_options)
                if results.obj_value is None:
                    reply = dict(
                        bundle=b,
                        error=(
                            f"subproblem solve failed: "
                            f"status={results.status} "
                            f"termination_condition={results.termination_condition}"
                        ),
                    )
                else:
                    reply = dict(
                        bundle=b,
                        error=None,
                        obj_value=results.obj_value,
                        x={
                            x: sp.get_variable_value(b, x)
                            for x in sp.shared_variables()
                        },
                    )
            except Exception:
                reply = dict(bundle=b, error=traceback.format_exc())

            comm.gather(reply, root=0)

    #
    # Coordinator logic
    #

    def _solve_subproblems(self, bundle_ids, *, iteration, w=None, xbar=None):
        """
        Dispatch one round of subproblem solves to the workers and gather the
        results.  Returns (obj_value, xvals) dictionaries indexed by bundle.
        """
        comm = self.comm
        nbundles = len(bundle_ids)
        rho = self.rho if xbar is not None else None

        payload = [None] * self.size
        for r in range(1, self.size):
            if r <= nbundles:
                b = bundle_ids[r - 1]
                payload[r] = dict(
                    cmd=_SOLVE,
                    w=None if w is None else w[b],
                    xbar=xbar,
                    rho=rho,
                )
            else:
                payload[r] = dict(cmd=_SOLVE)
        comm.scatter(payload, root=0)
        replies = comm.gather(None, root=0)

        obj_value = {}
        xvals = {}
        errors = []
        for reply in replies[1 : nbundles + 1]:
            b = reply["bundle"]
            if reply["error"] is not None:
                errors.append(f"bundle {b}: {reply['error']}")
                continue
            obj_value[b] = reply["obj_value"]
            xvals[b] = reply["x"]
            logger.verbose(f"Received results for subproblem {b}")

        if errors:
            raise RuntimeError(
                f"ERROR solving subproblems in iteration {iteration}:\n"
                + "\n".join(errors)
            )
        return obj_value, xvals

    def _stop_workers(self):
        stop = dict(cmd=_STOP)
        self.comm.scatter([stop] * self.size, root=0)

    def solve(self, sp_finalize, mf_sp=None, **options):
        """
        Solve a stochastic program using MPI-parallel progressive hedging.

        Must be called collectively on all ranks of the communicator.

        Parameters
        ----------
        sp_finalize : StochasticProgram
            The stochastic program to solve.
        mf_sp : StochasticProgram
            The multi-fidelity stochastic approximation used to for search.
            If this is None, then 'sp_finalize' is used for search.
        **options : dict
            Additional options for the solver.

        Returns
        -------
        object or None
            The solution pool manager on rank 0, and None on all other ranks.
        """
        if len(options) > 0:
            self.set_options(**options)

        if self.solver_name:
            sp_finalize.set_solver(self.solver_name)
            if mf_sp:
                mf_sp.set_solver(self.solver_name)

        # Identify the stochastic program used for search
        sp = mf_sp if mf_sp else sp_finalize

        bundle_ids = self._synchronize_bundles(sp)

        if self.rank != 0:
            self._worker_loop(sp, bundle_ids)
            return None

        try:
            return self._coordinator_solve(sp_finalize, mf_sp, sp, bundle_ids)
        finally:
            # Release the workers, whether we finished normally or raised.
            self._stop_workers()

    def _coordinator_solve(self, sp_finalize, mf_sp, sp, bundle_ids):
        start_time = datetime.datetime.now()
        if logger.isEnabledFor(logging.DEBUG):
            print("Solver Configuration")
            print(f"  mpi_processes              {self.size}")
            print(f"  bundles                    {len(bundle_ids)}")
            print(f"  cached_model_generation    {self.cached_model_generation}")
            print(f"  convergence_norm           {self.convergence_norm}")
            print(f"  convergence_tolerance      {self.convergence_tolerance}")
            print(f"  finalize_xbar_by_rounding  {self.finalize_xbar_by_rounding}")
            print(f"  finalize_all_xbar          {self.finalize_all_xbar}")
            print(f"  max_iterations             {self.max_iterations}")
            print(f"  normalize_convergence_norm {self.normalize_convergence_norm}")
            print(f"  rho                        {self.rho}")
            print(f"  solver_name                {self.solver_name}")
            print("")

        #
        # Setup solution manager and archive context information
        #
        if self.solutions is None:
            self.solutions = solnpool.SparowPoolManager()
        if self.finalize_all_xbar:
            sp_metadata = self.solutions.add_pool(
                name="PH Iterations", policy=solnpool.PoolPolicy.keep_all
            )
        else:
            sp_metadata = self.solutions.add_pool(
                name="PH Iterations", policy=solnpool.PoolPolicy.keep_latest
            )
        sp_metadata.solver = "PH Iteration Results"
        sp_metadata.solver_options = dict(
            cached_model_generation=self.cached_model_generation,
            max_iterations=self.max_iterations,
            convergence_tolerance=self.convergence_tolerance,
            normalize_convergence_norm=self.normalize_convergence_norm,
            solver_name=self.solver_name,
            solver_options=self.solver_options,
            mpi_processes=self.size,
        )

        #
        # The coordinator never solves a subproblem during search, but it needs
        # the first-stage variable metadata (indices, names, integrality), which
        # is initialized when a subproblem is created.  Build one (unsolved).
        #
        sp.create_subproblem(bundle_ids[0], cached=self.cached_model_generation)
        sfs_variables = sp.shared_variables()

        logger.info("ProgressiveHedgingSolver_MPI - START")
        iteration_timer = TicTocTimer()
        iteration_timer.tic(None)

        # Step 2
        tic("Initial subproblems", logger=logger, level=logging.VERBOSE)
        obj_value, xvals = self._solve_subproblems(bundle_ids, iteration=0)
        toc("Initial subproblems - DONE", logger=logger, level=logging.VERBOSE)
        self._check_variables(xvals, sfs_variables)
        obj_lb = sum(sp.bundles[b].probability * obj_value[b] for b in bundle_ids)

        # Step 3
        xbar = {}
        for x in sfs_variables:
            xbar[x] = sum(sp.bundles[b].probability * xvals[b][x] for b in bundle_ids)
        self.update_rho(sfs_variables, xbar, _GatheredValuesSP(sp, xvals))

        # Step 4
        w = {}
        for b in bundle_ids:
            w[b] = {}
            for x in sfs_variables:
                w[b][x] = self.rho[x] * (xvals[b][x] - xbar[x])

        # Step 4.1
        iteration = 0
        termination_condition = "Termination: unknown"
        latest_soln = self.archive_solution(
            sp=sp, xbar=xbar, w=w, iteration=iteration, obj_lb=obj_lb
        )
        time_last_iter = iteration_timer.toc(None)
        self.log_iteration(
            iteration=iteration,
            obj_lb=obj_lb,
            time=datetime.datetime.now(),
            time_last_iter=time_last_iter,
            xbar=xbar,
            rho=self.rho,
            w=w,
        )

        while True:
            iteration_timer.tic(None)
            iteration += 1

            # Step 5
            xbar_prev = xbar
            w_prev = w

            # Step 6
            tic(
                f"Subproblems for iteration {iteration}",
                logger=logger,
                level=logging.VERBOSE,
            )
            obj_value, xvals = self._solve_subproblems(
                bundle_ids, iteration=iteration, w=w_prev, xbar=xbar_prev
            )
            toc(
                f"Subproblems for iteration {iteration} - DONE",
                logger=logger,
                level=logging.VERBOSE,
            )
            obj_lb = sum(sp.bundles[b].probability * obj_value[b] for b in bundle_ids)

            # Step 7
            xbar = {}
            for x in sfs_variables:
                xbar[x] = sum(
                    sp.bundles[b].probability * xvals[b][x] for b in bundle_ids
                )
            logger.debug(f"xbar = {xbar}")

            self.update_rho(sfs_variables, xbar, _GatheredValuesSP(sp, xvals))
            logger.debug(f"rho = {self.rho}")

            # Step 8
            w = {}
            for b in bundle_ids:
                w[b] = {}
                for x in sfs_variables:
                    w[b][x] = w_prev[b][x] + self.rho[x] * (xvals[b][x] - xbar[x])
                logger.debug(f"w[{b}] = {w[b]}")

            # Step 9
            g = sum(
                sp.bundles[b].probability
                * norm(
                    [xvals[b][x] - xbar[x] for x in sfs_variables],
                    self.convergence_norm,
                )
                for b in bundle_ids
            )
            if self.normalize_convergence_norm:
                g /= len(sfs_variables)
            logger.info(f"g = {g}")

            G = norm(
                [xbar[x] - xbar_prev[x] for x in sfs_variables], self.convergence_norm
            )
            if self.normalize_convergence_norm:
                G /= len(sfs_variables)
            logger.info(f"G = {G}")

            # Step 9.1
            tic(
                f"Archiving solution: {iteration}", logger=logger, level=logging.VERBOSE
            )
            latest_soln = self.archive_solution(
                sp=sp, xbar=xbar, w=w, iteration=iteration, obj_lb=obj_lb, g=g
            )
            toc(f"Archiving solution - DONE", logger=logger, level=logging.VERBOSE)

            time_last_iter = iteration_timer.toc(None)
            self.log_iteration(
                iteration=iteration,
                obj_lb=obj_lb,
                time=datetime.datetime.now(),
                time_last_iter=time_last_iter,
                xbar=xbar,
                rho=self.rho,
                g=g,
                G=G,
                w=w,
            )

            # Step 10
            if G + g < self.convergence_tolerance:
                termination_condition = f"Termination: convergence tolerance ({G} + {g} < {self.convergence_tolerance})"
                logger.info(termination_condition)
                break

            if iteration >= self.max_iterations:
                termination_condition = f"Termination: max_iterations ({iteration} == {self.max_iterations})"
                logger.info(termination_condition)
                break

        end_time = datetime.datetime.now()

        sp_metadata = self.solutions.metadata
        sp_metadata.iterations = iteration
        sp_metadata.termination_condition = termination_condition
        sp_metadata.start_time = str(start_time)

        #
        # Finalization is performed serially on the coordinator.
        #
        logger.info("")
        logger.info("-" * 70)
        logger.info("ProgressiveHedgingSolver_MPI - FINALIZING")

        if mf_sp is not None:
            # Initialize the model logic in sp_finalize if it hasn't been used yet
            for b in sp_finalize.bundles:
                sp_finalize.create_subproblem(b, cached=self.cached_model_generation)

        if self.finalize_all_xbar:
            all_iterations = list(self.solutions)
            self.solutions.add_pool(
                name="Finalized All PH Iterations",
                policy=solnpool.PoolPolicy.keep_all,
            )
            for soln in all_iterations:
                finalize_ph_results(soln, sp=sp_finalize, solutions=self.solutions)
        else:
            soln = self.solutions[latest_soln]
            self.solutions.add_pool(
                name="Finalized Last PH Solution",
                policy=solnpool.PoolPolicy.keep_best,
            )
            finalize_ph_results(soln, sp=sp_finalize, solutions=self.solutions)

        sp_metadata.end_time = str(end_time)
        sp_metadata.time_elapsed = str(end_time - start_time)

        logger.info("")
        logger.info("-" * 70)
        logger.info("ProgressiveHedgingSolver_MPI - RESULTS")
        if logger.isEnabledFor(logging.DEBUG):
            pprint.pprint(self.solutions.to_dict())
            sys.stdout.flush()

        logger.info("")
        logger.info("-" * 70)
        logger.info("ProgressiveHedgingSolver_MPI - STOP")

        return self.solutions

    @staticmethod
    def _check_variables(xvals, sfs_variables):
        expected = set(sfs_variables)
        for b, x in xvals.items():
            if set(x.keys()) != expected:
                raise RuntimeError(
                    f"ProgressiveHedgingSolver_MPI: bundle {b} reported first-stage "
                    f"variables {sorted(x.keys())}, expected {sorted(expected)}"
                )
