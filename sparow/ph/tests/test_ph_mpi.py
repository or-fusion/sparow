import json
import os
import shutil
import subprocess
import sys

import pytest

from pyomo.opt import check_available_solvers

try:
    import mpi4py  # noqa: F401

    mpi4py_available = True
except ImportError:
    mpi4py_available = False

mpiexec = shutil.which("mpiexec") or shutil.which("mpirun")

_solvers = [s for s in ("gurobi", "highs") if check_available_solvers(s)]
solver = _solvers[0] if _solvers else None

driver = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_ph_mpi.py")


def run_driver(nprocs, tmp_path):
    clean_env = {
        k: v for k, v in os.environ.items()
        if not k.startswith(("OMPI_", "PMIX_", "PMI_", "I_MPI_", "MPICH_", "SLURM_"))
    }
    outfile = tmp_path / "results.json"
    cmd = [mpiexec, "-n", str(nprocs), sys.executable, driver, solver, str(outfile)]

    proc = subprocess.run(
        cmd,
        env=clean_env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc, outfile


@pytest.mark.skipif(not mpi4py_available, reason="mpi4py not installed")
@pytest.mark.skipif(mpiexec is None, reason="mpiexec not found")
@pytest.mark.skipif(solver is None, reason="no LP solver available")
class TestProgressiveHedgingMPI(object):

    def test_matches_serial(self, tmp_path):
        # 5 bundles: 6 ranks = 1 coordinator + 1 worker per bundle;
        # 7 ranks adds an idle search rank that still helps with finalization.
        for nprocs in (6, 7):
            proc, outfile = run_driver(nprocs, tmp_path)
            assert proc.returncode == 0, proc.stdout + proc.stderr

            results = json.loads(outfile.read_text())
            assert set(results) == {"default", "finalize_all_xbar", "solver_options"}
            for config, res in results.items():
                mpi, serial = res["mpi"], res["serial"]
                label = f"nprocs={nprocs} config={config}"
                assert mpi["xbar"] == pytest.approx(
                    serial["xbar"], rel=1e-6, abs=1e-6
                ), label
                assert mpi["objective"] == pytest.approx(
                    serial["objective"], rel=1e-6
                ), label

    def test_too_few_processes(self, tmp_path):
        proc, _ = run_driver(5, tmp_path)
        assert proc.returncode != 0
        assert "requires at least 6 MPI processes" in proc.stdout + proc.stderr
