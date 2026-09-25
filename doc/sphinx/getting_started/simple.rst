################
A Simple Example
################

Sparow provides a structured API for defining stochastic programming problems. The key components are:

1. **Application Data**: Problem parameters (constants)
2. **Model Data**: Scenario-specific data
3. **Builder Function**: Creates Pyomo models for scenarios
4. **Stochastic Program**: Container for the complete formulation

This approach separates concerns and enables flexible problem definition.

The General Workflow
--------------------

All Sparow formulations follow this pattern:

.. code-block:: python

   from sparow.sp import stochastic_program

   # 1. Define application data (constants)
   app_data = {...}

   # 2. Define model data (scenarios)
   model_data = {"scenarios": [...]}

   # 3. Define builder function
   def builder(data, args):
       # Create and return Pyomo model
       return model

   # 4. Create stochastic program
   sp = stochastic_program(first_stage_variables=[...])

   # 5. Initialize application
   sp.initialize_application(app_data=app_data)

   # 6. Initialize model
   sp.initialize_model(model_data=model_data, model_builder=builder)

Let's explore each component in detail using the newsvendor example.

Application Data
---------------

Application data contains problem parameters that are constant across all scenarios:

.. code-block:: python

   # Newsvendor example: application data
   app_data = dict(c=1.0, b=1.5, h=0.1)

   # General pattern:
   app_data = {
       'param1': value1,
       'param2': value2,
       # ... other constant parameters
   }

**Characteristics:**
- Constants that don't vary by scenario
- Used in all scenarios
- Typically includes costs, capacities, limits

Model Data
----------

Model data defines scenario-specific information:

.. code-block:: python

   # Newsvendor example: model data
   model_data = {
       "scenarios": [
           {"ID": 1, "d": 15},
           {"ID": 2, "d": 60},
           # ... more scenarios
       ],
   }

   # General pattern:
   model_data = {
       "scenarios": [
           {"ID": 1, "param1": value1, "param2": value2, ...},
           {"ID": 2, "param1": value3, "param2": value4, ...},
           # ... more scenarios
       ],
   }

**Characteristics:**
- Each scenario has a unique `ID`
- Contains parameters that vary by scenario
- Typically includes demands, prices, yields, etc.

**Scenario Probabilities:**

You can specify probabilities for each scenario:

.. code-block:: python

   model_data = {
       "scenarios": [
           {"ID": 1, "d": 15, "probability": 0.1},
           {"ID": 2, "d": 60, "probability": 0.6},
           {"ID": 3, "d": 100, "probability": 0.3},
       ],
   }

If probabilities are not specified, scenarios are assumed to be equally likely.

Builder Function
---------------

The builder function creates a Pyomo model for a single scenario:

.. code-block:: python

   # Newsvendor example: builder function
   def builder(data, args):
       """
       Create a Pyomo model for a single scenario.

       Parameters
       ----------
       data : dict
           Contains app_data + scenario-specific data
       args : dict
           Additional arguments (optional)

       Returns
       -------
       pyomo.ConcreteModel
           Model for this scenario
       """
       # Extract parameters
       b = data["b"]  # From app_data
       c = data["c"]  # From app_data
       h = data["h"]  # From app_data
       d = data["d"]  # From scenario data

       # Create Pyomo model
       M = pyo.ConcreteModel(data["ID"])

       # Define variables, constraints, objective
       # ... (Pyomo model construction)

       return M

**Key Requirements:**
- Must accept `data` and `args` parameters
- Must return a Pyomo `ConcreteModel`
- Must be pure (no side effects)
- Called once for each scenario

**The `data` Parameter:**

The `data` dictionary contains:
- All keys from `app_data`
- All keys from the specific scenario
- Special key `"ID"` with the scenario ID

This allows the builder to access both constant and scenario-specific parameters.

Stochastic Program Creation
----------------------------

Use `stochastic_program()` to create the container:

.. code-block:: python

   from sparow.sp import stochastic_program

   # Newsvendor example
   sp = stochastic_program(first_stage_variables=["x"])

   # General pattern
   sp = stochastic_program(first_stage_variables=[var1, var2, ...])

**Parameters:**
- `first_stage_variables`: List of variable names that are first-stage decisions
- `aml`: Modeling framework (default: "pyomo")

**First-Stage Variables:**

First-stage variables represent "here-and-now" decisions made before uncertainty is revealed:

.. code-block:: python

   # Single first-stage variable
   sp = stochastic_program(first_stage_variables=["x"])

   # Multiple first-stage variables
   sp = stochastic_program(first_stage_variables=["x1", "x2", "x3"])

These variables must match the names used in your Pyomo model.

Initializing the Application
---------------------------

Load application data into the stochastic program:

.. code-block:: python

   # From dictionary
   sp.initialize_application(app_data=app_data)

   # From JSON file
   sp.initialize_application(filename="app_data.json")

This step loads the constant parameters that will be used across all scenarios.

Initializing the Model
----------------------

Load model data and register the builder function:

.. code-block:: python

   # From dictionary
   sp.initialize_model(
       model_data=model_data,
       model_builder=builder
   )

   # From JSON file
   sp.initialize_model(
       filename="model_data.json",
       model_builder=builder
   )

**What This Does:**
1. Loads scenario data
2. Registers the builder function
3. Creates the scenario tree
4. Sets up bundles for the solver
5. Validates the formulation

Complete Formulation Example
----------------------------

Here's a complete formulation using the newsvendor problem:

.. code-block:: python

   from sparow.sp import stochastic_program
   import pyomo.environ as pyo

   # Step 1: Application data (constants)
   app_data = dict(c=1.0, b=1.5, h=0.1)

   # Step 2: Model data (scenarios)
   model_data = {
       "scenarios": [
           {"ID": 1, "d": 15},
           {"ID": 2, "d": 60},
           {"ID": 3, "d": 72},
           {"ID": 4, "d": 78},
           {"ID": 5, "d": 82},
       ],
   }

   # Step 3: Builder function
   def builder(data, args):
       # Extract parameters
       b = data["b"]
       c = data["c"]
       h = data["h"]
       d = data["d"]

       # Create Pyomo model
       M = pyo.ConcreteModel(data["ID"])

       # Define variables
       M.x = pyo.Var(within=pyo.NonNegativeReals)  # First-stage
       M.y = pyo.Var()  # Second-stage

       # Define constraints
       M.greater = pyo.Constraint(expr=M.y >= (c - b) * M.x + b * d)
       M.less = pyo.Constraint(expr=M.y >= (c + h) * M.x - h * d)

       # Define objective
       M.o = pyo.Objective(expr=M.y)

       return M

   # Step 4: Create stochastic program
   sp = stochastic_program(first_stage_variables=["x"])

   # Step 5: Initialize application
   sp.initialize_application(app_data=app_data)

   # Step 6: Initialize model
   sp.initialize_model(model_data=model_data, model_builder=builder)

   # Formulation is now complete and ready to solve
   print(f"Created stochastic program with {len(sp.scenario_data[None])} scenarios")
