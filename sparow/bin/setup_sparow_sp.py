#!/usr/bin/env python
#
# Generate a sparow stochastic program application package.
#
# The application itself -- the model builder and the sparow wiring -- lives in
# a separate app script handed to this generator:
#
#     cd sparow_examples/my_app
#     setup-sparow-sp my_app.py --name my_sp --scenarios scenarios.json
#
# That script must define
#
#     create_sp(scenario_data)  -> configured stochastic_program
#
# where `scenario_data` is the parsed scenario data file.  create_sp registers
# the app script's own scenario builder, conventionally
#
#     scenario_builder(data, args)  -> Pyomo model for one scenario
#
# By default the generator copies the app script and the scenario data file into
# the package as `<NAME>/_app.py` and `<NAME>/scenarios.json`, so the package is
# self-contained; pass --editable (-e) to load both in place from their current
# paths instead.  Either way the generator writes `<NAME>/__init__.py`, whose
# `create_sp()` reads the scenario data and passes it to the app script's
# create_sp:
#
#     from sparow_examples.my_app.my_sp import create_sp
#     sp = create_sp()
#
# With --model-dir (-m), the generator also copies a model tree once into
# the package, as a subpackage keeping the tree's directory name.  The app
# script is always loaded as a module of the generated package, so it imports
# the copy relative to `__package__`:
#
#     def scenario_builder(data, args):
#         model = importlib.import_module(".model", __package__)
#         return model.create_model(alpha=data["alpha"])
#
# With --scenario-models, the generator copies a model tree once per scenario
# ID instead, as a subpackage named for the ID, for scenarios that need
# physically separate module state:
#
#     def scenario_builder(data, args):
#         model = importlib.import_module("." + data["ID"], __package__)
#         return model.create_model(alpha=data["alpha"])
#
#     setup-sparow-sp my_app.py --name my_sp --scenarios scenarios.json \
#         --scenario-models model
#
# If the app script also defines
#
#     customize_scenario(name, data)
#
# the generator calls it once per scenario, right after copying that scenario's
# model tree, with the working directory set to the copy.  `name` is the
# scenario ID and `data` is the scenario's entry in the scenario data file.
#
# With --editable, model trees are symlinked to the originals rather than
# copied, so model edits also take effect without regenerating.  Per-scenario
# trees are still copied when the app script defines customize_scenario, since
# customizing through a link would edit the shared original.
#

import argparse
import importlib.util
import inspect
import json
import os
import shutil
import string
import sys
import tempfile

# ---- Names used inside the generated package ---------------------------------
#
# Both are fixed rather than derived from the input file names, so the
# generated __init__.py never has to change shape between runs.

#: Module name the app script is copied to inside the generated package.  The
#: leading underscore marks it private: users import create_sp from the
#: package, not from the app script directly.
APP_MODULE = "_app"

#: File name the scenario data is copied to inside the generated package.
SCENARIO_FILE = "scenarios.json"

# ---- Templates for the generated __init__.py ---------------------------------
#
# string.Template is used rather than str.format because the generated code is
# full of braces (f-strings, dicts) that format() would try to interpret.

#: Loads the app script from its original location, when it is not copied in.
#: The module is named <package>._app, the same as the copied form, so the app
#: script's `__package__` is the generated package in both modes and relative
#: imports of model directories work either way.
LOAD_IN_PLACE = string.Template('''#: App script, loaded from where it lives rather than copied into this package.
APP_SCRIPT = $path


def _load_app_script(path):
    spec = importlib.util.spec_from_file_location(__name__ + ".$app_module", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"{path}: not an importable Python module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


$app_module = _load_app_script(APP_SCRIPT)
''')


#: The generated __init__.py.  The placeholders are filled in by main():
#:   $imports          stdlib imports, which differ between copied and -e mode
#:   $app_import       binds $app_module, by relative import or LOAD_IN_PLACE
#:   $scenario_file    defines SCENARIO_FILE, relative to the package or absolute
MODULE_TEMPLATE = string.Template('''#
# $import_path
#
# GENERATED FILE -- written by $script from $app_script and $scenario_source.
# Edit those and re-run the generator, not this file.
#
# Usage:
#     from $import_path import create_sp
#     sp = create_sp()
#

$imports

$app_import
$scenario_file

def create_sp():
    """
    Build the stochastic program from the scenario data in SCENARIO_FILE.

    SCENARIO_FILE is a JSON file of the form::

        {"data": {...},
         "scenarios": [{"ID": "s1", "Probability": 0.5, ...}, ...]}

    The "data" block is optional.  Scenario probabilities are normalized by
    their sum; if any scenario omits "Probability", sparow falls back to a
    uniform distribution over all scenarios.

    Returns
    -------
    StochasticProgram_Pyomo_NamedBuilder
    """
    with open(SCENARIO_FILE) as fp:
        scenario_data = json.load(fp)
    return $app_module.create_sp(scenario_data)
''')


# ---- Validating the app script -----------------------------------------------

#: Required app script entry points, and the positional arity of each.
CONTRACT = {"create_sp": 1}

#: Optional app script entry points, checked only when defined.
OPTIONAL = {"customize_scenario": 2}


def check_signature(path, func, name, arity):
    """Exit unless `func` can be called with `arity` positional arguments."""
    try:
        # bind() applies the real calling rules, so defaults, *args and
        # keyword-only parameters are all judged correctly without calling
        # the function.  The dummy values are never used.
        inspect.signature(func).bind(*range(arity))
    except TypeError:
        expected = ", ".join(inspect.signature(func).parameters)
        raise SystemExit(
            f"{path}: '{name}' must accept {arity} positional "
            f"argument{'s' if arity != 1 else ''} (found: {name}({expected}))"
        )


def load_app_script(path):
    """
    Import the app script standalone and check it satisfies the contract.

    Returns the imported module so its conventional `APP_DATA` can be used to
    validate the scenario file.
    """
    if not os.path.isfile(path):
        raise SystemExit(f"{path}: app script not found")

    # Load the script by path under a private top-level name.  This runs the
    # user's module-level code at generate time, and because the module is
    # not part of any package here, a top-level relative import in the script
    # fails -- which is why model directories must be imported inside
    # functions.
    spec = importlib.util.spec_from_file_location("_sparow_app_script", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"{path}: not an importable Python module")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise SystemExit(f"{path}: failed to import: {exc!r}")

    # Required entry points must exist and accept the right number of
    # positional arguments.
    for name, arity in CONTRACT.items():
        func = getattr(module, name, None)
        if not callable(func):
            raise SystemExit(f"{path}: does not define a callable '{name}'")
        check_signature(path, func, name, arity)

    # Optional entry points are checked the same way, but only when present.
    for name, arity in OPTIONAL.items():
        func = getattr(module, name, None)
        if func is None:
            continue
        if not callable(func):
            raise SystemExit(f"{path}: '{name}' is defined but not callable")
        check_signature(path, func, name, arity)

    return module


def app_data_of(module):
    """Return the app script's application data, by convention, else None."""
    # Only a convention: sparow receives the application data through
    # create_sp(), which the generator cannot see into.
    for name in ("APP_DATA", "app_data"):
        value = getattr(module, name, None)
        if isinstance(value, dict):
            return value
    return None


# ---- Validating the scenario data file ---------------------------------------


def load_scenarios(path, app_data=None):
    """Read and validate the scenario data file, returning its scenarios."""
    # These checks mirror what sparow itself requires, so that a bad file
    # fails here with a readable message rather than deep inside sparow.
    if not os.path.isfile(path):
        raise SystemExit(f"{path}: scenario data file not found")
    try:
        with open(path) as fp:
            scenario_data = json.load(fp)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}")

    # Check the overall shape before looking inside it, so a file of the
    # wrong structure gets a message rather than an AttributeError.
    if not isinstance(scenario_data, dict):
        raise SystemExit(f"{path}: top level must be a JSON object")
    scenarios = scenario_data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise SystemExit(f"{path}: 'scenarios' must be a non-empty list")
    if not isinstance(scenario_data.get("data", {}), dict):
        raise SystemExit(f"{path}: 'data' must be a JSON object")

    # Every scenario needs a unique ID: sparow keys scenarios and bundles by
    # it, and --scenario-models uses it to name a subpackage.  IDs must be
    # strings, because the builder receives them unconverted and builds
    # module names from them.
    ids = []
    for i, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise SystemExit(f"{path}: scenario {i} is not a JSON object")
        if "ID" not in scenario:
            raise SystemExit(f"{path}: scenario {i} has no 'ID'")
        if not isinstance(scenario["ID"], str):
            raise SystemExit(
                f"{path}: scenario {i} 'ID' must be a string "
                f"(found {scenario['ID']!r})"
            )
        ids.append(scenario["ID"])

    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise SystemExit(f"{path}: duplicate scenario IDs: {sorted(duplicates)}")

    if app_data is None:
        # The app script does not expose its application data, so the key
        # collision below cannot be checked here; sparow will assert instead.
        return scenarios

    # sparow merges the application data, the "data" block, and each scenario
    # into one dict and asserts that no key is defined twice.  Catch that here.
    # `shared` accumulates the keys every scenario inherits; its values are
    # never read.  Scenario keys are checked only against it, not against one
    # another, since each scenario is merged separately.
    shared = dict(app_data)
    for key in scenario_data.get("data", {}):
        if key in shared:
            raise SystemExit(
                f"{path}: 'data' key {key!r} is already defined in the app "
                f"script's application data"
            )
        shared[key] = None
    for scenario in scenarios:
        for key in scenario:
            if key in shared:
                raise SystemExit(
                    f"{path}: scenario {scenario['ID']!r} key {key!r} is already "
                    f"defined in the application data or the 'data' block"
                )

    return scenarios


# ---- Rendering pieces of the generated __init__.py ---------------------------


def render_imports(editable):
    """Render the generated module's import block."""
    names = ["json"]
    if editable:
        # Loads the app script from its original location.
        names.append("importlib.util")
    else:
        # Locates the scenario data file copied into the package.
        names.append("os")
    return "\n".join(f"import {name}" for name in sorted(names))


def render_app_import(app_script, editable):
    """Render the block that makes the app script available as APP_MODULE."""
    if not editable:
        return f"from . import {APP_MODULE}\n"
    # repr() yields a valid Python string literal for any path, including
    # ones containing quotes or backslashes.
    return LOAD_IN_PLACE.substitute(
        path=repr(os.path.abspath(app_script)), app_module=APP_MODULE
    )


def render_scenario_file(scenarios, editable):
    """Render the SCENARIO_FILE definition read by the generated create_sp()."""
    if not editable:
        # Resolved against the package's own location at import time, so
        # create_sp() works whatever the caller's working directory is.
        return (
            "#: Scenario data file, copied into this package.\n"
            "SCENARIO_FILE = os.path.join(os.path.dirname(__file__), "
            f"{SCENARIO_FILE!r})\n"
        )
    return (
        "#: Scenario data file, loaded in place rather than copied into this "
        "package.\n"
        f"SCENARIO_FILE = {os.path.abspath(scenarios)!r}\n"
    )


# ---- Copying model directories -----------------------------------------------


def model_dir_name(source):
    """Return the subpackage name a model tree is copied to, and check it."""
    if not os.path.isdir(source):
        raise SystemExit(f"{source}: model directory not found")
    # normpath drops a trailing slash, which would otherwise make basename
    # return "".  The name must be importable, since the copy is a subpackage.
    label = os.path.basename(os.path.normpath(source))
    if not label.isidentifier():
        raise SystemExit(
            f"{source}: directory name {label!r} is not a valid Python "
            f"identifier, so it cannot name a subpackage"
        )
    return label


def copy_tree(source, dest, link, display):
    """Copy the model tree `source` to `dest`, or symlink it when `link`."""
    label = os.path.basename(os.path.normpath(source))
    if link:
        # An absolute target keeps the link valid regardless of where the
        # package directory sits relative to the source.
        os.symlink(os.path.abspath(source), dest, target_is_directory=True)
        print(f"  {display}/  (link to {label}/)")
    else:
        shutil.copytree(source, dest)
        print(f"  {display}/  (copy of {label}/)")


def copy_scenario_dirs(source, package_dir, name, scenarios, link, customize):
    """
    Copy the model tree once per scenario into the new package directory, as a
    subpackage named for the scenario ID, or symlink it when `link`.

    When `customize` is given, call it as customize(ID, scenario) after each
    copy, with the working directory set to that copy.
    """
    # Validate the source and every ID before copying anything, so a bad ID
    # late in the list does not leave some scenarios copied and others not.
    model_dir_name(source)
    for scenario in scenarios:
        scenario_id = scenario["ID"]
        if not scenario_id.isidentifier():
            raise SystemExit(
                f"scenario ID {scenario_id!r} is not a valid Python identifier, so "
                f"it cannot name a scenario package"
            )

    for scenario in scenarios:
        scenario_id = scenario["ID"]
        dest = os.path.join(package_dir, scenario_id)
        copy_tree(source, dest, link, os.path.join(name, scenario_id))
        if customize is None:
            continue
        # Run the hook inside the fresh copy so it can edit files by relative
        # path, and always restore the working directory: later relative
        # paths in this run (dest, the package directory) depend on it.
        cwd = os.getcwd()
        os.chdir(dest)
        try:
            customize(scenario_id, scenario)
        except Exception as exc:
            raise SystemExit(
                f"customize_scenario({scenario_id!r}, ...) failed: {exc!r}"
            )
        finally:
            os.chdir(cwd)
        print(f"      customized by customize_scenario({scenario_id!r}, ...)")


# ---- Package directory handling ----------------------------------------------


def check_inputs_outside(package_dir, inputs):
    """
    Exit if any of the generator's `inputs` lives inside the existing package
    directory, which replacing it would delete.
    """
    # Only a real directory can contain anything; a symlink or file in the
    # way is simply replaced.
    if os.path.islink(package_dir) or not os.path.isdir(package_dir):
        return

    # Compare fully resolved paths, so an input reached through a symlink or
    # a "../" path is still recognized as living inside the directory.
    # commonpath rather than startswith, so that "pkg2" is not mistaken for
    # being inside "pkg".
    real_package_dir = os.path.realpath(package_dir)
    for path in inputs:
        if path is None:
            continue
        real_path = os.path.realpath(path)
        if os.path.commonpath([real_package_dir, real_path]) == real_package_dir:
            raise SystemExit(
                f"{path}: is inside {package_dir}, which --force would delete"
            )


def remove_path(path):
    """Remove a directory tree, or a file or symlink, at `path`."""
    # Never rmtree through a symlink: that would delete whatever it points to.
    if os.path.islink(path) or not os.path.isdir(path):
        os.unlink(path)
    else:
        # rmtree removes symlinks found inside the tree (such as -e scenario
        # links) without following them, so the linked originals survive.
        shutil.rmtree(path)


def import_path_of(package_dir):
    """
    Return the dotted import path of `package_dir`, found by walking up through
    enclosing directories that are themselves packages (contain __init__.py).
    """
    # Used only for the header and the closing message.  Namespace packages
    # (no __init__.py) end the walk, so the path may be shorter than the one
    # users actually import.
    parts = [os.path.basename(package_dir)]
    parent = os.path.dirname(package_dir)
    while os.path.isfile(os.path.join(parent, "__init__.py")):
        parts.append(os.path.basename(parent))
        parent = os.path.dirname(parent)
    return ".".join(reversed(parts))


def build_package(
    args,
    staging_dir,
    package_dir,
    scenarios,
    model_dir,
    scenario_models,
    link_scenario_models,
    customize,
):
    """
    Write the complete package into `staging_dir`, which main() then renames
    to `package_dir`.  Returns the package's import path.
    """
    # The shared -m copy is linked under -e like everything else; only
    # per-scenario copies have the customize_scenario exception.
    if model_dir is not None:
        label = model_dir_name(model_dir)
        copy_tree(
            model_dir,
            os.path.join(staging_dir, label),
            args.editable,
            os.path.join(args.name, label),
        )

    if scenario_models is not None:
        copy_scenario_dirs(
            scenario_models,
            staging_dir,
            args.name,
            scenarios,
            link_scenario_models,
            customize,
        )

    # In -e mode nothing is copied: the generated __init__.py records the
    # original paths instead (see render_app_import, render_scenario_file).
    if not args.editable:
        for path, copy_name in (
            (args.app_script, f"{APP_MODULE}.py"),
            (args.scenarios, SCENARIO_FILE),
        ):
            shutil.copyfile(path, os.path.join(staging_dir, copy_name))
            print(
                f"  {os.path.join(args.name, copy_name)}  "
                f"(copy of {os.path.basename(path)})"
            )

    # __init__.py is written last.  The import path is worked out from the
    # final location, not the staging directory.
    import_path = import_path_of(os.path.abspath(package_dir))
    source = MODULE_TEMPLATE.substitute(
        import_path=import_path,
        script=os.path.basename(__file__),
        app_script=os.path.basename(args.app_script),
        scenario_source=os.path.basename(args.scenarios),
        app_module=APP_MODULE,
        imports=render_imports(args.editable),
        app_import=render_app_import(args.app_script, args.editable),
        scenario_file=render_scenario_file(args.scenarios, args.editable),
    )

    init_path = os.path.join(staging_dir, "__init__.py")
    with open(init_path, "w") as output:
        output.write(source)
    print(f"  {os.path.join(args.name, '__init__.py')}  (create_sp)")
    return import_path


# ---- Command line ------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate a sparow stochastic program application package "
        "from an app script defining create_sp(scenario_data)."
    )
    parser.add_argument(
        "app_script",
        metavar="APP_SCRIPT",
        help="Python script defining create_sp(scenario_data), which builds "
        "the stochastic program from the parsed scenario data file",
    )
    parser.add_argument(
        "-n",
        "--name",
        required=True,
        help="name of the generated package, e.g. load_scenarios",
    )
    parser.add_argument(
        "-e",
        "--editable",
        action="store_true",
        help="use the original app script, scenario data file and model "
        "directories, so edits take effect without regenerating: the app script "
        "and scenario data are loaded in place rather than copied into the "
        "package as %s.py and %s, and model directories are symlinks rather "
        "than copies (per-scenario models are still copied when the app script "
        "defines customize_scenario).  By default all are copied, which makes "
        "the package self-contained" % (APP_MODULE, SCENARIO_FILE),
    )
    parser.add_argument(
        "-m",
        "--model-dir",
        metavar="DIR",
        help="model tree to copy once into the package, as a subpackage keeping "
        "its directory name; "
        "the app script imports it with importlib.import_module('.<DIR name>', "
        "__package__)",
    )
    parser.add_argument(
        "--scenario-models",
        metavar="DIR",
        help="model tree to copy once per scenario ID, as a subpackage named "
        "for the ID; the app "
        "script imports its copy with importlib.import_module('.' + data['ID'], "
        "__package__).  If the app script defines customize_scenario(name, "
        "data), it is called for each scenario in its copy",
    )
    parser.add_argument(
        "-s",
        "--scenarios",
        metavar="FILE",
        required=True,
        help="JSON scenario data file read by the generated create_sp(); copied "
        "into the package as %s unless --editable" % SCENARIO_FILE,
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="replace the generated package directory if it already exists",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=os.getcwd(),
        help="directory the package is written to, i.e. the directory of the "
        "parent package (default: the current directory)",
    )
    args = parser.parse_args(argv)

    # Phase 1: validate everything before touching the filesystem.  Every
    # check up to "Phase 2" can fail without leaving anything behind.  All
    # input paths are taken relative to the current directory.

    if not args.name.isidentifier():
        raise SystemExit(f"--name {args.name!r} is not a valid Python identifier")

    outdir = args.output_dir
    if not os.path.isdir(outdir):
        raise SystemExit(f"{outdir}: output directory not found")

    # The app script is loaded first because its APP_DATA feeds the scenario
    # file's key-collision check, and its customize_scenario (if any) decides
    # how --scenario-models behaves under -e.
    app_module = load_app_script(args.app_script)
    scenarios = load_scenarios(args.scenarios, app_data_of(app_module))
    ids = [scenario["ID"] for scenario in scenarios]
    customize = getattr(app_module, "customize_scenario", None)

    model_dir = args.model_dir
    if model_dir is not None:
        # `label` is the subpackage name of the -m copy.  It must not shadow
        # the app module or, with per-scenario copies, a scenario subpackage.
        label = model_dir_name(model_dir)
        if label == APP_MODULE:
            raise SystemExit(f"{model_dir}: {label!r} is reserved for the app script")
        if args.scenario_models is not None and label in ids:
            raise SystemExit(
                f"{model_dir}: {label!r} is also a scenario ID, so its copy would "
                f"collide with that scenario's model copy"
            )

    scenario_models = args.scenario_models
    if scenario_models is not None:
        if APP_MODULE in ids:
            raise SystemExit(f"scenario ID {APP_MODULE!r} is reserved for the app script")
    elif customize is not None:
        # Not an error: the same app script may be used with and without
        # per-scenario copies.
        print(
            "Note: the app script defines customize_scenario, which is only "
            "called with --scenario-models"
        )
    # Customizing through a symlink would edit the shared original tree.
    link_scenario_models = args.editable and customize is None

    # lexists() rather than exists(), so that a dangling symlink at the
    # package path also counts as "already there".
    package_dir = os.path.join(outdir, args.name)
    replaced = os.path.lexists(package_dir)
    if replaced:
        if not args.force:
            raise SystemExit(
                f"{package_dir}: already exists; pass -f/--force to replace it"
            )
        check_inputs_outside(
            package_dir,
            [args.app_script, args.scenarios, model_dir, scenario_models],
        )

    # Phase 2: build the package in a staging directory beside the target, so
    # a failure part-way (a failed copy, a customize_scenario error, Ctrl-C)
    # leaves any existing package untouched.  The leading dot keeps the
    # staging directory from looking like a package, and being in the same
    # directory as the target makes the final rename a cheap, same-filesystem
    # operation.
    staging_dir = tempfile.mkdtemp(prefix=f".{args.name}.", dir=outdir)
    print(f"Generating package '{args.name}/' in {os.path.abspath(outdir)}")
    try:
        # mkdtemp makes the directory private (0o700); give it the permissions
        # an ordinary mkdir would, since it becomes the package directory.
        umask = os.umask(0)
        os.umask(umask)
        os.chmod(staging_dir, 0o777 & ~umask)
        import_path = build_package(
            args,
            staging_dir,
            package_dir,
            scenarios,
            model_dir,
            scenario_models,
            link_scenario_models,
            customize,
        )
    except BaseException:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise

    # Phase 3: swap the staged package in.  The old package is moved aside
    # rather than deleted first, so that if the rename fails it can be put
    # back; only once the new package is in place is the old one removed.
    if replaced:
        backup = staging_dir + ".old"
        os.rename(package_dir, backup)
        try:
            os.rename(staging_dir, package_dir)
        except BaseException:
            os.rename(backup, package_dir)
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise
        remove_path(backup)
    else:
        os.rename(staging_dir, package_dir)
    print(f"{'Replaced' if replaced else 'Created'} package '{args.name}/'")

    # Summary: in -e mode, list every original the package now depends on.
    if args.editable:
        print(f"\nApp script loaded in place from {os.path.abspath(args.app_script)}")
        print(f"Scenario data loaded in place from {os.path.abspath(args.scenarios)}")
        if model_dir is not None:
            print(f"Model package links to {os.path.abspath(model_dir)}")
        if scenario_models is not None and link_scenario_models:
            print(f"Scenario packages link to {os.path.abspath(scenario_models)}")
        print("Moving or deleting these will break the generated package.")
    print(f"\nScenarios in {args.scenarios}: {', '.join(ids)}")
    print("\nImport path:")
    print(f"  from {import_path} import create_sp")
    print("  sp = create_sp()")


# Errors are reported by raising SystemExit with a message, which Python
# prints to stderr with exit status 1; main() itself returns None (status 0).
if __name__ == "__main__":
    sys.exit(main())
