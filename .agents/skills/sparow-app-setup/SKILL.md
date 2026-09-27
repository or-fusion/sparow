---
name: sparow-app-setup
description: Generate a custom sparow stochastic program application package from a user-supplied app script defining create_sp(scenario_data), using the setup-sparow-sp command. Use when asked to scaffold, set up, or generate a sparow SP application or a create_sp() module for a new stochastic program, or when wiring an existing Pyomo model builder into sparow.
---

# Generating a sparow application

A sparow application is a Python package whose `create_sp()` returns a
configured `stochastic_program`.  This skill does not write that package
directly — you write an **app script** that defines the model, and the
`setup-sparow-sp` command (`sparow/bin/setup_sparow_sp.py`) generates the
package from it and a scenario data file:

```
app script ──────┐
                 ├─> setup-sparow-sp ──> <name>/__init__.py   (create_sp())
scenario JSON ───┘                       <name>/_app.py       (copy of app script)
                                         <name>/scenarios.json
```

The app script owns everything application-specific; the command owns the
packaging, the scenario-file plumbing and the model-directory copies.

Read `reference.md` before writing the app script — it covers the app script
contract, the data-merge rules, the `"Probability"` key, and the first-stage
variable syntax.

## 1. The app script

`templates/app_script.py` is the starting point.  The one required entry point,
which the command checks by name and arity before writing anything, is:

```python
def create_sp(scenario_data):   # -> configured stochastic_program
```

`scenario_data` is the parsed scenario JSON.  `create_sp` builds the
`stochastic_program` and registers the app script's own builder, conventionally
`scenario_builder(data, args)`:

```python
sp.initialize_model(model_data=scenario_data, model_builder=scenario_builder)
```

Keep sparow's keyword as `model_builder=`.  `initialize_model` does not reject
unknown keywords, so a misspelled one registers nothing and fails much later
with an unhelpful `KeyError: None`.

Everything else lives here too: application data, first-stage variables, the
Pyomo model.  Name the application data `APP_DATA` at module level and the
command will check it against the scenario file for the key collisions that
sparow otherwise catches with a bare `assert` deep in model construction.

If the user already has a Pyomo model builder, wrap it rather than rewriting it:
`scenario_builder()` becomes the adapter that pulls the builder's keyword
arguments out of `data`.

The command imports the script standalone to validate it, so it must not
depend on its surrounding package at import time.  Imports of model
directories (below) belong inside functions.

## 2. Model directories (optional)

When the Pyomo model lives in its own package directory, the command can copy
it into the generated package.  The app script is always loaded as
`<name>._app`, so it imports the copy relative to `__package__`.

**Once** (`-m/--model-dir DIR`) — copied to `<name>/<dirname>/`:

```python
def scenario_builder(data, args):
    model = importlib.import_module(".model", __package__)
    return model.create_model(alpha=data["alpha"])
```

**Once per scenario** (`--scenario-models DIR`) — copied to `<name>/<ID>/` for
every scenario ID.  Use this only when scenarios need physically separate
module state, as the GTEP examples under `sparow_examples/` do.  Every scenario
ID must be a valid Python identifier.

```python
def scenario_builder(data, args):
    model = importlib.import_module("." + data["ID"], __package__)
    return model.create_model(alpha=data["alpha"])
```

With `--scenario-models`, the app script may also define

```python
def customize_scenario(name, data):
```

which the command calls once per scenario, right after copying that
scenario's model directory, **with the working directory set to the copy** —
use it to rewrite files in the copy.  `name` is the scenario ID and `data` is
that scenario's entry in the scenario JSON (not the merged data the builder
sees).  It is ignored, with a note, when `--scenario-models` is not given.

The two options combine: shared code once with `-m`, per-scenario state with
`--scenario-models`.

Like every other input path, both are resolved relative to the current
directory, whatever `-o` is.

## 3. Run the command

```bash
cd <parent package directory>
setup-sparow-sp my_app.py -n <name> -s scenarios.json [-m model] [--scenario-models model]
```

| Option | Meaning |
| --- | --- |
| `APP_SCRIPT` | The app script (positional, first) |
| `-n/--name` | Name of the generated package (required) |
| `-s/--scenarios` | Scenario JSON (required); copied in as `scenarios.json` |
| `-m/--model-dir` | Model directory copied once |
| `--scenario-models` | Model directory copied once per scenario |
| `-e/--editable` | Use originals in place rather than copies (below) |
| `-f/--force` | Replace `<name>/` if it already exists |
| `-o/--output-dir` | Directory to write `<name>/` into (default: current) |

`templates/scenarios.json` is a starting point for the scenario file — offer
it when the user has no scenario data yet, but do not invent scenario values
for a real application.

The generated package's import path is worked out by walking up through
parent directories that contain `__init__.py`, and printed at the end.

By default the app script, scenario file and model directories are all
**copied**, so the package is self-contained and installs or relocates as one
unit; re-run with `-f` after editing any of them.  `-e` instead loads the app
script and scenario file from their original paths and symlinks the model
directories, so edits take effect without regenerating — at the cost of a
package that breaks if they move.  Per-scenario directories are still real
copies under `-e` when the app script defines `customize_scenario`, since
customizing through a link would edit the shared original.  Prefer the default
for anything committed or shared, and `-e` while iterating on the model.

An existing `<name>/` is never overwritten without `-f`, and `-f` refuses to
run if any input lives inside the directory it would delete.  The package is
built in a hidden staging directory beside the target and swapped in only
when complete, so a failure part-way — including an exception from
`customize_scenario` — leaves any existing package untouched.

## 4. Verify

Build the SP and its extensive form — this exercises the app script, the data
merge, the model-directory imports and every first-stage variable name without
needing a solver:

```bash
python -c "
from <import path> import create_sp
sp = create_sp()
print('bundles:', list(sp.get_bundles()))
sp.create_EF()
print('shared:', [sp.get_variable_name(v) for v in sp.shared_variables()])
"
```

Expect one bundle per scenario in the data file, and one shared variable per
first-stage variable the CUID patterns expand to.  An empty `shared` list means
`FIRST_STAGE_VARIABLES` matched nothing and the scenarios are not actually tied
together.  Keep this call order: `create_EF()` re-bundles into a single bundle,
so `get_bundles()` must come before it and `shared_variables()` after.

## Notes

* Never hand-edit the generated `__init__.py`; it says so in its header.  Fix
  the app script or scenario file and re-run with `-f`.
* Two `create_sp` functions exist: the app script's takes `(scenario_data)`,
  the generated package's takes no arguments, reads its scenario file and
  calls the former.
* A packaged (non-editable) install of the generated package includes the
  copied `scenarios.json` only if the project's setuptools configuration
  includes package data, e.g. `[tool.setuptools.package-data]`.
* The older `setup_*.py` scripts in `sparow_examples/` inline the builder and
  `model_data` into the generated module.  Prefer `setup-sparow-sp`; reach for
  the inlined form only when asked to match those existing examples exactly.
