###########
Newsvendor
###########

Newsvendor Problem Examples
============================

The newsvendor problem is a classic stochastic programming example that demonstrates inventory management under uncertain demand. It's an excellent introduction to stochastic programming concepts and Sparow's capabilities.

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

The newsvendor must balance:

* **Overordering**: Buying too much leads to excess inventory and lost profit
* **Underordering**: Buying too little leads to lost sales opportunities

Simple Newsvendor Example
-------------------------

The simplest version demonstrates basic stochastic programming formulation:

.. code-block:: python

   from sparow.sp.examples import simple_newsvendor
   from sparow.ef import ExtensiveFormSolver

   # Create the simple newsvendor application
   app = simple_newsvendor()

   # Solve using Extensive Form
   solver = ExtensiveFormSolver()
   solver.set_options(solver='highs')
   results = solver.solve(app.sp)

   # Analyze results
   results_dict = results.to_dict()
   solution = next(iter(results_dict["solutions"].values()))

   x_value = solution['variables'][0]['value']
   objective = solution['objectives'][0]['value']

   print(f"Optimal order quantity: {x_value:.2f}")
   print(f"Expected profit: {-objective:.2f}")

This example uses a small set of discrete demand scenarios to illustrate the basic formulation.

Multi-Fidelity Newsvendor
--------------------------

Sparow provides different fidelity versions of the newsvendor problem:

Low-Fidelity (LF) Newsvendor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The LF version uses a simplified representation with fewer scenarios:

.. code-block:: python

   from sparow.sp.examples import LF_newsvendor

   # Create LF newsvendor application
   app = LF_newsvendor()

   # Solve and analyze
   solver = ExtensiveFormSolver()
   results = solver.solve(app.sp)

High-Fidelity (HF) Newsvendor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The HF version uses more scenarios for greater accuracy:

.. code-block:: python

   from sparow.sp.examples import HF_newsvendor

   # Create HF newsvendor application
   app = HF_newsvendor()

   # Solve and analyze
   solver = ExtensiveFormSolver()
   results = solver.solve(app.sp)

Comparing Solvers
-----------------

The newsvendor problem is excellent for comparing different Sparow solvers:

Extensive Form (EF) Solver
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.ef import ExtensiveFormSolver

   app = simple_newsvendor()
   solver = ExtensiveFormSolver()
   solver.set_options(solver='gurobi')
   ef_results = solver.solve(app.sp)

Progressive Hedging (PH) Solver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.ph import ProgressiveHedgingSolver

   app = simple_newsvendor()
   solver = ProgressiveHedgingSolver()
   solver.set_options(solver='gurobi')
   solver.set_options(max_iterations=100)
   ph_results = solver.solve(app.sp)

Benders Decomposition Solver
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.benders import BendersSolver

   app = simple_newsvendor()
   solver = BendersSolver()
   solver.set_options(mip_solver='gurobi')
   benders_results = solver.solve(app.sp)

Comparing Results
~~~~~~~~~~~~~~~~

.. code-block:: python

   def get_objective(results):
       results_dict = results.to_dict()
       solution = next(iter(results_dict["solutions"].values()))
       return solution['objectives'][0]['value']

   ef_obj = get_objective(ef_results)
   ph_obj = get_objective(ph_results)
   benders_obj = get_objective(benders_results)

   print(f"EF objective: {ef_obj:.4f}")
   print(f"PH objective: {ph_obj:.4f}")
   print(f"Benders objective: {benders_obj:.4f}")

Confidence Intervals
--------------------

Compute confidence intervals to assess solution quality:

.. code-block:: python

   from sparow.conf_intervals import compute_confidence_intervals

   # Compute confidence intervals for EF solution
   ci_results = compute_confidence_intervals(ef_results, app.sp)

   print(f"Objective estimate: {ci_results.objective_estimate:.4f}")
   print(f"95% CI: [{ci_results.lower_bound:.4f}, {ci_results.upper_bound:.4f}]")
   print(f"Relative width: {ci_results.relative_width*100:.2f}%")

Visualizing Results
-------------------

Create visualizations to understand the newsvendor solution:

.. code-block:: python

   import matplotlib.pyplot as plt
   import numpy as np

   # Demand scenarios and probabilities
   scenarios = app.sp.scenario_tree.scenarios
   demands = [s.data['d'] for s in scenarios]
   probabilities = [s.probability for s in scenarios]

   # Plot demand distribution
   plt.figure(figsize=(10, 6))
   plt.bar(demands, probabilities, width=5)
   plt.axvline(x=x_value, color='r', linestyle='--', label=f'Optimal order: {x_value:.1f}')
   plt.xlabel('Demand')
   plt.ylabel('Probability')
   plt.title('Demand Distribution with Optimal Order Quantity')
   plt.legend()
   plt.grid(True, alpha=0.3)
   plt.show()

Expected Profit Analysis
-----------------------

Analyze how expected profit varies with order quantity:

.. code-block:: python

   def expected_profit(x, c, b, h, demand_scenarios, probabilities):
       """Calculate expected profit for a given order quantity."""
       expected_profit = 0
       for d, prob in zip(demand_scenarios, probabilities):
           # Profit = revenue - cost + salvage
           # Revenue = min(x, d) * b
           # Cost = x * c
           # Salvage = max(0, x - d) * h
           profit = min(x, d) * b - x * c + max(0, x - d) * h
           expected_profit += profit * prob
       return expected_profit

   # Test different order quantities
   test_quantities = np.linspace(10, 80, 50)
   profits = [expected_profit(x, 1.0, 1.5, 0.1, demands, probabilities) for x in test_quantities]

   # Plot expected profit curve
   plt.figure(figsize=(10, 6))
   plt.plot(test_quantities, profits, 'b-', label='Expected profit')
   plt.axvline(x=x_value, color='r', linestyle='--', label=f'Optimal: {x_value:.1f}')
   plt.xlabel('Order Quantity')
   plt.ylabel('Expected Profit')
   plt.title('Expected Profit vs Order Quantity')
   plt.legend()
   plt.grid(True, alpha=0.3)
   plt.show()

Sensitivity Analysis
-------------------

Explore how the solution changes with different parameters:

.. code-block:: python

   # Vary purchase cost
   costs = np.linspace(0.8, 1.5, 10)
   optimal_orders = []

   for cost in costs:
       # Create newsvendor with different cost
       app_data = {'c': cost, 'b': 1.5, 'h': 0.1}
       app = simple_newsvendor(app_data=app_data)

       # Solve
       solver = ExtensiveFormSolver()
       results = solver.solve(app.sp)
       solution = next(iter(results.to_dict()["solutions"].values()))

       optimal_orders.append(solution['variables'][0]['value'])

   # Plot sensitivity
   plt.figure(figsize=(10, 6))
   plt.plot(costs, optimal_orders, 'bo-')
   plt.xlabel('Purchase Cost')
   plt.ylabel('Optimal Order Quantity')
   plt.title('Sensitivity of Optimal Order to Purchase Cost')
   plt.grid(True, alpha=0.3)
   plt.show()

Advanced Applications
---------------------

Random Newsvendor
~~~~~~~~~~~~~~~~~

Use randomly generated scenarios:

.. code-block:: python

   from sparow.sp.examples import MFrandom_newsvendor

   # Create newsvendor with random scenarios
   app = MFrandom_newsvendor(num_scenarios=50, random_seed=42)

   # Solve
   solver = ExtensiveFormSolver()
   results = solver.solve(app.sp)

Multi-Stage Newsvendor
~~~~~~~~~~~~~~~~~~~~~~

Extend to multiple decision stages:

.. code-block:: python

   # This would involve creating a multi-stage scenario tree
   # and formulating the problem with decisions at each stage

Key Insights
------------

1. **Risk vs Reward**: The optimal order quantity balances the risk of overordering against the reward of meeting demand
2. **Demand Distribution**: The shape of the demand distribution significantly affects the optimal solution
3. **Cost Structure**: The ratio of costs (c, b, h) determines the optimal order quantity
4. **Solver Choice**: Different solvers may be more appropriate depending on problem size and structure
5. **Confidence Intervals**: Essential for understanding solution quality and uncertainty

The newsvendor problem illustrates fundamental stochastic programming concepts that apply to many real-world applications in inventory management, supply chain optimization, and resource allocation.