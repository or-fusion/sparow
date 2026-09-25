###############
Solution Pools
###############

Solution pools are a key feature in Sparow for managing and organizing optimization solutions. They provide a flexible framework for storing, comparing, and retrieving solutions according to different policies. This is particularly useful when generating multiple alternative solutions or when working with multi-objective optimization problems.

*************************
What are Solution Pools?
*************************

A solution pool is a container that stores optimization solutions and manages them according to a specific policy. Solution pools help you:

- **Store multiple solutions**: Keep track of various solutions from different optimization runs
- **Apply management policies**: Automatically filter solutions based on criteria like quality, uniqueness, or Pareto optimality
- **Compare solutions**: Evaluate solutions based on objectives and constraints
- **Retrieve solutions**: Access solutions efficiently for further analysis or use

Sparow's solution pool implementation is built on top of the `or_topas` library, which provides the core functionality. Sparow extends this with its own solution and pool manager classes.

********************
Key Concepts
********************

Solution
========

A `Solution` object represents an optimization solution and contains:

- **Variables**: The values of decision variables in the solution
- **Objectives**: The objective function value(s)
- **Metadata**: Additional information about the solution (e.g., suffix data)

In Sparow, solutions are created using the `SparowSolution` class, which extends the base `Solution` class from `or_topas`.

Solution Pool
=============

A solution pool is a container that holds multiple solutions and manages them according to a policy. Different pool types implement different management strategies.

Pool Manager
============

The `PoolManager` class manages multiple solution pools. It allows you to:

- Create and manage multiple pools with different policies
- Switch between active pools
- Query information about all pools

**********************
Solution Pool Policies
**********************

Sparow supports several pool policies that determine how solutions are managed:

Keep All
========

The `keep_all` policy stores every solution added to the pool without any filtering.

**Use Case**: When you want to preserve all solutions for later analysis or comparison.

.. code-block:: python

   from sparow import solnpool

   # Create a pool that keeps all solutions
   pool_manager = solnpool.SparowPoolManager()
   pool_manager.add_pool(name="all_solutions", policy=solnpool.PoolPolicy.keep_all)

Keep Best
=========

The `keep_best` policy keeps solutions that are within a specified tolerance of the best objective value. This policy is useful when you want to maintain a set of high-quality solutions.

**Parameters**:
- `max_pool_size`: Maximum number of solutions to keep (optional)
- `objective_index`: Index of the objective to compare (default: 0)
- `abs_tolerance`: Absolute tolerance from best value
- `rel_tolerance`: Relative tolerance from best value
- `sense_is_min`: Whether the problem is minimization (True) or maximization (False)

.. code-block:: python

   # Create a pool that keeps the best solutions within 5% of the optimum
   pool_manager.add_pool(
       name="best_solutions",
       policy=solnpool.PoolPolicy.keep_best,
       max_pool_size=10,
       rel_tolerance=0.05,
       sense_is_min=True
   )

Keep Latest
===========

The `keep_latest` policy keeps only the most recently added solutions, up to a specified maximum size.

**Use Case**: When you're interested only in recent solutions and want to limit memory usage.

.. code-block:: python

   # Create a pool that keeps the latest 5 solutions
   pool_manager.add_pool(
       name="recent_solutions",
       policy=solnpool.PoolPolicy.keep_latest,
       max_pool_size=5
   )

Keep Latest Unique
==================

The `keep_latest_unique` policy keeps the most recent unique solutions. Solutions are considered duplicates if they have identical variable values.

**Parameters**:
- `max_pool_size`: Maximum number of solutions to keep
- `solution_tolerance`: Optional tolerance for considering solutions similar (using norm-based comparison)
- `norm_ord`: Norm order for tolerance comparison (1, 2, or infinity)

.. code-block:: python

   # Create a pool that keeps unique solutions
   pool_manager.add_pool(
       name="unique_solutions",
       policy=solnpool.PoolPolicy.keep_latest_unique,
       max_pool_size=20,
       solution_tolerance=1e-6
   )

Keep Pareto
===========

The `keep_pareto` policy maintains an approximation of the Pareto frontier for multi-objective optimization problems. It keeps solutions that are non-dominated.

**Parameters**:
- `sense_is_min`: Whether objectives are to be minimized (True) or maximized (False)
- `objective_tolerance`: Tolerance for comparing objective values
- `solution_tolerance`: Tolerance for considering solutions similar
- `report_newly_inferior_solns`: Whether to report solutions that become dominated

.. code-block:: python

   # Create a pool for multi-objective optimization
   pool_manager.add_pool(
       name="pareto_frontier",
       policy=solnpool.PoolPolicy.keep_pareto,
       sense_is_min=True,
       objective_tolerance=1e-6
   )

****************************
Using Solution Pools in Sparow
****************************

Basic Usage
===========

Here's how to use solution pools in a typical Sparow workflow:

.. code-block:: python

   from sparow import solnpool

   # 1. Create a pool manager
   solutions = solnpool.SparowPoolManager()

   # 2. Add a solution pool with a specific policy
   solutions.add_pool(
       name="my_pool",
       policy=solnpool.PoolPolicy.keep_all
   )

   # 3. Create variables for a solution
   variables = [
       solnpool.create_variable(name="x1", value=10.0),
       solnpool.create_variable(name="x2", value=5.0),
   ]

   # 4. Create objectives for a solution
   objectives = [
       solnpool.create_objective(value=150.0)
   ]

   # 5. Add the solution to the pool
   solution_id = solutions.add(variables=variables, objectives=objectives)

   # 6. Access the solution
   solution = solutions[solution_id]
   print(f"Solution ID: {solution_id}")
   print(f"Objective value: {solution.objective().value}")

Working with Multiple Pools
=============================

You can manage multiple pools with different policies:

.. code-block:: python

   # Create multiple pools with different policies
   solutions.add_pool(name="all", policy=solnpool.PoolPolicy.keep_all)
   solutions.add_pool(name="best", policy=solnpool.PoolPolicy.keep_best, rel_tolerance=0.1)
   solutions.add_pool(name="recent", policy=solnpool.PoolPolicy.keep_latest, max_pool_size=3)

   # Add solutions to the active pool (default is the most recently added)
   for i in range(10):
       variables = [solnpool.create_variable(name="x", value=i)]
       objectives = [solnpool.create_objective(value=i*i)]
       solutions.add(variables=variables, objectives=objectives)

   # Switch to a different pool
   solutions.activate("best")

   # Add more solutions to the best pool
   solutions.add(variables=variables, objectives=objectives)

Querying Pool Information
==========================

You can retrieve information about your pools:

.. code-block:: python

   # Get all pool names
   pool_names = solutions.get_pool_names()
   print(f"Pool names: {pool_names}")

   # Get pool policies
   policies = solutions.get_pool_policies()
   print(f"Pool policies: {policies}")

   # Get pool sizes
   sizes = solutions.get_pool_sizes()
   print(f"Pool sizes: {sizes}")

   # Get full pool information as dictionaries
   pool_dicts = solutions.get_pool_dicts()
   for name, pool_dict in pool_dicts.items():
       print(f"\nPool '{name}':")
       print(f"  Policy: {pool_dict['metadata']['policy']}")
       print(f"  Number of solutions: {len(pool_dict['solutions'])}")

Complete Example
================

Here's a complete example using solution pools with a Sparow application:

.. code-block:: python

   from sparow.sp.examples import simple_newsvendor
   from sparow import solnpool

   # Create a newsvendor application
   app = simple_newsvendor()

   # Create a pool manager
   solutions = solnpool.SparowPoolManager()

   # Add pools with different policies
   solutions.add_pool(name="all_solutions", policy=solnpool.PoolPolicy.keep_all)
   solutions.add_pool(
       name="best_solutions",
       policy=solnpool.PoolPolicy.keep_best,
       rel_tolerance=0.05,
       sense_is_min=True
   )

   # Create and add multiple solutions
   for i in range(5):
       # Vary the solution slightly
       x_value = app.solution_values["x"] * (1.0 + 0.1 * i)
       variables = [
           solnpool.create_variable(name="x", value=x_value),
           solnpool.create_variable(name="s[None,1].x", value=15.0),
           solnpool.create_variable(name="s[None,2].x", value=60.0),
       ]
       objectives = [solnpool.create_objective(value=76.5 + i)]

       solution_id = solutions.add(variables=variables, objectives=objectives)
       print(f"Added solution {solution_id} with objective {76.5 + i}")

   # Analyze the pools
   print("\nPool Analysis:")
   for pool_name in solutions.get_pool_names():
       solutions.activate(pool_name)
       print(f"\nPool '{pool_name}':")
       print(f"  Number of solutions: {len(solutions)}")
       print(f"  Best objective: {solutions.last_solution.objective().value}")

   # Export pool data
   pool_data = solutions.get_pool_dicts()
   print(f"\nExported data for {len(pool_data)} pools")

****************************
Advanced Features
****************************

Solution Comparison
==================

Solutions can be compared based on their variable values:

.. code-block:: python

   # Create two solutions
   sol1 = solutions[0]
   sol2 = solutions[1]

   # Check if solutions are equal
   if sol1 == sol2:
       print("Solutions are identical")
   else:
       print("Solutions are different")

Solution Serialization
======================

Solutions can be converted to dictionaries for serialization:

.. code-block:: python

   # Convert solution to dictionary
   soln_dict = solution.to_dict()

   # Convert to JSON string
   import json
   soln_json = json.dumps(soln_dict, indent=2)
   print(soln_json)

Working with Variable and Objective Info
=========================================

You can access detailed information about variables and objectives:

.. code-block:: python

   # Access variables
   for var in solution.variables():
       print(f"Variable: {var.name}, Value: {var.value}, Fixed: {var.fixed}")

   # Access objectives
   for obj in solution.objectives():
       print(f"Objective: {obj.name}, Value: {obj.value}")

   # Access specific variable by name
   x_var = solution.variable("x")
   print(f"x value: {x_var.value}")

Custom Solution Creation
========================

For advanced use cases, you can create custom solutions:

.. code-block:: python

   # Create variable info objects
   var1 = solnpool.VariableInfo(name="x", value=10.0, fixed=False, discrete=False)
   var2 = solnpool.VariableInfo(name="y", value=5.0, fixed=True, discrete=True)

   # Create objective info objects
   obj1 = solnpool.ObjectiveInfo(name="cost", value=150.0)

   # Create a solution directly
   custom_solution = solnpool.SparowSolution(
       variables=[var1, var2],
       objectives=[obj1],
       suffix={"custom_data": "example"}
   )

   # Add to pool
   sol_id = solutions.add(custom_solution)

*********
Reference
*********

Key Classes and Functions
=========================

SparowSolution
--------------

A solution class that extends `or_topas.solnpool.solution.Solution` with Sparow-specific features.

SparowPoolManager
-----------------

A pool manager that extends `or_topas.solnpool.solnpool.PoolManager` for managing Sparow solutions.

PoolPolicy
----------

An enumeration of available pool policies:
- `keep_all`: Keep all solutions
- `keep_best`: Keep solutions within tolerance of the best
- `keep_latest`: Keep most recent solutions
- `keep_latest_unique`: Keep most recent unique solutions
- `keep_pareto`: Keep Pareto non-dominated solutions

Helper Functions
----------------

create_variable(*args, **kwargs)
   Create a `VariableInfo` object

create_objective(*args, **kwargs)
   Create an `ObjectiveInfo` object
