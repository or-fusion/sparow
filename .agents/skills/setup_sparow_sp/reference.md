# The sparow stochastic program contract

Details the app script and the generated package must respect.  Source of
truth: `sparow/sp/api.py`, `sparow/sp/sp.py`, `sparow/sp/sp_pyomo.py`,
`sparow/sp/bundling/`, and for the packaging, `sparow/bin/setup_sparow_sp.py`.

## Construction sequence

```python
sp = stochastic_program(first_stage_variables=[...])   # sparow/sp/api.py
sp.initialize_application(app_data={...})              # or filename="app.json"
sp.initialize_model(model_data={...}, model_builder=scenario_builder)
```

`stochastic_program()` accepts only keyword arguments and currently supports
`aml="pyomo"`; passing `model_builder_list` raises (no multi-stage support yet).

`initialize_model()` accepts either `model_data=` (a parsed dict, what the app
script's `create_sp` receives) or `filename=` (a path sparow parses itself).
Either way the call also builds the default bundles — `single_scenario`, one per
scenario — which is why it must come after `initialize_application()`.  It does
not reject unknown keywords: misspell `model_builder=` and no builder is
registered, which surfaces only later as `KeyError: None`.

`create_EF()` re-bundles under the `single_bundle` scheme, replacing those
defaults, so inspect `get_bundles()` before calling it.

## Scenario data file

```json
{
    "data":      {"horizon": 12},
    "scenarios": [{"ID": "low", "Probability": 0.25, "demand": 15},
                  {"ID": "high", "Probability": 0.75, "demand": 100}]
}
```

* The top level is a JSON object.  `"scenarios"` is required and must be a
  non-empty list of objects; every entry needs a unique `"ID"`, which
  `setup-sparow-sp` requires to be a string (`"1"`, not `1`).
* `"data"` is optional — an object of parameters shared by every scenario of
  this model.
* `"Probability"` is capitalized.  Values are normalized by their sum, so they
  need not total 1.  If *any* scenario omits it, sparow ignores the key entirely
  and assumes a uniform distribution (`sparow/sp/bundling/SF_schemes.py`).
  Note that `doc/sphinx/getting_started/simple.rst` writes it lowercase; the
  code reads `"Probability"`.
* With `--scenario-models`, every `"ID"` must be a valid Python identifier (it
  names a subpackage) and must not be `_app`.

## App script contract

The script handed to `setup-sparow-sp` must define

```python
def create_sp(scenario_data):   # -> configured stochastic_program
```

which the generated package's `create_sp()` calls with the parsed scenario
file.  It may also define

```python
def customize_scenario(name, data):   # called at generate time
```

used only with `--scenario-models`: the command calls it once per scenario
after copying that scenario's model directory, with the working directory set
to the copy.  `name` is the scenario ID; `data` is the scenario's own entry in
the scenario file.  Both are checked for arity before anything is written.

Naming the application data `APP_DATA` (or `app_data`) at module level is
conventional, not required; the command uses it, when present, to check the
scenario file for the key collisions described below.

The command imports the script standalone to validate it, so it must not rely
on being part of its surrounding package at import time.  In the generated
package it is loaded as `<name>._app` — copied there by default, or from its
original path under `-e` — so `__package__` is the generated package and model
directories are imported relative to it, inside functions:

```python
importlib.import_module(".model", __package__)        # -m model
importlib.import_module("." + data["ID"], __package__) # --scenario-models
```

## The scenario builder

`scenario_builder(data, args)` returns a fresh Pyomo `ConcreteModel` per call.
The name is conventional; `create_sp` registers whatever function it likes.

`data` is assembled by `_create_scenario()` as the merge, in this order, of

1. `app_data`,
2. the scenario file's `"data"` block,
3. the scenario's own entry (including `"ID"` and `"Probability"`),

**and sparow asserts that no key appears in more than one of them.**  A key
defined in both `APP_DATA` and a scenario aborts model construction, so the
command validates this up front and fails with a readable message instead.

`args` is always `{}`.

## First-stage variables

Strings parsed as Pyomo `ComponentUID`s and resolved against each scenario
model; an unresolvable name raises `Pyomo error: Unknown variable '<name>'`.

```python
"x"                                          # scalar Var
"DevotedAcreage[*]"                          # every member of an indexed Var
"investmentStage[*].genInstalled[*].binary_indicator_var"   # GDP disjuncts
```

The same names must exist, with the same index sets, in every scenario model —
they are the non-anticipative variables tied across scenarios.

## Multiple models in one SP

`initialize_model(name=..., default=...)` registers several named models against
one `sp` (multifidelity work, and `sparow/sp/examples/farmers/MRPfarmers.py`).
The app script template registers a single unnamed model; add `name=` and
repeated `initialize_model()` calls there only when the application genuinely
needs them.
