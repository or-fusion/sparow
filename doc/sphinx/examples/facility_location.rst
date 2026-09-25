####################
Facility Location
####################

Facility Location Problem Examples
===================================

The facility location problem is a classic stochastic programming application that demonstrates strategic decision-making under uncertainty. It involves deciding where to locate facilities (e.g., warehouses, factories) to serve customers with uncertain demand.

Problem Description
------------------

The facility location problem involves:

* **Decisions**:
  * Where to locate facilities (binary decisions)
  * How much to produce/supply from each facility (continuous decisions)
* **Uncertainty**: Customer demand follows probability distributions
* **Costs**:
  * Fixed costs for opening facilities
  * Variable costs for production and transportation
* **Constraints**:
  * Facility capacity limits
  * Demand satisfaction requirements

This is a more complex problem than the newsvendor, demonstrating multi-stage decision-making and binary variables.

Basic Facility Location Example
--------------------------------

.. code-block:: python

   from sparow.sp.examples import AMPL_facilityloc
   from sparow.ef import ExtensiveFormSolver

   # Create the facility location application
   app = AMPL_facilityloc()

   # Solve using Extensive Form
   solver = ExtensiveFormSolver()
   solver.set_options(solver='gurobi')  # Gurobi handles binary variables well
   results = solver.solve(app.sp)

   # Analyze results
   results_dict = results.to_dict()
   solution = next(iter(results_dict["solutions"].values()))

   # Extract facility opening decisions
   variables = solution['variables']
   facility_vars = [v for v in variables if 'x[' in v['name']]  # Facility location variables

   print("Facility Location Solution:")
   for var in facility_vars:
       facility_id = var['name'].split('[')[1].split(']')[0]
       is_open = var['value']
       print(f"Facility {facility_id}: {'OPEN' if is_open > 0.5 else 'CLOSED'}")

Low-Fidelity (LF) Facility Location
------------------------------------

The LF version uses continuous variables and aggregated demand scenarios:

.. code-block:: python

   from sparow.sp.examples.facilityloc import facilityloc

   # Create LF facility location application
   app = facilityloc()

   # Solve and analyze
   solver = ExtensiveFormSolver()
   results = solver.solve(app.sp)

High-Fidelity (HF) Facility Location
-------------------------------------

The HF version uses binary variables for facility location and more detailed demand scenarios:

.. code-block:: python

   from sparow.sp.examples import AMPL_facilityloc

   # Create HF facility location application
   app = AMPL_facilityloc()

   # Solve with different solvers
   solvers = {
       'EF': ExtensiveFormSolver(),
       'PH': ProgressiveHedgingSolver(),
       'Benders': BendersSolver()
   }

   results_dict = {}
   for name, solver in solvers.items():
       solver.set_options(solver='gurobi')
       results_dict[name] = solver.solve(app.sp)

Comparing Solver Performance
----------------------------

.. code-block:: python

   import time

   def solve_and_time(solver, app, name):
       start_time = time.time()
       results = solver.solve(app.sp)
       elapsed = time.time() - start_time

       # Get objective value
       solution = next(iter(results.to_dict()["solutions"].values()))
       obj_value = solution['objectives'][0]['value']

       return {'time': elapsed, 'objective': obj_value}

   # Compare solver performance
   performance = {}
   for name, solver in solvers.items():
       perf = solve_and_time(solver, app, name)
       performance[name] = perf
       print(f"{name}: Time={perf['time']:.2f}s, Objective={perf['objective']:.2f}")

Analyzing Facility Location Solutions
-------------------------------------

.. code-block:: python

   def analyze_facility_solution(results, app):
       """Analyze and visualize facility location solution."""
       results_dict = results.to_dict()
       solution = next(iter(results_dict["solutions"].values()))
       variables = solution['variables']

       # Extract facility decisions
       facilities = {}
       for var in variables:
           if 'x[' in var['name']:  # Facility location variable
               facility_id = int(var['name'].split('[')[1].split(']')[0])
               facilities[facility_id] = var['value']

       # Extract customer assignments
       assignments = {}
       for var in variables:
           if 'z[' in var['name']:  # Assignment variable
               parts = var['name'].split('[')[1].split(']')[0].split(',')
               facility_id = int(parts[0].strip())
               customer_id = int(parts[1].strip())
               assignments[(facility_id, customer_id)] = var['value']

       return {'facilities': facilities, 'assignments': assignments}

   # Analyze solution
   analysis = analyze_facility_solution(results, app)
   print("Open facilities:", [fid for fid, val in analysis['facilities'].items() if val > 0.5])

Visualizing Facility Networks
-----------------------------

.. code-block:: python

   import networkx as nx
   import matplotlib.pyplot as plt

   def plot_facility_network(analysis, app):
       """Plot the facility-customer network."""
       G = nx.DiGraph()

       # Add facilities (red if open, blue if closed)
       for fid, is_open in analysis['facilities'].items():
           color = 'red' if is_open > 0.5 else 'blue'
           G.add_node(f'F{fid}', color=color, type='facility')

       # Add customers
       num_customers = len(app.sp.scenario_tree.scenarios[0].data['d'])
       for cid in range(num_customers):
           G.add_node(f'C{cid}', color='green', type='customer')

       # Add assignments
       for (fid, cid), amount in analysis['assignments'].items():
           if amount > 0.01:  # Significant assignment
               G.add_edge(f'F{fid}', f'C{cid}', weight=amount)

       # Draw the network
       pos = nx.spring_layout(G, seed=42)
       colors = [G.nodes[n]['color'] for n in G.nodes()]

       plt.figure(figsize=(12, 8))
       nx.draw(G, pos, node_color=colors, with_labels=True, node_size=1000)
       edge_labels = nx.get_edge_attributes(G, 'weight')
       nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
       plt.title('Facility-Customer Network')
       plt.show()

   # Plot the network
   plot_facility_network(analysis, app)

Demand Scenario Analysis
------------------------

.. code-block:: python

   def analyze_demand_scenarios(app):
       """Analyze demand scenarios in the facility location problem."""
       scenarios = app.sp.scenario_tree.scenarios

       # Extract demand data
       demands = []
       for scenario in scenarios:
           demand_data = scenario.data['d']
           demands.append(demand_data)
           print(f"Scenario {scenario.name}: Demand={demand_data}, Probability={scenario.probability}")

       return demands

   # Analyze scenarios
   demands = analyze_demand_scenarios(app)

Cost Analysis
------------

.. code-block:: python

   def analyze_costs(results, app):
       """Analyze cost components of the facility location solution."""
       results_dict = results.to_dict()
       solution = next(iter(results_dict["solutions"].values()))
       variables = solution['variables']

       # Extract costs
       fixed_costs = app.app_data['f']
       variable_costs = app.app_data['c']

       # Calculate total costs
       total_fixed_cost = 0
       total_variable_cost = 0

       for var in variables:
           if 'x[' in var['name']:  # Facility location
               facility_id = int(var['name'].split('[')[1].split(']')[0])
               if var['value'] > 0.5:  # Facility is open
                   total_fixed_cost += fixed_costs[facility_id]
           elif 'z[' in var['name']:  # Assignment
               parts = var['name'].split('[')[1].split(']')[0].split(',')
               facility_id = int(parts[0].strip())
               customer_id = int(parts[1].strip())
               amount = var['value']
               total_variable_cost += amount * variable_costs[facility_id][customer_id]

       total_cost = total_fixed_cost + total_variable_cost
       objective = solution['objectives'][0]['value']

       print(f"Cost Analysis:")
       print(f"  Fixed costs: {total_fixed_cost:.2f}")
       print(f"  Variable costs: {total_variable_cost:.2f}")
       print(f"  Total cost: {total_cost:.2f}")
       print(f"  Objective value: {objective:.2f}")

       return {'fixed': total_fixed_cost, 'variable': total_variable_cost}

   # Analyze costs
   costs = analyze_costs(results, app)

Sensitivity Analysis
-------------------

.. code-block:: python

   def sensitivity_analysis(app):
       """Perform sensitivity analysis on facility costs."""
       base_fixed_costs = app.app_data['f']
       sensitivities = []

       # Vary fixed costs
       for multiplier in [0.8, 0.9, 1.0, 1.1, 1.2]:
           new_app_data = app.app_data.copy()
           new_app_data['f'] = [cost * multiplier for cost in base_fixed_costs]

           # Create new application
           new_app = facilityloc(app_data=new_app_data)

           # Solve
           solver = ExtensiveFormSolver()
           results = solver.solve(new_app.sp)
           solution = next(iter(results.to_dict()["solutions"].values()))
           obj_value = solution['objectives'][0]['value']

           # Count open facilities
           open_facilities = sum(1 for v in solution['variables']
                               if 'x[' in v['name'] and v['value'] > 0.5)

           sensitivities.append({
               'cost_multiplier': multiplier,
               'objective': obj_value,
               'open_facilities': open_facilities
           })

       return sensitivities

   # Perform sensitivity analysis
   sensitivities = sensitivity_analysis(app)
   for s in sensitivities:
       print(f"Cost multiplier {s['cost_multiplier']}: {s['open_facilities']} facilities, objective={s['objective']:.2f}")

Confidence Intervals for Facility Location
-------------------------------------------

.. code-block:: python

   from sparow.conf_intervals import compute_confidence_intervals

   # Compute confidence intervals
   ci_results = compute_confidence_intervals(results, app.sp)

   print(f"Objective estimate: {ci_results.objective_estimate:.2f}")
   print(f"95% CI: [{ci_results.lower_bound:.2f}, {ci_results.upper_bound:.2f}]")
   print(f"Relative width: {ci_results.relative_width*100:.2f}%")

Advanced Applications
---------------------

Multi-Stage Facility Location
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extend to multiple decision stages:

.. code-block:: python

   # This would involve:
   # 1. Creating a multi-stage scenario tree
   # 2. First-stage: Initial facility location decisions
   # 3. Second-stage: Capacity expansion decisions
   # 4. Third-stage: Operational decisions

Uncertainty Quantification
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.conf_intervals import objective_ci, variable_ci

   # Compute confidence intervals for facility decisions
   for fid in range(len(app.app_data['f'])):
       var_name = f'x[{fid}]'
       try:
           ci = variable_ci(results, variable_name=var_name)
           print(f"Facility {fid} decision CI: [{ci.lower:.2f}, {ci.upper:.2f}]")
       except:
           print(f"Could not compute CI for facility {fid}")

Key Insights
------------

1. **Trade-offs**: Facility location involves balancing fixed costs (opening facilities) with variable costs (transportation)
2. **Uncertainty Impact**: Demand uncertainty significantly affects optimal facility locations
3. **Scalability**: Different solvers handle the problem's complexity differently
4. **Visualization**: Network visualizations help understand facility-customer relationships
5. **Sensitivity**: Small changes in costs can lead to different optimal facility configurations

The facility location problem demonstrates how stochastic programming can handle complex, real-world strategic decisions with both binary choices (where to locate) and continuous decisions (how much to supply) under uncertainty.

Real-World Applications
-----------------------

The facility location problem applies to:

* **Supply Chain Design**: Warehouse and distribution center location
* **Healthcare**: Hospital and clinic location
* **Retail**: Store location planning
* **Manufacturing**: Factory location
* **Emergency Services**: Fire station and ambulance location
* **Telecommunications**: Cell tower placement
* **Energy**: Power plant and charging station location