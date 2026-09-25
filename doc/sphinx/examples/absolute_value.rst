###############
Absolute Value
###############

Absolute Value Problem Examples
===============================

The absolute value problem is a fundamental stochastic programming example that demonstrates how to handle nonlinear objectives and constraints. It's particularly useful for illustrating Benders decomposition and other advanced solver techniques.

Problem Description
------------------

The absolute value problem involves:

* **Objective**: Minimize the expected absolute deviation from a target
* **Decision Variable**: A single continuous variable x
* **Uncertainty**: Random parameters that affect the optimal solution
* **Formulation**: Often involves piecewise linear representations of absolute values

This problem is useful for demonstrating:

* Handling nonlinear functions in stochastic programming
* Benders decomposition for problems with complicating variables
* Different approaches to modeling absolute values

Simple Absolute Value Problem
-----------------------------

.. code-block:: python

   from sparow.sp.examples import simple_absolute_value
   from sparow.ef import ExtensiveFormSolver

   # Create the absolute value application
   app = simple_absolute_value()

   # Solve using Extensive Form
   solver = ExtensiveFormSolver()
   solver.set_options(solver='highs')
   results = solver.solve(app.sp)

   # Analyze results
   results_dict = results.to_dict()
   solution = next(iter(results_dict["solutions"].values()))

   x_value = solution['variables'][0]['value']
   objective = solution['objectives'][0]['value']

   print(f"Optimal x: {x_value:.4f}")
   print(f"Objective value: {objective:.4f}")

Adjustable Absolute Value Problem
---------------------------------

The adjustable version demonstrates more complex decision-making:

.. code-block:: python

   from sparow.sp.examples import adjustable_absolute_value

   # Create adjustable absolute value application
   app = adjustable_absolute_value()

   # Solve and analyze
   solver = ExtensiveFormSolver()
   results = solver.solve(app.sp)

Benders Decomposition Example
-----------------------------

The absolute value problem is excellent for demonstrating Benders decomposition:

.. code-block:: python

   from sparow.benders import BendersSolver

   # Create the application
   app = simple_absolute_value()

   # Solve with Benders decomposition
   solver = BendersSolver()
   solver.set_options(mip_solver='gurobi')
   solver.set_options(max_iterations=50)
   solver.set_options(verbose=True)
   results = solver.solve(app.sp)

   # Analyze Benders performance
   print(f"Number of iterations: {results.num_iterations}")
   print(f"Number of cuts added: {results.num_cuts}")

   # Get solution
   solution = next(iter(results.to_dict()["solutions"].values()))
   print(f"Benders solution: x = {solution['variables'][0]['value']:.4f}")

Comparing Solvers
-----------------

.. code-block:: python

   from sparow.ph import ProgressiveHedgingSolver

   # Compare EF, PH, and Benders solvers
   solvers = {
       'EF': ExtensiveFormSolver(),
       'PH': ProgressiveHedgingSolver(),
       'Benders': BendersSolver()
   }

   results_dict = {}
   for name, solver in solvers.items():
       if name == 'EF' or name == 'Benders':
           solver.set_options(solver='gurobi')
       if name == 'PH':
           solver.set_options(solver='gurobi')
           solver.set_options(max_iterations=100)
       if name == 'Benders':
           solver.set_options(max_iterations=50)

       results_dict[name] = solver.solve(app.sp)

   # Compare results
   for name, results in results_dict.items():
       solution = next(iter(results.to_dict()["solutions"].values()))
       obj_value = solution['objectives'][0]['value']
       x_value = solution['variables'][0]['value']
       print(f"{name}: x={x_value:.4f}, objective={obj_value:.4f}")

Analyzing Absolute Value Solutions
----------------------------------

.. code-block:: python

   import numpy as np
   import matplotlib.pyplot as plt

   def analyze_absolute_value_solution(app, results):
       """Analyze the absolute value problem solution."""
       results_dict = results.to_dict()
       solution = next(iter(results_dict["solutions"].values()))
       x_opt = solution['variables'][0]['value']

       # Get scenario data
       scenarios = app.sp.scenario_tree.scenarios
       scenario_data = []
       for scenario in scenarios:
           data = scenario.data
           scenario_data.append({
               'id': scenario.name,
               'probability': scenario.probability,
               'data': data
           })

       return {'x_opt': x_opt, 'scenarios': scenario_data}

   # Analyze solution
   analysis = analyze_absolute_value_solution(app, results)
   print(f"Optimal x: {analysis['x_opt']:.4f}")

Visualizing the Objective Function
----------------------------------

.. code-block:: python

   def plot_objective_function(app, x_opt):
       """Plot the objective function for different x values."""
       scenarios = app.sp.scenario_tree.scenarios

       # Create a range of x values
       x_values = np.linspace(0, 20, 100)
       objective_values = []

       for x in x_values:
           obj_val = 0
           for scenario in scenarios:
               # Calculate objective for this scenario
               # This depends on the specific problem formulation
               # Example: absolute value objective
               data = scenario.data
               # Assuming the objective is E[|x - d|] where d is scenario data
               d = data.get('d', 10)  # Example parameter
               scenario_obj = abs(x - d)
               obj_val += scenario_obj * scenario.probability
           objective_values.append(obj_val)

       # Plot
       plt.figure(figsize=(10, 6))
       plt.plot(x_values, objective_values, 'b-', label='Expected objective')
       plt.axvline(x=x_opt, color='r', linestyle='--', label=f'Optimal x: {x_opt:.2f}')
       plt.xlabel('x')
       plt.ylabel('Expected Objective Value')
       plt.title('Objective Function for Absolute Value Problem')
       plt.legend()
       plt.grid(True, alpha=0.3)
       plt.show()

   # Plot objective function
   plot_objective_function(app, analysis['x_opt'])

Confidence Intervals
--------------------

.. code-block:: python

   from sparow.conf_intervals import compute_confidence_intervals

   # Compute confidence intervals
   ci_results = compute_confidence_intervals(results, app.sp)

   print(f"Objective estimate: {ci_results.objective_estimate:.4f}")
   print(f"95% CI: [{ci_results.lower_bound:.4f}, {ci_results.upper_bound:.4f}]")
   print(f"Relative width: {ci_results.relative_width*100:.2f}%")

Benders Decomposition Analysis
------------------------------

.. code-block:: python

   def analyze_benders_performance(app):
       """Analyze Benders decomposition performance."""
       solver = BendersSolver()
       solver.set_options(mip_solver='gurobi')
       solver.set_options(max_iterations=100)
       solver.set_options(verbose=False)

       # Track progress
       results = solver.solve(app.sp)

       # Analyze cuts
       print(f"Benders Analysis:")
       print(f"  Iterations: {results.num_iterations}")
       print(f"  Cuts added: {results.num_cuts}")
       print(f"  Final objective: {results.objective:.4f}")

       return results

   # Analyze Benders performance
   benders_results = analyze_benders_performance(app)

Advanced Applications
---------------------

Piecewise Linear Approximation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The absolute value problem often uses piecewise linear approximations:

.. code-block:: python

   # Example of piecewise linear formulation
   # This would be in the model builder function
   def piecewise_absolute_value_builder(data, args):
       import pyomo.environ as pyo

       M = pyo.ConcreteModel(data["ID"])

       # Decision variable
       M.x = pyo.Var()

       # Piecewise linear representation of |x - d|
       M.y = pyo.Var()  # Auxiliary variable for absolute value

       # Two linear constraints representing |x - d| = y
       M.abs1 = pyo.Constraint(expr=M.y >= M.x - data['d'])
       M.abs2 = pyo.Constraint(expr=M.y >= data['d'] - M.x)

       # Objective
       M.o = pyo.Objective(expr=M.y)

       return M

Multi-Stage Absolute Value Problem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extend to multiple stages:

.. code-block:: python

   # This would involve:
   # 1. Creating a multi-stage scenario tree
   # 2. Adding intermediate decision variables
   # 3. Including more complex uncertainty patterns

Key Insights
------------

1. **Nonlinear Handling**: Demonstrates how to handle nonlinear functions in stochastic programming
2. **Benders Suitability**: Shows why Benders decomposition works well for certain problem structures
3. **Piecewise Linear**: Illustrates the use of piecewise linear approximations
4. **Solver Comparison**: Provides a basis for comparing different solver approaches
5. **Confidence Intervals**: Shows how to assess solution quality for nonlinear problems

The absolute value problem is a fundamental building block for more complex stochastic programming applications involving nonlinearities and is particularly valuable for understanding advanced decomposition techniques like Benders.

Real-World Applications
-----------------------

The absolute value problem and its variants apply to:

* **Inventory Management**: Minimizing deviations from target inventory levels
* **Production Planning**: Minimizing deviations from production targets
* **Portfolio Optimization**: Minimizing tracking error relative to a benchmark
* **Resource Allocation**: Minimizing imbalances in resource distribution
* **Quality Control**: Minimizing deviations from quality targets
* **Scheduling**: Minimizing deviations from desired schedules