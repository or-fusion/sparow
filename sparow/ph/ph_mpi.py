"""
An MPI-parallel progressive hedging solver.

Subproblem solves are distributed with mpi4py using an asynchronous
master-worker scheme:

* Rank 0 is the master.  It runs the PH algorithm (computing xbar, w, rho and
  the convergence metrics, archiving solutions and finalizing the results),
  and maintains a queue of tasks.
* Ranks 1, ..., size-1 are workers.  A worker receives a task, executes it,
  and sends back the result.
* The master initially sends one task to every worker.  Whenever a result
  arrives, the master sends that worker the next pending task, until the
  queue is empty and all results have been received.

There are two kinds of tasks:

* During search, a task solves the PH subproblem for one bundle.
* During finalization, a task evaluates a candidate first-stage point on one
  bundle of the finalization model.

Any number of processes can be used.  Load is balanced dynamically, so fewer
workers than bundles is fine (each worker simply solves several subproblems
per iteration), and with a single process the master executes all tasks
itself.

When a worker becomes free, the master prefers to give it a bundle that it
solved in the previous iteration, and only otherwise moves a bundle from the
worker with the most remaining work.  When subproblem solve times are
similar, this keeps each bundle on the same worker, so cached subproblem
models (``cached_model_generation``) are reused.

The solver is used in SPMD style: every rank executes the same script, builds
the same stochastic program and calls ``solve()``.  For example:

    mpiexec -n 4 python my_script.py

``solve()`` returns the solution pool on rank 0 and ``None`` on all other ranks.

Logging: when more than one process is used, log messages are prefixed with
the rank (e.g. "[rank 2] INFO - ...").  The ``loglevel`` option applies to the
master, and the ``worker_loglevel`` option (default "WARNING") applies to the
workers, so worker output is limited to warnings and errors unless requested.
"""

import collections
import traceback

import munch

import sparow.logs
from sparow.ph.ph import ProgressiveHedgingSolverBase

logger = sparow.logs.logger

# Commands sent from the master to the workers
_SOLVE = "solve"
_EVALUATE = "evaluate"
_STOP = "stop"

# Message tags
_TAG_TASK = 1
_TAG_RESULT = 2


class ProgressiveHedgingSolver_MPI(ProgressiveHedgingSolverBase):
    """
    A progressive hedging solver that solves the bundle subproblems in
    parallel using mpi4py, with an asynchronous master-worker scheme.

    The algorithm (and all options) are identical to ProgressiveHedgingSolver;
    both are implemented by ProgressiveHedgingSolverBase, and only the location
    of the subproblem solves changes.

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
        from mpi4py import MPI

        self._MPI = MPI
        if comm is None:
            comm = MPI.COMM_WORLD
        self.comm = comm
        self.rank = comm.Get_rank()
        self.size = comm.Get_size()
        self.worker_loglevel = "WARNING"
        # Master state
        self._busy = {}  # worker rank -> key of the task it is executing
        self._affinity = {}  # bundle -> worker rank that last solved it
        self._sp = None
        self._sp_finalize = None
        self._finalize_ids = None

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
    # Setup
    #

    def _synchronize_bundles(self, sp):
        """
        Verify that every rank built identical bundles.  Returns the ordered
        list of bundle ids.

        All ranks reach the same conclusion, so errors are raised consistently
        everywhere (no rank is left blocked in a collective call).
        """
        comm = self.comm
        # Note: sp.bundles is lazily initialized, so touch it on every rank.
        local_ids = list(sp.bundles)
        bundle_ids = comm.bcast(local_ids if self.rank == 0 else None, root=0)
        reference = comm.bcast(sp.get_bundles() if self.rank == 0 else None, root=0)

        local_ok = local_ids == bundle_ids and sp.get_bundles() == reference
        all_ok = comm.allreduce(local_ok, op=self._MPI.LAND)
        if not all_ok:
            raise RuntimeError(
                "ProgressiveHedgingSolver_MPI: the bundles differ across MPI ranks. "
                "Every rank must construct identical bundles (e.g. seed any "
                "randomized bundling scheme)."
            )
        return bundle_ids

    #
    # Task execution (on a worker, or on the master when there are no workers)
    #

    def _execute(self, msg, sp, sp_finalize):
        """
        Execute a task, and return its result.  Exceptions are caught and
        reported in the result, so a failing task never leaves a rank blocked.
        """
        try:
            if msg["cmd"] == _SOLVE:
                return self._execute_solve(sp, msg)
            elif msg["cmd"] == _EVALUATE:
                return self._execute_evaluate(sp_finalize, msg)
            return dict(error=f"unknown command {msg['cmd']!r}")
        except Exception:
            return dict(error=traceback.format_exc())

    def _execute_solve(self, sp, msg):
        """
        Build and solve the PH subproblem for one bundle.
        """
        b = msg["bundle"]
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
                error=(
                    f"subproblem solve failed: "
                    f"status={results.status} "
                    f"termination_condition={results.termination_condition}"
                ),
            )
        return dict(
            error=None,
            obj_value=results.obj_value,
            x={x: sp.get_variable_value(b, x) for x in sp.shared_variables()},
        )

    def _execute_evaluate(self, sp, msg):
        """
        Evaluate a first-stage point on one bundle.  This mirrors the body of
        the loop in StochasticProgram.evaluate().  An objective value of None
        indicates that the point is infeasible for this bundle.
        """
        b = msg["bundle"]
        M = sp.create_subproblem(b, cached=False)
        for i, xval in enumerate(msg["x"]):
            sp.fix_variable(b, i, xval)
        results = sp.solve(M, solver_options=msg["solver_options"] or {})
        return dict(error=None, obj_value=results.obj_value)

    def _worker_loop(self, sp, sp_finalize):
        """
        Execute tasks from the master until told to stop.
        """
        comm = self.comm
        while True:
            msg = comm.recv(source=0, tag=_TAG_TASK)
            if msg["cmd"] == _STOP:
                return
            reply = self._execute(msg, sp, sp_finalize)
            comm.send(reply, dest=0, tag=_TAG_RESULT)

    #
    # Task scheduling (on the master)
    #

    def _run_tasks(self, tasks, *, affinity=None, stop_when=None):
        """
        Execute a set of tasks on the workers, and return their results.

        Parameters
        ----------
        tasks : list
            List of (key, msg) tuples.  Keys must be unique.
        affinity : dict, optional
            Maps task keys to the worker rank that should preferably execute
            the task.  A free worker is given one of its own tasks first, then
            a task without affinity.  Otherwise it steals the last task of the
            worker with the most remaining tasks.
        stop_when : callable, optional
            Called with each successful result; if it returns True, no further
            tasks are dispatched (outstanding tasks are still collected).

        Returns
        -------
        dict
            Maps task keys to results, for the tasks that were executed.  The
            results are dictionaries that include a 'worker' entry, which is
            the rank that executed the task.

        Raises
        ------
        RuntimeError
            If any task failed.  All outstanding tasks are collected first.
        """
        results = {}
        errors = []

        if self.size == 1:
            # No workers: execute the tasks here
            for key, msg in tasks:
                reply = self._execute(msg, self._sp, self._sp_finalize)
                if reply["error"] is not None:
                    errors.append(f"{key}: {reply['error']}")
                    break
                reply["worker"] = 0
                results[key] = reply
                if stop_when is not None and stop_when(reply):
                    break
            if errors:
                raise RuntimeError("\n".join(errors))
            return results

        comm = self.comm
        status = self._MPI.Status()

        #
        # The queue of pending tasks.  Each pending task is in exactly one of
        # the queues: queues[w] holds the tasks with affinity to worker w, and
        # queues[None] holds the tasks without affinity.  (Dicts are used as
        # ordered sets.)
        #
        pending = dict(tasks)
        queues = collections.defaultdict(dict)
        owner = {}
        for key, _ in tasks:
            worker = affinity.get(key) if affinity else None
            if worker is not None and not (1 <= worker < self.size):
                worker = None
            owner[key] = worker
            queues[worker][key] = None

        def next_task(worker, steal):
            """
            Select a task for a worker: one of its own tasks, else a task
            without affinity, else (if steal is True) the last task of the
            worker with the most remaining tasks.  Returns None if no task
            was selected.
            """
            for queue in (queues[worker], queues[None]):
                if queue:
                    return next(iter(queue))
            if not steal:
                return None
            victim = max(
                (w for w in queues if w is not None and queues[w]),
                key=lambda w: len(queues[w]),
                default=None,
            )
            return None if victim is None else next(reversed(queues[victim]))

        def dispatch(worker, key):
            del queues[owner[key]][key]
            comm.send(pending.pop(key), dest=worker, tag=_TAG_TASK)
            self._busy[worker] = key

        def dispatch_idle():
            # Two passes: first give the idle workers their own tasks (or tasks
            # without affinity), and only then let the remaining idle workers
            # steal.  This avoids a cascade where an idle worker takes another
            # worker's task, which then takes a third worker's task, etc.
            for steal in (False, True):
                for worker in list(idle):
                    if not pending:
                        return
                    key = next_task(worker, steal)
                    if key is not None:
                        idle.remove(worker)
                        dispatch(worker, key)

        idle = collections.deque(range(1, self.size))
        stopping = False
        while True:
            # Dispatch tasks to the idle workers
            if not stopping:
                dispatch_idle()

            if not self._busy:
                break

            # Wait for the next result
            reply = comm.recv(
                source=self._MPI.ANY_SOURCE, tag=_TAG_RESULT, status=status
            )
            worker = status.Get_source()
            key = self._busy.pop(worker)
            idle.append(worker)

            if reply["error"] is not None:
                errors.append(f"{key} (rank {worker}): {reply['error']}")
                stopping = True
                continue
            reply["worker"] = worker
            results[key] = reply
            logger.verbose(f"Received results for {key} from rank {worker}")
            if stop_when is not None and stop_when(reply):
                stopping = True

        if errors:
            raise RuntimeError("\n".join(errors))
        return results

    def _stop_workers(self):
        """
        Collect the results of any outstanding tasks (e.g. after an error on
        the master), and then tell all workers to stop.
        """
        comm = self.comm
        for worker in list(self._busy):
            comm.recv(source=worker, tag=_TAG_RESULT)
            del self._busy[worker]
        for worker in range(1, self.size):
            comm.send(dict(cmd=_STOP), dest=worker, tag=_TAG_TASK)

    #
    # Hooks for ProgressiveHedgingSolverBase
    #

    def _solve(self, sp_finalize, mf_sp, sp):
        """
        Split the ranks into the master (rank 0), which runs the PH algorithm,
        and the workers, which execute tasks on request.
        """
        self._synchronize_bundles(sp)
        if mf_sp is not None:
            self._synchronize_bundles(sp_finalize)

        if self.size > 1:
            sparow.logs.set_log_prefix(f"[rank {self.rank}] ")

        if self.rank != 0:
            level = logger.level
            logger.setLevel(self.worker_loglevel)
            try:
                self._worker_loop(sp, sp_finalize)
            finally:
                logger.setLevel(level)
            return None

        self._sp = sp
        self._sp_finalize = sp_finalize
        self._finalize_ids = list(sp_finalize.bundles)
        self._busy = {}
        self._affinity = {}
        try:
            return self._run_ph(sp_finalize, mf_sp, sp, list(sp.bundles))
        finally:
            # Release the workers, whether we finished normally or raised.
            self._stop_workers()

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
        tasks = [
            (
                b,
                dict(
                    cmd=_SOLVE,
                    bundle=b,
                    w=None if w is None else w[b],
                    xbar=xbar,
                    rho=rho,
                ),
            )
            for b in bundle_ids
        ]
        try:
            results = self._run_tasks(tasks, affinity=self._affinity)
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
            self._affinity[b] = reply["worker"]
        return obj_value, xvals

    def _prepare_finalize(self, sp_finalize, mf_sp):
        if mf_sp is not None:
            # The master needs the first-stage variable metadata of
            # sp_finalize (e.g. integrality, for rounding), which is
            # initialized when a subproblem is created.  Build one (unsolved).
            sp_finalize.create_subproblem(
                self._finalize_ids[0], cached=self.cached_model_generation
            )

        def evaluate(x, solver_options=None):
            return self._parallel_evaluate(sp_finalize, x, solver_options)

        return evaluate

    def _parallel_evaluate(self, sp, x, solver_options):
        """
        A parallel drop-in replacement for sp.evaluate(x, solver_options): the
        point x is evaluated on each finalization bundle by the workers.
        Dispatching stops as soon as x is found to be infeasible for a bundle.
        """
        x = list(x)
        tasks = [
            (b, dict(cmd=_EVALUATE, bundle=b, x=x, solver_options=solver_options))
            for b in self._finalize_ids
        ]
        try:
            results = self._run_tasks(
                tasks, stop_when=lambda reply: reply["obj_value"] is None
            )
        except RuntimeError as e:
            raise RuntimeError(f"ERROR evaluating a candidate solution:\n{e}") from None

        # Report the first infeasible bundle (in bundle order)
        for b in self._finalize_ids:
            if b in results and results[b]["obj_value"] is None:
                logger.debug(f"Error evaluating solution for bundle {b}")
                return munch.Munch(feasible=False, bundle=b)

        obj = sum(
            sp.bundles[b].probability * results[b]["obj_value"]
            for b in self._finalize_ids
        )
        # The first-stage variables are fixed to x in every bundle
        variables = {sp.get_variable_name(i): x[i] for i in sp.shared_variables()}
        return munch.Munch(feasible=True, objective=obj, variables=variables)

    def _extra_metadata(self):
        return dict(mpi_processes=self.size)
