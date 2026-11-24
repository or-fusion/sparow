"""
The parallel execution layer used by ProgressiveHedgingSolver_MPI.

ParallelWorker manages all of the MPI logic for distributing subproblem
solves and solution evaluations, using an asynchronous master-worker scheme:

* Rank 0 is the master.  It maintains a queue of tasks, and dispatches them
  to the workers.

* Ranks 1, ..., size-1 are workers.  A worker receives a task, executes it,
  and sends back the result, until it is told to stop.

* The master initially sends one task to every worker.  Whenever a result
  arrives, the master sends that worker the next pending task, until the
  queue is empty and all results have been received.

There are two kinds of tasks:

* A solve task builds and solves the PH subproblem for one bundle.

* An evaluate task evaluates a candidate first-stage point on one bundle of
  the finalization model.

With a single process there are no workers, and the master executes all
tasks itself.

When a worker becomes free, the master prefers to give it a bundle that it
solved previously, and only otherwise moves a bundle from the worker with the
most remaining work.  When subproblem solve times are similar, this keeps
each bundle on the same worker, so cached subproblem models are reused.
"""

import collections
import traceback

import sparow.logs

logger = sparow.logs.logger

# Commands sent from the master to the workers
_SOLVE = "solve"
_EVALUATE = "evaluate"
_STOP = "stop"

# Message tags
_TAG_TASK = 1
_TAG_RESULT = 2


class ParallelWorker(object):
    """
    Manages the parallel setup and execution of subproblem solves and
    solution evaluations on MPI ranks 1, ..., size-1.

    Usage (every rank executes the same code):

        pw = ParallelWorker(comm)
        pw.setup(sp, sp_finalize, check_finalize=..., ...)
        if not pw.is_master:
            pw.worker_loop()          # returns when the master stops it
        else:
            try:
                ... pw.solve_subproblems(...) / pw.evaluate(...) ...
            finally:
                pw.stop()

    Parameters
    ----------
    comm : mpi4py.MPI.Comm, optional
        The communicator to use (default is MPI.COMM_WORLD).
    """

    def __init__(self, comm=None):
        from mpi4py import MPI

        self._MPI = MPI
        if comm is None:
            comm = MPI.COMM_WORLD
        self.comm = comm
        self.rank = comm.Get_rank()
        self.size = comm.Get_size()

        self._sp = None
        self._sp_finalize = None
        self.finalize_ids = None
        self.cached_model_generation = True
        self.solver_options = {}
        self.worker_loglevel = "WARNING"
        # Master state
        self._busy = {}  # worker rank -> key of the task it is executing
        self._affinity = {}  # bundle -> worker rank that last solved it

    @property
    def is_master(self):
        return self.rank == 0

    @property
    def num_workers(self):
        return self.size - 1

    #
    # Setup
    #

    def setup(
        self,
        sp,
        sp_finalize,
        *,
        check_finalize=True,
        cached_model_generation=True,
        solver_options=None,
        worker_loglevel=None,
    ):
        """
        Collectively set up the parallel execution on all ranks.

        Parameters
        ----------
        sp : StochasticProgram
            The model used for the PH subproblem solves.
        sp_finalize : StochasticProgram
            The model used for evaluating candidate solutions.
        check_finalize : bool
            If True, also verify that the bundles of sp_finalize are
            identical across ranks.  (Not needed when sp_finalize is sp.)
        cached_model_generation : bool
            If True, cached subproblem models are reused by the solve tasks.
        solver_options : dict, optional
            The solver options for the subproblem solves.
        worker_loglevel : str, optional
            The logging level on the worker ranks.
        """
        self.synchronize_bundles(sp)
        if check_finalize:
            self.synchronize_bundles(sp_finalize)

        self._sp = sp
        self._sp_finalize = sp_finalize
        self.finalize_ids = list(sp_finalize.bundles)
        self.cached_model_generation = cached_model_generation
        self.solver_options = solver_options or {}
        if worker_loglevel is not None:
            self.worker_loglevel = worker_loglevel
        self._busy = {}
        self._affinity = {}

        if self.size > 1:
            sparow.logs.set_log_prefix(f"[rank {self.rank}] ")

    def synchronize_bundles(self, sp):
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
    # Worker side
    #

    def worker_loop(self):
        """
        Execute tasks from the master until told to stop.  Called on ranks
        1, ..., size-1.
        """
        comm = self.comm
        level = logger.level
        logger.setLevel(self.worker_loglevel)
        try:
            while True:
                msg = comm.recv(source=0, tag=_TAG_TASK)
                if msg["cmd"] == _STOP:
                    return
                reply = self._execute(msg)
                comm.send(reply, dest=0, tag=_TAG_RESULT)
        finally:
            logger.setLevel(level)

    def _execute(self, msg):
        """
        Execute a task, and return its result.  Exceptions are caught and
        reported in the result, so a failing task never leaves a rank blocked.
        """
        try:
            if msg["cmd"] == _SOLVE:
                return self._execute_solve(msg)
            elif msg["cmd"] == _EVALUATE:
                return self._execute_evaluate(msg)
            return dict(error=f"unknown command {msg['cmd']!r}")
        except Exception:
            return dict(error=traceback.format_exc())

    def _execute_solve(self, msg):
        """
        Build and solve the PH subproblem for one bundle.
        """
        sp = self._sp
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

    def _execute_evaluate(self, msg):
        """
        Evaluate a first-stage point on one bundle.  This mirrors the body of
        the loop in StochasticProgram.evaluate().  An objective value of None
        indicates that the point is infeasible for this bundle.
        """
        sp = self._sp_finalize
        b = msg["bundle"]
        M = sp.create_subproblem(b, cached=False)
        for i, xval in enumerate(msg["x"]):
            sp.fix_variable(b, i, xval)
        results = sp.solve(M, solver_options=msg["solver_options"] or {})
        return dict(error=None, obj_value=results.obj_value)

    #
    # Master side
    #

    def solve_subproblems(self, bundle_ids, *, w=None, xbar=None, rho=None):
        """
        Solve the PH subproblems for the given bundles in parallel.  Each
        bundle is preferably solved by the worker that solved it last.

        Returns
        -------
        dict
            Maps each bundle to its result: a dictionary with 'obj_value',
            'x' (first-stage values, indexed by shared variable) and 'worker'.

        Raises
        ------
        RuntimeError
            If any subproblem solve failed.
        """
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
        results = self.run_tasks(tasks, affinity=self._affinity)
        for b, reply in results.items():
            self._affinity[b] = reply["worker"]
        return results

    def evaluate(self, x, solver_options=None):
        """
        Evaluate the first-stage point x on each finalization bundle in
        parallel.  Dispatching stops as soon as x is found to be infeasible
        for a bundle.

        Returns
        -------
        dict
            Maps bundles to results: dictionaries with 'obj_value' (None if
            x is infeasible for the bundle) and 'worker'.  If x is infeasible,
            some bundles may be missing.

        Raises
        ------
        RuntimeError
            If any evaluation failed.
        """
        x = list(x)
        tasks = [
            (b, dict(cmd=_EVALUATE, bundle=b, x=x, solver_options=solver_options))
            for b in self.finalize_ids
        ]
        return self.run_tasks(tasks, stop_when=lambda reply: reply["obj_value"] is None)

    def run_tasks(self, tasks, *, affinity=None, stop_when=None):
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
        if self.size == 1:
            return self._run_tasks_locally(tasks, stop_when=stop_when)

        results = {}
        errors = []
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

    def _run_tasks_locally(self, tasks, *, stop_when=None):
        """
        Execute the tasks on the master (used when there are no workers).
        """
        results = {}
        for key, msg in tasks:
            reply = self._execute(msg)
            if reply["error"] is not None:
                raise RuntimeError(f"{key}: {reply['error']}")
            reply["worker"] = 0
            results[key] = reply
            if stop_when is not None and stop_when(reply):
                break
        return results

    def stop(self):
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
