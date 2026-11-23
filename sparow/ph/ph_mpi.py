"""
An MPI-parallel variant of ProgressiveHedgingSolver.

Subproblem solves are distributed with mpi4py using a simple coordinator/worker
scheme:

* Rank 0 is the coordinator.  It computes xbar, w, rho and the convergence
  metrics, archives solutions and finalizes the results.
* Rank r (1 <= r <= N) owns bundle r-1 and repeatedly builds and solves that
  single subproblem.
* Ranks > N are idle during search; they simply participate in the
  collective calls.
* During finalization, each candidate point is evaluated in parallel: the
  bundles of the finalization model are distributed round-robin over all
  worker ranks (1, ..., size-1), so idle ranks are used there too.

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

import munch

from pyomo.common.timing import tic, toc, TicTocTimer
import sparow.logs
from sparow import solnpool
from sparow.ph.ph import ProgressiveHedgingSolver, finalize_ph_results, norm

logger = sparow.logs.logger

_SOLVE = "solve"
_EVALUATE = "evaluate"
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

    def _synchronize_bundles(self, sp, *, require_worker_per_bundle=True):
        """
        Verify that every rank built identical bundles, and (optionally)
        confirm that there is one worker process per bundle.  Returns the
        ordered list of bundle ids.

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
        if self.size < 2 or (require_worker_per_bundle and self.size < nbundles + 1):
            raise RuntimeError(
                f"ProgressiveHedgingSolver_MPI requires at least {nbundles + 1} MPI "
                f"processes for {nbundles} bundles (1 coordinator + 1 per bundle), "
                f"but only {self.size} are available."
            )
        return bundle_ids

    #
    # Worker logic
    #

    def _worker_loop(self, sp, bundle_ids, sp_finalize, finalize_ids):
        """
        Receive work from the coordinator until told to stop.
        """
        comm = self.comm
        b = bundle_ids[self.rank - 1] if self.rank <= len(bundle_ids) else None
        my_finalize_ids = self._finalize_assignment(finalize_ids)[self.rank]

        while True:
            msg = comm.scatter(None, root=0)
            if msg["cmd"] == _STOP:
                return
            elif msg["cmd"] == _SOLVE:
                reply = None if b is None else self._worker_solve(sp, b, msg)
            elif msg["cmd"] == _EVALUATE:
                reply = self._worker_evaluate(
                    sp_finalize, my_finalize_ids, msg["x"], msg["solver_options"]
                )
            else:
                reply = dict(error=f"unknown command {msg['cmd']!r}")
            comm.gather(reply, root=0)

    def _worker_solve(self, sp, b, msg):
        """
        Build and solve the PH subproblem for bundle b.
        """
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
                return dict(
                    bundle=b,
                    error=(
                        f"subproblem solve failed: "
                        f"status={results.status} "
                        f"termination_condition={results.termination_condition}"
                    ),
                )
            return dict(
                bundle=b,
                error=None,
                obj_value=results.obj_value,
                x={x: sp.get_variable_value(b, x) for x in sp.shared_variables()},
            )
        except Exception:
            return dict(bundle=b, error=traceback.format_exc())

    def _worker_evaluate(self, sp, bundles, x, solver_options):
        """
        Evaluate the first-stage point x on each of the given bundles.  This
        mirrors StochasticProgram.evaluate(), restricted to a subset of the
        bundles.  An objective value of None indicates an infeasible (or
        failed) bundle; evaluation stops at the first such bundle, since the
        point is then infeasible regardless of the other bundles.
        """
        obj_value = {}
        try:
            for b in bundles:
                M = sp.create_subproblem(b, cached=False)
                for i, xval in enumerate(x):
                    sp.fix_variable(b, i, xval)
                results = sp.solve(M, solver_options=solver_options or {})
                obj_value[b] = results.obj_value
                if results.obj_value is None:
                    break
            return dict(error=None, obj_value=obj_value)
        except Exception:
            return dict(error=traceback.format_exc())

    def _finalize_assignment(self, finalize_ids):
        """
        Round-robin assignment of finalization bundles to worker ranks.
        Returns a list indexed by rank (rank 0 is always assigned nothing).
        """
        nworkers = self.size - 1
        assignment = [[] for _ in range(self.size)]
        for j, b in enumerate(finalize_ids):
            assignment[1 + j % nworkers].append(b)
        return assignment

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

    def _parallel_evaluate(self, sp, finalize_ids, x, solver_options=None):
        """
        A parallel drop-in replacement for sp.evaluate(x, solver_options): each worker
        evaluates x on its share of the finalization bundles, and the results
        are combined here.
        """
        comm = self.comm
        x = list(x)
        payload = [None] + [
            dict(cmd=_EVALUATE, x=x, solver_options=solver_options)
            for _ in range(1, self.size)
        ]
        comm.scatter(payload, root=0)
        replies = comm.gather(None, root=0)

        obj_value = {}
        errors = []
        for r, reply in enumerate(replies[1:], start=1):
            if reply["error"] is not None:
                errors.append(f"rank {r}: {reply['error']}")
            else:
                obj_value.update(reply["obj_value"])
        if errors:
            raise RuntimeError(
                "ERROR evaluating a candidate solution:\n" + "\n".join(errors)
            )

        # Report the first infeasible bundle (in bundle order), as sp.evaluate() does
        for b in finalize_ids:
            if b in obj_value and obj_value[b] is None:
                logger.debug(f"Error evaluating solution for bundle {b}")
                return munch.Munch(feasible=False, bundle=b)

        obj = sum(sp.bundles[b].probability * obj_value[b] for b in finalize_ids)
        # The first-stage variables are fixed to x in every bundle
        variables = {sp.get_variable_name(i): x[i] for i in sp.shared_variables()}
        return munch.Munch(feasible=True, objective=obj, variables=variables)

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
        if mf_sp is None:
            finalize_ids = bundle_ids
        else:
            finalize_ids = self._synchronize_bundles(
                sp_finalize, require_worker_per_bundle=False
            )

        if self.rank != 0:
            self._worker_loop(sp, bundle_ids, sp_finalize, finalize_ids)
            return None

        try:
            return self._coordinator_solve(
                sp_finalize, mf_sp, sp, bundle_ids, finalize_ids
            )
        finally:
            # Release the workers, whether we finished normally or raised.
            self._stop_workers()

    def _coordinator_solve(self, sp_finalize, mf_sp, sp, bundle_ids, finalize_ids):
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
        # Finalization: candidate points are evaluated in parallel by the workers.
        #
        logger.info("")
        logger.info("-" * 70)
        logger.info("ProgressiveHedgingSolver_MPI - FINALIZING")

        if mf_sp is not None:
            # The coordinator needs the first-stage variable metadata of
            # sp_finalize (e.g. integrality, for rounding), which is initialized
            # when a subproblem is created.  Build one (unsolved).
            sp_finalize.create_subproblem(
                finalize_ids[0], cached=self.cached_model_generation
            )

        def evaluate(x, solver_options=None):
            return self._parallel_evaluate(
                sp_finalize, finalize_ids, x, solver_options=solver_options
            )

        if self.finalize_all_xbar:
            all_iterations = list(self.solutions)
            self.solutions.add_pool(
                name="Finalized All PH Iterations",
                policy=solnpool.PoolPolicy.keep_all,
            )
            for soln in all_iterations:
                finalize_ph_results(
                    soln,
                    sp=sp_finalize,
                    solutions=self.solutions,
                    finalize_xbar_by_rounding=self.finalize_xbar_by_rounding,
                    evaluate=evaluate,
                    solver_options=self.solver_options,
                )
        else:
            soln = self.solutions[latest_soln]
            self.solutions.add_pool(
                name="Finalized Last PH Solution",
                policy=solnpool.PoolPolicy.keep_best,
            )
            finalize_ph_results(
                soln,
                sp=sp_finalize,
                solutions=self.solutions,
                finalize_xbar_by_rounding=self.finalize_xbar_by_rounding,
                evaluate=evaluate,
                solver_options=self.solver_options,
            )

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
