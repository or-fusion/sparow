########
Farmers
########

Farmers Problem Examples
========================

The farmers problem is a classic stochastic programming example that demonstrates multi-stage decision-making under uncertainty. It involves farmers making planting decisions with uncertain crop yields and prices.

Problem Description
------------------

The farmers problem involves:

* **Decisions**:
  * First-stage: How much land to allocate to different crops
  * Second-stage: How much to sell or store after yields are realized
* **Uncertainty**:
  * Crop yields (how much each crop produces)
  * Market prices (what price crops will fetch)
* **Constraints**:
  * Land availability
  * Water requirements
  * Labor constraints
  * Storage capacity

This problem demonstrates multi-stage stochastic programming with recourse decisions.

Basic Farmers Problem
--------------------

.. code-block:: python

   from sparow.sp.examples import MFfarmers
   from sparow.ef import ExtensiveFormSolver

   # Create the farmers application
   app = MFfarmers()

   # Solve using Extensive Form
   solver = ExtensiveFormSolver()
   solver.set_options(solver='gurobi')
   results = solver.solve(app.sp)

   # Analyze results
   results_dict = results.to_dict()
   solution = next(iter(results_dict["solutions"].values()))

   # Extract planting decisions
   variables = solution['variables']
   planting_vars = [v for v in variables if 'x[' in v['name']]

   print("Planting Decisions:")
   for var in planting_vars:
       crop = var['name'].split('[')[1].split(']')[0]
       acres = var['value']
       print(f"  {crop}: {acres:.1f} acres")

Multi-Fidelity Farmers Problem
------------------------------

Sparow provides different versions of the farmers problem:

Mean-Field (MF) Farmers
~~~~~~~~~~~~~~~~~~~~~~~

The MF version uses aggregated uncertainty representation:

.. code-block:: python

   from sparow.sp.examples import MFfarmers

   # Create MF farmers application
   app = MFfarmers()

   # Solve and analyze
   solver = ExtensiveFormSolver()
   results = solver.solve(app.sp)

Mean-Field Random (MFrandom) Farmers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The MFrandom version uses randomly generated scenarios:

.. code-block:: python

   from sparow.sp.examples import MFrandom_farmers

   # Create farmers application with random scenarios
   app = MFrandom_farmers(num_scenarios=30, random_seed=42)

   # Solve
   solver = ExtensiveFormSolver()
   results = solver.solve(app.sp)

Comparing Solvers
-----------------

.. code-block:: python

   from sparow.ph import ProgressiveHedgingSolver
   from sparow.benders import BendersSolver

   # Compare different solvers
   solvers = {
       'EF': ExtensiveFormSolver(),
       'PH': ProgressiveHedgingSolver(),
       'Benders': BendersSolver()
   }

   results_dict = {}
   for name, solver in solvers.items():
       solver.set_options(solver='gurobi')
       if name == 'PH':
           solver.set_options(max_iterations=200)
       results_dict[name] = solver.solve(app.sp)

   # Compare objectives
   for name, results in results_dict.items():
       solution = next(iter(results.to_dict()["solutions"].values()))
       obj_value = solution['objectives'][0]['value']
       print(f"{name} objective: {obj_value:.2f}")

Analyzing Farmers Problem Solutions
------------------------------------

.. code-block:: python

   def analyze_farmers_solution(results, app):
       """Analyze and visualize farmers problem solution."""
       results_dict = results.to_dict()
       solution = next(iter(results_dict["solutions"].values()))
       variables = solution['variables']

       # Extract planting decisions
       planting = {}
       for var in variables:
           if 'x[' in var['name']:
               crop = var['name'].split('[')[1].split(']')[0]
               planting[crop] = var['value']

       # Extract second-stage decisions
       sales = {}
       storage = {}
       for var in variables:
           if 'y[' in var['name']:
               parts = var['name'].split('[')[1].split(']')[0].split(',')
               crop = parts[0].strip()
               scenario = parts[1].strip()
               if 'sales' not in sales:
                   sales[crop] = []
               sales[crop].append(var['value'])
           elif 'z[' in var['name']:
               parts = var['name'].split('[')[1].split(']')[0].split(',')
               crop = parts[0].strip()
               scenario = parts[1].strip()
               if 'storage' not in storage:
                   storage[crop] = []
               storage[crop].append(var['value'])

       return {'planting': planting, 'sales': sales, 'storage': storage}

   # Analyze solution
   analysis = analyze_farmers_solution(results, app)
   print("Planting decisions:", analysis['planting'])

Visualizing Crop Allocation
----------------------------

.. code-block:: python

   import matplotlib.pyplot as plt

   def plot_crop_allocation(analysis):
       """Plot crop allocation decisions."""
       crops = list(analysis['planting'].keys())
       acres = list(analysis['planting'].values())

       plt.figure(figsize=(10, 6))
       plt.bar(crops, acres, color='green')
       plt.xlabel('Crop')
       plt.ylabel('Acres Planted')
       plt.title('Optimal Crop Allocation')
       plt.grid(True, alpha=0.3)
       plt.show()

   # Plot crop allocation
   plot_crop_allocation(analysis)

Scenario Analysis
----------------

.. code-block:: python

   def analyze_scenarios(app):
       """Analyze different yield scenarios."""
       scenarios = app.sp.scenario_tree.scenarios

       print("Demand Scenarios:")
       for scenario in scenarios:
           data = scenario.data
           print(f"  Scenario {scenario.name} (prob={scenario.probability}):")
           for key, value in data.items():
               print(f"    {key}: {value}")

   # Analyze scenarios
   analyze_scenarios(app)

Profit Analysis
--------------

.. code-block:: python

   def analyze_profit(results, app):
       """Analyze profit components."""
       results_dict = results.to_dict()
       solution = next(iter(results_dict["solutions"].values()))
       objective = solution['objectives'][0]['value']

       # Extract variables for profit calculation
       variables = solution['variables']
       planting_costs = {}
       expected_revenue = {}

       for var in variables:
           if 'x[' in var['name']:
               crop = var['name'].split('[')[1].split(']')[0]
               # Assuming cost data is available in app
               cost_per_acre = 100  # Example value
               planting_costs[crop] = var['value'] * cost_per_acre

       print(f"Total profit: {objective:.2f}")
       print(f"Planting costs: {sum(planting_costs.values()):.2f}")

   # Analyze profit
   analyze_profit(results, app)

Sensitivity Analysis
-------------------

.. code-block:: python

   def sensitivity_analysis(app):
       """Perform sensitivity analysis on crop prices."""
       base_data = app.app_data.copy()
       sensitivities = []

       # Vary crop prices
       price_multipliers = [0.8, 0.9, 1.0, 1.1, 1.2]

       for multiplier in price_multipliers:
           new_data = base_data.copy()
           # Modify price data (assuming it's in the app data)
           # This is example code - actual implementation depends on data structure
           new_data['prices'] = [p * multiplier for p in base_data.get('prices', [1.0])]

           # Create new application
           new_app = MFfarmers(app_data=new_data)

           # Solve
           solver = ExtensiveFormSolver()
           results = solver.solve(new_app.sp)
           solution = next(iter(results.to_dict()["solutions"].values()))
           obj_value = solution['objectives'][0]['value']

           sensitivities.append({
               'price_multiplier': multiplier,
               'profit': obj_value
           })

       return sensitivities

   # Perform sensitivity analysis
   sensitivities = sensitivity_analysis(app)
   for s in sensitivities:
       print(f"Price multiplier {s['price_multiplier']}: profit={s['profit']:.2f}")

Confidence Intervals
--------------------

.. code-block:: python

   from sparow.conf_intervals import compute_confidence_intervals

   # Compute confidence intervals
   ci_results = compute_confidence_intervals(results, app.sp)

   print(f"Profit estimate: {ci_results.objective_estimate:.2f}")
   print(f"95% CI: [{ci_results.lower_bound:.2f}, {ci_results.upper_bound:.2f}]")
   print(f"Relative width: {ci_results.relative_width*100:.2f}%")

Advanced Applications
---------------------

Multi-Stage Decision Making
~~~~~~~~~~~~~~~~~~~~~~~~~~

The farmers problem demonstrates multi-stage decisions:

1. **First-stage**: Planting decisions (before knowing yields)
2. **Second-stage**: Sales and storage decisions (after yields are known)

.. code-block:: python

   # To create a more complex multi-stage version:
   # 1. Define multiple stages in the scenario tree
   # 2. Add intermediate decisions (e.g., irrigation, pest control)
   # 3. Include more uncertainty sources (weather, pests, etc.)

Uncertainty Quantification
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.conf_intervals import variable_ci

   # Compute confidence intervals for planting decisions
   for crop in analysis['planting'].keys():
       var_name = f'x[{crop}]'
       try:
           ci = variable_ci(results, variable_name=var_name)
           print(f"{crop} planting CI: [{ci.lower:.2f}, {ci.upper:.2f}] acres")
       except:
           print(f"Could not compute CI for {crop}")

Key Insights
------------

1. **Risk Management**: Farmers must balance potential profits against risks of poor yields
2. **Diversification**: Optimal solutions often involve planting multiple crops
3. **Recourse Value**: The ability to adjust sales/storage after yields are known is valuable
4. **Uncertainty Impact**: Yield uncertainty significantly affects optimal planting decisions
5. **Policy Analysis**: Can be used to evaluate agricultural policies and subsidies

The farmers problem illustrates how stochastic programming can model complex agricultural decision-making with multiple stages, uncertain outcomes, and recourse actions.

Real-World Applications
-----------------------

The farmers problem applies to:

* **Agricultural Planning**: Crop selection and land allocation
* **Supply Chain Management**: Procurement under uncertain supply
* **Energy Portfolio Management**: Investment in different energy sources
* **Financial Portfolio Optimization**: Asset allocation under market uncertainty
* **Production Planning**: Resource allocation with uncertain demand
* **Natural Resource Management**: Harvest planning with uncertain yields