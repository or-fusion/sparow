#
# Tests for sparow/bin/setup_sparow_sp.py (the setup-sparow-sp command).
#
# Each test generates a package into a temporary directory by calling main()
# directly, then imports it and builds the stochastic program to confirm the
# package actually works.  Generated package names all start with "sptest_" so
# the autouse fixture below can drop them from sys.modules between tests.
#

import importlib
import json
import os
import subprocess
import sys

import pytest

from sparow.bin.setup_sparow_sp import import_path_of, main

SCENARIOS = {
    "data": {"horizon": 12},
    "scenarios": [
        {"ID": "low", "Probability": 0.25, "demand": 15},
        {"ID": "mid", "Probability": 0.50, "demand": 60},
        {"ID": "high", "Probability": 0.25, "demand": 100},
    ],
}
IDS = ["low", "mid", "high"]

#: App script template; $BUILDER is replaced by the scenario builder body and
#: $EXTRA by any additional module-level code.
APP_SCRIPT = """\
import importlib
import os

import pyomo.environ as pyo

from sparow.sp import stochastic_program

APP_DATA = {"c": 1.0, "b": 1.5}


def inline_model(data, scale=1):
    M = pyo.ConcreteModel()
    M.x = pyo.Var(within=pyo.NonNegativeReals)
    M.y = pyo.Var(within=pyo.NonNegativeReals)
    M.sold = pyo.Constraint(expr=M.y <= M.x)
    M.limit = pyo.Constraint(expr=M.y <= data["demand"])
    M.cost = pyo.Objective(expr=scale * data["c"] * M.x - data["b"] * M.y)
    return M


def scenario_builder(data, args):
$BUILDER


def create_sp(scenario_data):
    sp = stochastic_program(first_stage_variables=["x"])
    sp.initialize_application(app_data=APP_DATA)
    sp.initialize_model(model_data=scenario_data, model_builder=scenario_builder)
    return sp
$EXTRA
"""

INLINE = "    return inline_model(data)"
ONCE = (
    '    model = importlib.import_module(".model", __package__)\n'
    "    return inline_model(data, model.SCALE)"
)
PER_SCENARIO = (
    '    model = importlib.import_module("." + data["ID"], __package__)\n'
    "    return inline_model(data, model.SCALE)"
)


@pytest.fixture(autouse=True)
def forget_generated_packages():
    """Drop generated packages from sys.modules after each test."""
    yield
    for name in [n for n in sys.modules if n.startswith("sptest_")]:
        del sys.modules[name]


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """A temporary working directory that is also on sys.path."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    write_json("scenarios.json", SCENARIOS)
    return tmp_path


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fp:
        fp.write(text)


def write_json(path, data):
    write(path, json.dumps(data))


def write_app(path="app.py", builder=INLINE, extra=""):
    text = APP_SCRIPT.replace("$BUILDER", builder).replace("$EXTRA", extra)
    write(path, text)
    return path


def write_model(path, scale=2):
    """A model directory exposing SCALE, imported by ONCE / PER_SCENARIO."""
    write(os.path.join(path, "__init__.py"), "from .params import SCALE\n")
    write(os.path.join(path, "params.py"), f"SCALE = {scale}\n")


def load(name):
    """Import a freshly generated package."""
    # New directories were just created on sys.path; without this, the import
    # system may use a stale cached directory listing and not find them.
    importlib.invalidate_caches()
    return importlib.import_module(name)


def check_sp(package, ids=IDS):
    """Build the package's SP and extensive form, as the skill's verify step."""
    sp = package.create_sp()
    assert list(sp.get_bundles()) == ids
    sp.create_EF()
    assert [sp.get_variable_name(v) for v in sp.shared_variables()] == ["x"]


def listing(path):
    return sorted(os.listdir(path))


# ---- Generated package contents ---------------------------------------------


def test_default_copies_app_and_scenarios(workdir):
    main([write_app(), "-n", "sptest_pkg", "-s", "scenarios.json"])

    assert listing("sptest_pkg") == ["__init__.py", "_app.py", "scenarios.json"]
    check_sp(load("sptest_pkg"))


def test_default_package_is_independent_of_cwd(workdir, monkeypatch):
    main([write_app(), "-n", "sptest_pkg", "-s", "scenarios.json"])
    elsewhere = workdir / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    check_sp(load("sptest_pkg"))


def test_default_package_survives_removing_inputs(workdir):
    main([write_app(), "-n", "sptest_pkg", "-s", "scenarios.json"])
    os.remove("app.py")
    os.remove("scenarios.json")

    check_sp(load("sptest_pkg"))


def test_editable_loads_inputs_in_place(workdir):
    main([write_app(), "-n", "sptest_pkg", "-s", "scenarios.json", "-e"])

    assert listing("sptest_pkg") == ["__init__.py"]
    with open("sptest_pkg/__init__.py") as fp:
        source = fp.read()
    assert repr(str(workdir / "app.py")) in source
    assert repr(str(workdir / "scenarios.json")) in source

    # Edits to the original scenario file take effect without regenerating.
    data = json.loads(json.dumps(SCENARIOS))
    data["scenarios"].append({"ID": "extra", "Probability": 0.1, "demand": 5})
    write_json("scenarios.json", data)
    check_sp(load("sptest_pkg"), IDS + ["extra"])


def test_generated_header_and_usage(workdir, capsys):
    main([write_app(), "-n", "sptest_pkg", "-s", "scenarios.json"])

    with open("sptest_pkg/__init__.py") as fp:
        source = fp.read()
    assert "GENERATED FILE" in source
    assert "from sptest_pkg import create_sp" in source
    out = capsys.readouterr().out
    assert "Created package 'sptest_pkg/'" in out
    assert "Scenarios in scenarios.json: low, mid, high" in out


def test_output_dir_and_nested_import_path(workdir, capsys):
    write("top/__init__.py", "")
    write("top/sub/__init__.py", "")
    main([write_app(), "-n", "sptest_pkg", "-s", "scenarios.json", "-o", "top/sub"])

    assert "from top.sub.sptest_pkg import create_sp" in capsys.readouterr().out
    check_sp(load("top.sub.sptest_pkg"))
    for name in [n for n in sys.modules if n == "top" or n.startswith("top.")]:
        del sys.modules[name]


def test_import_path_of_stops_at_first_non_package(tmp_path):
    write(str(tmp_path / "a/__init__.py"), "")
    write(str(tmp_path / "a/b/__init__.py"), "")

    assert import_path_of(str(tmp_path / "a/b/pkg")) == "a.b.pkg"
    assert import_path_of(str(tmp_path / "pkg")) == "pkg"


# ---- Model directories ------------------------------------------------------


def test_model_dir_copied_once(workdir):
    write_model("model")
    main(
        [
            write_app(builder=ONCE),
            "-n",
            "sptest_pkg",
            "-s",
            "scenarios.json",
            "-m",
            "model",
        ]
    )

    assert "model" in listing("sptest_pkg")
    assert not os.path.islink("sptest_pkg/model")
    check_sp(load("sptest_pkg"))


def test_model_dir_linked_with_editable(workdir):
    write_model("model")
    main(
        [
            write_app(builder=ONCE),
            "-n",
            "sptest_pkg",
            "-s",
            "scenarios.json",
            "-m",
            "model",
            "-e",
        ]
    )

    assert os.path.realpath("sptest_pkg/model") == str(workdir / "model")
    check_sp(load("sptest_pkg"))


def test_scenario_models_copied_per_scenario(workdir):
    write_model("smodel")
    argv = ["-n", "sptest_pkg", "-s", "scenarios.json", "--scenario-models", "smodel"]
    main([write_app(builder=PER_SCENARIO)] + argv)

    for scenario_id in IDS:
        assert not os.path.islink(f"sptest_pkg/{scenario_id}")
    package = load("sptest_pkg")
    check_sp(package)
    # Each scenario gets its own module, which is the point of this mode.
    modules = {id(sys.modules[f"sptest_pkg.{i}"]) for i in IDS}
    assert len(modules) == len(IDS)


def test_scenario_models_linked_with_editable(workdir):
    write_model("smodel")
    argv = [
        "-n",
        "sptest_pkg",
        "-s",
        "scenarios.json",
        "--scenario-models",
        "smodel",
        "-e",
    ]
    main([write_app(builder=PER_SCENARIO)] + argv)

    for scenario_id in IDS:
        assert os.path.realpath(f"sptest_pkg/{scenario_id}") == str(workdir / "smodel")
    check_sp(load("sptest_pkg"))


def test_model_dir_and_scenario_models_together(workdir):
    write_model("model")
    write_model("smodel")
    builder = '    importlib.import_module(".model", __package__)\n' + PER_SCENARIO
    main(
        [write_app(builder=builder), "-n", "sptest_pkg", "-s", "scenarios.json"]
        + ["-m", "model", "--scenario-models", "smodel"]
    )

    assert listing("sptest_pkg") == sorted(
        ["__init__.py", "_app.py", "scenarios.json", "model"] + IDS
    )
    check_sp(load("sptest_pkg"))


def test_model_paths_are_relative_to_cwd_not_output_dir(workdir):
    write_model("model")
    os.mkdir("out")
    main(
        [write_app(builder=ONCE), "-n", "sptest_pkg", "-s", "scenarios.json"]
        + ["-o", "out", "-m", "model"]
    )

    assert os.path.isdir("out/sptest_pkg/model")


# ---- customize_scenario -----------------------------------------------------

#: Records each call, then rewrites the copy's params.py to SCALE = demand.
CUSTOMIZE = """

def customize_scenario(name, data):
    with open($LOG, "a") as fp:
        fp.write(name + " " + os.path.basename(os.getcwd()) + " " + data["ID"] + "\\n")
    with open("params.py", "w") as fp:
        fp.write(f"SCALE = {data['demand']}\\n")
"""


def write_customizing_app(workdir):
    extra = CUSTOMIZE.replace("$LOG", repr(str(workdir / "calls.log")))
    return write_app(builder=PER_SCENARIO, extra=extra)


@pytest.mark.parametrize("editable", [False, True])
def test_customize_scenario_runs_in_each_copy(workdir, editable):
    write_model("smodel", scale=1)
    argv = ["-n", "sptest_pkg", "-s", "scenarios.json", "--scenario-models", "smodel"]
    main([write_customizing_app(workdir)] + argv + (["-e"] if editable else []))

    # Called once per scenario, in order, with the working directory set to
    # that scenario's copy and the scenario's own entry as data.
    with open("calls.log") as fp:
        assert fp.read().split("\n")[:-1] == [f"{i} {i} {i}" for i in IDS]

    # Even under -e the copies are real, so the original is not edited.
    for scenario_id in IDS:
        assert not os.path.islink(f"sptest_pkg/{scenario_id}")
    with open("smodel/params.py") as fp:
        assert fp.read() == "SCALE = 1\n"

    check_sp(load("sptest_pkg"))
    scales = [sys.modules[f"sptest_pkg.{i}"].SCALE for i in IDS]
    assert scales == [15, 60, 100]


def test_customize_scenario_ignored_without_scenario_models(workdir, capsys):
    main([write_customizing_app(workdir), "-n", "sptest_pkg", "-s", "scenarios.json"])

    assert "only called with --scenario-models" in capsys.readouterr().out
    assert not os.path.exists("calls.log")


# ---- Existing package and --force -------------------------------------------


def test_existing_package_requires_force(workdir):
    app = write_app()
    main([app, "-n", "sptest_pkg", "-s", "scenarios.json"])

    with pytest.raises(SystemExit, match="already exists; pass -f/--force"):
        main([app, "-n", "sptest_pkg", "-s", "scenarios.json"])


def test_force_replaces_whole_package(workdir, capsys):
    app = write_app()
    main([app, "-n", "sptest_pkg", "-s", "scenarios.json"])
    write("sptest_pkg/stale.txt", "old")

    main([app, "-n", "sptest_pkg", "-s", "scenarios.json", "-f"])

    assert listing("sptest_pkg") == ["__init__.py", "_app.py", "scenarios.json"]
    assert "Replaced package 'sptest_pkg/'" in capsys.readouterr().out


def test_force_failure_leaves_old_package_untouched(workdir):
    main([write_app(), "-n", "sptest_pkg", "-s", "scenarios.json"])
    write("sptest_pkg/marker.txt", "old")
    before = listing("sptest_pkg")

    write_model("smodel")
    failing = write_app(
        "failing.py",
        extra="\n\ndef customize_scenario(name, data):\n"
        "    if name == 'mid':\n        raise ValueError('boom')\n",
    )
    argv = [
        "-n",
        "sptest_pkg",
        "-s",
        "scenarios.json",
        "--scenario-models",
        "smodel",
        "-f",
    ]
    with pytest.raises(SystemExit, match=r"customize_scenario\('mid', \.\.\.\) failed"):
        main([failing] + argv)

    assert listing("sptest_pkg") == before
    # No staging or backup directories are left behind.
    assert [n for n in os.listdir(".") if n.startswith(".")] == []


def test_force_refuses_to_delete_an_input(workdir):
    app = write_app()
    main([app, "-n", "sptest_pkg", "-s", "scenarios.json"])

    with pytest.raises(SystemExit, match="which --force would delete"):
        main([app, "-n", "sptest_pkg", "-s", "sptest_pkg/scenarios.json", "-f"])
    assert os.path.isfile("sptest_pkg/scenarios.json")


def test_force_keeps_link_targets(workdir):
    write_model("model")
    app = write_app(builder=ONCE)
    argv = ["-n", "sptest_pkg", "-s", "scenarios.json", "-m", "model"]
    main([app] + argv + ["-e"])

    main([app] + argv + ["-f"])

    assert not os.path.islink("sptest_pkg/model")
    assert listing("model") == ["__init__.py", "params.py"]


def test_force_replaces_a_file_in_the_way(workdir):
    write("sptest_pkg", "not a package")

    main([write_app(), "-n", "sptest_pkg", "-s", "scenarios.json", "-f"])

    check_sp(load("sptest_pkg"))


def test_force_restores_old_package_if_swap_fails(workdir, monkeypatch):
    app = write_app()
    main([app, "-n", "sptest_pkg", "-s", "scenarios.json"])
    write("sptest_pkg/marker.txt", "old")
    before = listing("sptest_pkg")

    # Fail the rename that moves the staged package into place (the second
    # rename; the first moves the old package aside).
    real_rename = os.rename
    calls = []

    def flaky_rename(src, dst):
        calls.append((src, dst))
        if len(calls) == 2:
            raise OSError("simulated rename failure")
        real_rename(src, dst)

    monkeypatch.setattr(os, "rename", flaky_rename)
    with pytest.raises(OSError, match="simulated rename failure"):
        main([app, "-n", "sptest_pkg", "-s", "scenarios.json", "-f"])

    assert listing("sptest_pkg") == before
    assert [n for n in os.listdir(".") if n.startswith(".")] == []


# ---- Validation errors ------------------------------------------------------


def run_with_app(text, *args):
    write("bad_app.py", text)
    main(["bad_app.py", "-n", "sptest_pkg", "-s", "scenarios.json", *args])


@pytest.mark.parametrize(
    "text, message",
    [
        ("x = 1\n", "does not define a callable 'create_sp'"),
        ("create_sp = 1\n", "does not define a callable 'create_sp'"),
        (
            "def create_sp(data, builder): pass\n",
            r"'create_sp' must accept 1 positional argument",
        ),
        (
            "def create_sp(d): pass\ndef customize_scenario(name): pass\n",
            r"'customize_scenario' must accept 2 positional arguments",
        ),
        (
            "def create_sp(d): pass\ncustomize_scenario = 1\n",
            "'customize_scenario' is defined but not callable",
        ),
        ("raise RuntimeError('broken')\n", "failed to import"),
    ],
)
def test_invalid_app_script(workdir, text, message):
    with pytest.raises(SystemExit, match=message):
        run_with_app(text)
    assert not os.path.exists("sptest_pkg")


def test_missing_app_script(workdir):
    with pytest.raises(SystemExit, match="app script not found"):
        main(["missing.py", "-n", "sptest_pkg", "-s", "scenarios.json"])


def test_app_script_must_be_python(workdir):
    # Without a .py suffix, importlib cannot pick a loader for the file.
    write("app.txt", "def create_sp(scenario_data): pass\n")
    with pytest.raises(SystemExit, match="not an importable Python module"):
        main(["app.txt", "-n", "sptest_pkg", "-s", "scenarios.json"])


@pytest.mark.parametrize(
    "data, message",
    [
        ([1, 2], "top level must be a JSON object"),
        ({}, "'scenarios' must be a non-empty list"),
        ({"scenarios": []}, "'scenarios' must be a non-empty list"),
        ({"scenarios": {}}, "'scenarios' must be a non-empty list"),
        ({"scenarios": [1]}, "scenario 0 is not a JSON object"),
        ({"scenarios": [{"x": 1}]}, "scenario 0 has no 'ID'"),
        ({"scenarios": [{"ID": 1}]}, r"scenario 0 'ID' must be a string \(found 1\)"),
        ({"scenarios": [{"ID": "a"}, {"ID": "a"}]}, "duplicate scenario IDs"),
        ({"data": [], "scenarios": [{"ID": "a"}]}, "'data' must be a JSON object"),
        (
            {"data": {"c": 2}, "scenarios": [{"ID": "a"}]},
            "'data' key 'c' is already defined",
        ),
        (
            {"data": {"h": 1}, "scenarios": [{"ID": "a", "h": 2}]},
            "scenario 'a' key 'h' is already defined",
        ),
    ],
)
def test_invalid_scenario_file(workdir, data, message):
    write_json("bad.json", data)
    with pytest.raises(SystemExit, match=message):
        main([write_app(), "-n", "sptest_pkg", "-s", "bad.json"])
    assert not os.path.exists("sptest_pkg")


def test_invalid_scenario_json(workdir):
    write("bad.json", "{not json")
    with pytest.raises(SystemExit, match="invalid JSON"):
        main([write_app(), "-n", "sptest_pkg", "-s", "bad.json"])


def test_missing_scenario_file(workdir):
    with pytest.raises(SystemExit, match="scenario data file not found"):
        main([write_app(), "-n", "sptest_pkg", "-s", "missing.json"])


def test_collision_check_skipped_without_app_data(workdir):
    # Without APP_DATA the generator cannot see the application data, so a
    # scenario key that would collide with it is not caught here.
    write("plain.py", "def create_sp(scenario_data):\n    return scenario_data\n")
    write_json("s.json", {"scenarios": [{"ID": "a", "c": 1}]})
    main(["plain.py", "-n", "sptest_pkg", "-s", "s.json"])

    assert load("sptest_pkg").create_sp() == {"scenarios": [{"ID": "a", "c": 1}]}


@pytest.mark.parametrize(
    "args, message",
    [
        (["-n", "not-valid"], "is not a valid Python identifier"),
        (["-o", "missing"], "output directory not found"),
        (["-m", "missing"], "model directory not found"),
        (["-m", "bad-name"], "is not a valid Python identifier"),
        (["-m", "_app"], "'_app' is reserved for the app script"),
        (
            ["-m", "low", "--scenario-models", "smodel"],
            "'low' is also a scenario ID",
        ),
        (["--scenario-models", "missing"], "model directory not found"),
    ],
)
def test_invalid_options(workdir, args, message):
    write_model("smodel")
    for name in ("bad-name", "_app", "low"):
        write_model(name)
    argv = [write_app(), "-n", "sptest_pkg", "-s", "scenarios.json"]
    # A later -n overrides the default one above.
    with pytest.raises(SystemExit, match=message):
        main(argv + args)


@pytest.mark.parametrize(
    "scenario_id, message",
    [
        ("not-valid", "is not a valid Python identifier"),
        ("_app", "scenario ID '_app' is reserved"),
    ],
)
def test_invalid_scenario_id_for_scenario_models(workdir, scenario_id, message):
    write_model("smodel")
    write_json("s.json", {"scenarios": [{"ID": scenario_id}]})
    with pytest.raises(SystemExit, match=message):
        main(
            [
                write_app(),
                "-n",
                "sptest_pkg",
                "-s",
                "s.json",
                "--scenario-models",
                "smodel",
            ]
        )


def test_required_arguments(workdir, capsys):
    with pytest.raises(SystemExit) as excinfo:
        main([write_app(), "-n", "sptest_pkg"])
    assert excinfo.value.code == 2
    assert "-s/--scenarios" in capsys.readouterr().err


# ---- Command line entry points ----------------------------------------------


def test_runs_as_module():
    result = subprocess.run(
        [sys.executable, "-m", "sparow.bin.setup_sparow_sp", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--scenario-models" in result.stdout
