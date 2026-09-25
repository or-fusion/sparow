############
Formulation
############

Formulating Stochastic Programs with Sparow
=============================================

This guide illustrates the general Sparow API for formulating stochastic programming problems using the newsvendor example as a concrete illustration. The same pattern applies to all Sparow formulations.

Sparow's Formulation API
------------------------

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

**Examples from other problems:**
- Facility location: Fixed costs, capacities
- Portfolio optimization: Transaction costs, risk limits
- Production planning: Machine capacities, labor costs

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

Formulation Patterns
--------------------

Single-Stage Problems
~~~~~~~~~~~~~~~~~~~~~

For problems with only second-stage variables:

.. code-block:: python

   # No first-stage variables
   sp = stochastic_program(first_stage_variables=[])

Multi-Stage Problems
~~~~~~~~~~~~~~~~~~~~

For problems with multiple decision stages, use the same pattern but with more complex builder functions that handle multiple stages.

Multiple Models
~~~~~~~~~~~~~~~

You can define multiple models in a single stochastic program:

.. code-block:: python

   # Initialize multiple models
   sp.initialize_model(name="model1", model_data=data1, model_builder=builder1)
   sp.initialize_model(name="model2", model_data=data2, model_builder=builder2)

This is useful for multi-fidelity modeling or comparing different formulations.

Validation and Debugging
------------------------

**Checking Your Formulation:**

.. code-block:: python

   # Check scenario data
   print(f"Number of scenarios: {len(sp.scenario_data[None])}")

   # Check first-stage variables
   print(f"First-stage variables: {sp.first_stage_variables}")

   # Check application data
   print(f"Application data: {sp.app_data}")

**Common Issues:**

1. **Variable Name Mismatch**: First-stage variables in `stochastic_program()` must match Pyomo model
2. **Missing Data**: Builder function must handle all required parameters
3. **Probability Errors**: Scenario probabilities must sum to 1 (or be unspecified for equal weighting)
4. **Builder Errors**: Builder function must be pure and handle all scenarios

Best Practices
--------------

1. **Start Simple**: Begin with a small number of scenarios
2. **Validate Data**: Check that all parameters are correctly specified
3. **Test Builder**: Verify the builder works for individual scenarios
4. **Use Descriptive Names**: Clear variable and parameter names
5. **Document Assumptions**: Comment your formulation decisions
6. **Modular Design**: Keep builder functions focused and reusable

Advanced Formulation Techniques
--------------------------------

Scenario Generation
~~~~~~~~~~~~~~~~~~

Generate scenarios programmatically:

.. code-block:: python

   import numpy as np

   # Generate scenarios from a distribution
   demands = np.random.normal(loc=50, scale=15, size=100)
   model_data = {
       "scenarios": [
           {"ID": i, "d": float(d)}
           for i, d in enumerate(demands, 1)
       ],
   }

Conditional Parameters
~~~~~~~~~~~~~~~~~~~~~~

Use conditional logic in the builder:

.. code-block:: python

   def builder(data, args):
       # Different constraints based on scenario type
       if data["scenario_type"] == "high_demand":
           # Use one set of constraints
           pass
       else:
           # Use another set
           pass

Multi-Fidelity Modeling
~~~~~~~~~~~~~~~~~~~~~~

Combine models of different fidelity:

.. code-block:: python

   # Low-fidelity model (simpler, faster)
   sp.initialize_model(name="LF", model_data=lf_data, model_builder=lf_builder)

   # High-fidelity model (more detailed, slower)
   sp.initialize_model(name="HF", model_data=hf_data, model_builder=hf_builder)

This enables efficient exploration of the solution space.

Formulation Examples
--------------------

Newsvendor Problem
~~~~~~~~~~~~~~~~~~

The classic inventory management problem (shown above).

Facility Location
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Application data: fixed costs, capacities
   app_data = {
       "fixed_costs": [400000, 200000, 600000],
       "capacities": [1550, 650, 1750],
   }

   # Model data: customer demands
   model_data = {
       "scenarios": [
           {"ID": 1, "demands": [450, 910, 379, 91]},
           {"ID": 2, "demands": [650, 1134, 416, 113]},
           # ... more scenarios
       ],
   }

Farmers Problem
~~~~~~~~~~~~~~~

.. code-block:: python

   # Application data: crop parameters
   app_data = {
       "costs": {"wheat": 150, "corn": 230, "sugar_beets": 260},
       "prices": {"wheat": 170, "corn": 150, "sugar_beets": 36},
   }

   # Model data: yields by scenario
   model_data = {
       "scenarios": [
           {"ID": 1, "yields": {"wheat": 3.0, "corn": 3.6, "sugar_beets": 20}},
           # ... more scenarios
       ],
   }

Portfolio Optimization
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Application data: asset parameters
   app_data = {
       "assets": ["stocks", "bonds", "commodities"],
       "transaction_costs": {"stocks": 0.001, "bonds": 0.0005, "commodities": 0.002},
   }

   # Model data: returns by scenario
   model_data = {
       "scenarios": [
           {"ID": 1, "returns": {"stocks": 0.08, "bonds": 0.03, "commodities": 0.12}},
           # ... more scenarios
       ],
   }

Summary
-------

The Sparow formulation API provides a flexible and consistent way to define stochastic programming problems:

1. **Separate concerns**: Application data vs model data
2. **Modular design**: Builder functions for scenario models
3. **Clear structure**: Explicit initialization steps
4. **Flexible**: Supports various problem types and complexities

Once you understand this pattern, you can apply it to formulate any stochastic programming problem using Sparow. The same workflow applies whether you're solving inventory problems, facility location, portfolio optimization, or any other stochastic application.

For more examples, see the specific problem formulations in the :doc:`examples` section.