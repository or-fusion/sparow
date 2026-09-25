###########
Newsvendor
###########

Newsvendor Problem Examples
============================

The newsvendor problem is a classic stochastic programming example that demonstrates inventory management under uncertain demand. This example illustrates the key steps in using Sparow's API to set up and solve stochastic programming problems.

Problem Description
------------------

The newsvendor problem involves a retailer who must decide how much of a perishable product to order before knowing the actual demand. The key characteristics are:

* **Decision**: How much to order (x)
* **Uncertainty**: Demand (d) follows a probability distribution
* **Costs**:
  * **c**: Purchase cost per unit
  * **b**: Selling price per unit
  * **h**: Salvage value per unit (for unsold items)
* **Objective**: Maximize expected profit

Sparow API Workflow
-------------------

The newsvendor example demonstrates the standard Sparow workflow for setting up stochastic programs:

1. **Define application data** - Problem parameters in a dictionary
2. **Define model data** - Scenario-specific data
3. **Create builder function** - Returns a Pyomo model for a single scenario
4. **Create stochastic program** - Using `stochastic_program()`
5. **Initialize application** - Using `initialize_application()`
6. **Initialize model** - Using `initialize_model()`

Let's examine each step in detail:

Step 1: Application Data
------------------------

Application data contains the problem parameters that are constant across all scenarios:

.. code-block:: python

   # Data for a simple newsvendor example
   app_data = dict(c=1.0, b=1.5, h=0.1)

Here:
- `c=1.0`: Purchase cost per unit
- `b=1.5`: Selling price per unit
- `h=0.1`: Salvage value per unit

These parameters define the cost structure of the problem.

Step 2: Model Data
------------------

Model data defines the scenario-specific information:

.. code-block:: python

   model_data = {
       "scenarios": [
           {"ID": 1, "d": 15},
           {"ID": 2, "d": 60},
           {"ID": 3, "d": 72},
           {"ID": 4, "d": 78},
           {"ID": 5, "d": 82},
       ],
   }

Each scenario represents a different demand realization:
- `ID`: Unique scenario identifier
- `d`: Demand value for that scenario

Step 3: Builder Function
-------------------------

The builder function creates a Pyomo model for a single scenario:

.. code-block:: python

   def builder(data, args):
       """
       Build a Pyomo model for a single scenario.

       Parameters
       ----------
       data : dict
           Scenario-specific data (includes app_data and scenario data)
       args : dict
           Additional arguments

       Returns
       -------
       pyomo.ConcreteModel
           The constructed Pyomo model for this scenario
       """
       # Extract parameters from data
       b = data["b"]  # Selling price
       c = data["c"]  # Purchase cost
       h = data["h"]  # Salvage value
       d = data["d"]  # Demand for this scenario

       # Create Pyomo model
       M = pyo.ConcreteModel(data["ID"])

       # Define variables
       M.x = pyo.Var(within=pyo.NonNegativeReals)  # Order quantity
       M.y = pyo.Var()  # Auxiliary variable for absolute value

       # Define constraints (piecewise linear representation)
       M.greater = pyo.Constraint(expr=M.y >= (c - b) * M.x + b * d)
       M.less = pyo.Constraint(expr=M.y >= (c + h) * M.x - h * d)

       # Define objective
       M.o = pyo.Objective(expr=M.y)

       return M

The builder function receives scenario-specific data and returns a Pyomo model.

Step 4: Create Stochastic Program
---------------------------------

Use `stochastic_program()` to create a Sparow stochastic program object:

.. code-block:: python

   from sparow.sp import stochastic_program

   # Create stochastic program with first-stage variables
   sp = stochastic_program(first_stage_variables=["x"])

The `first_stage_variables` parameter specifies which variables are first-stage (here-and-now) decisions.

Step 5: Initialize Application
------------------------------

Use `initialize_application()` to set up the application data:

.. code-block:: python

   # Initialize with application data
   sp.initialize_application(app_data=app_data)

This loads the problem parameters into the stochastic program.

Step 6: Initialize Model
------------------------

Use `initialize_model()` to set up the model data and builder:

.. code-block:: python

   # Initialize with model data and builder function
   sp.initialize_model(model_data=model_data, model_builder=builder)

This completes the setup by:
- Loading scenario data
- Registering the builder function
- Creating the scenario tree
- Setting up bundles

Complete Example
----------------

Here's the complete newsvendor example showing all steps:

.. code-block:: python

   from munch import Munch
   import pyomo.environ as pyo
   from sparow.sp import stochastic_program

   # Step 1: Application data
   app_data = dict(c=1.0, b=1.5, h=0.1)

   # Step 2: Model data
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
       b = data["b"]
       c = data["c"]
       h = data["h"]
       d = data["d"]

       M = pyo.ConcreteModel(data["ID"])
       M.x = pyo.Var(within=pyo.NonNegativeReals)
       M.y = pyo.Var()
       M.greater = pyo.Constraint(expr=M.y >= (c - b) * M.x + b * d)
       M.less = pyo.Constraint(expr=M.y >= (c + h) * M.x - h * d)
       M.o = pyo.Objective(expr=M.y)
       return M

   # Step 4: Create stochastic program
   sp = stochastic_program(first_stage_variables=["x"])

   # Step 5: Initialize application
   sp.initialize_application(app_data=app_data)

   # Step 6: Initialize model
   sp.initialize_model(model_data=model_data, model_builder=builder)

   # Now the stochastic program is ready to solve
   print(f"Created stochastic program with {len(sp.scenario_data[None])} scenarios")

Solving the Problem
-------------------

Once initialized, you can solve the problem using any Sparow solver:

.. code-block:: python

   from sparow.ef import ExtensiveFormSolver

   # Create and solve with EF solver
   solver = ExtensiveFormSolver()
   results = solver.solve(sp)

   # Get the solution
   results_dict = results.to_dict()
   solution = next(iter(results_dict["solutions"].values()))

   # Extract results
   x_value = solution['variables'][0]['value']
   objective = solution['objectives'][0]['value']

   print(f"Optimal order quantity: {x_value:.2f}")
   print(f"Expected profit: {-objective:.2f}")

Key Concepts Illustrated
-------------------------

1. **Application Data vs Model Data**:
   - Application data: Constant parameters (c, b, h)
   - Model data: Scenario-specific data (demand values)

2. **Builder Function**:
   - Takes scenario data and returns a Pyomo model
   - Called once for each scenario
   - Must be pure (no side effects)

3. **Stochastic Program Setup**:
   - `stochastic_program()` creates the container
   - `initialize_application()` loads constants
   - `initialize_model()` loads scenarios and builder

4. **First-Stage Variables**:
   - Specified when creating the stochastic program
   - Must match variable names in the Pyomo model
   - Represent here-and-now decisions

Variations of the Newsvendor Problem
------------------------------------

Sparow provides different versions of the newsvendor problem:

Simple Newsvendor
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.sp.examples import simple_newsvendor

   # Creates a basic newsvendor problem
   app = simple_newsvendor()
   sp = app.sp  # Access the stochastic program

Single Scenario Newsvendor
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.sp.examples import single_scenario_newsvendor

   # Creates a newsvendor with only one scenario
   app = single_scenario_newsvendor()
   sp = app.sp

Low-Fidelity (LF) Newsvendor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.sp.examples import LF_newsvendor

   # Creates a simplified version with fewer scenarios
   app = LF_newsvendor()
   sp = app.sp

High-Fidelity (HF) Newsvendor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.sp.examples import HF_newsvendor

   # Creates a more detailed version with more scenarios
   app = HF_newsvendor()
   sp = app.sp

Random Newsvendor
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.sp.examples import MFrandom_newsvendor

   # Creates a newsvendor with randomly generated scenarios
   app = MFrandom_newsvendor(num_scenarios=50, random_seed=42)
   sp = app.sp

Understanding the Solution
--------------------------

The solution provides the optimal order quantity that balances:

* **Overordering risk**: Buying too much leads to excess inventory
* **Underordering risk**: Buying too little leads to lost sales

The expected profit is computed across all scenarios, weighted by their probabilities.

Advanced Usage
--------------

Customizing the Newsvendor Problem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can create custom variations by modifying the data:

.. code-block:: python

   # Custom application data
   custom_app_data = dict(c=1.2, b=1.8, h=0.2)

   # Custom scenarios
   custom_model_data = {
       "scenarios": [
           {"ID": 1, "d": 10, "probability": 0.1},
           {"ID": 2, "d": 50, "probability": 0.6},
           {"ID": 3, "d": 100, "probability": 0.3},
       ],
   }

   # Create custom stochastic program
   sp = stochastic_program(first_stage_variables=["x"])
   sp.initialize_application(app_data=custom_app_data)
   sp.initialize_model(model_data=custom_model_data, model_builder=builder)

Adding More Complexity
~~~~~~~~~~~~~~~~~~~~~~

For more complex problems, you can:

1. **Add more variables**: Include storage, pricing, or other decisions
2. **Add more constraints**: Capacity limits, budget constraints, etc.
3. **Use different distributions**: Modify scenario probabilities
4. **Add more stages**: Extend to multi-stage decision making

Best Practices
--------------

1. **Start Simple**: Begin with a small number of scenarios
2. **Validate Data**: Ensure scenario probabilities sum to 1
3. **Test Builder**: Verify the builder function works for individual scenarios
4. **Check First-Stage Variables**: Ensure they're correctly specified
5. **Monitor Performance**: Larger problems may need different solvers

The newsvendor problem illustrates the fundamental Sparow workflow that applies to all stochastic programming applications. Once you understand this pattern, you can apply it to more complex problems like facility location, portfolio optimization, and supply chain management.