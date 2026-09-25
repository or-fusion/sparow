############
Benders Solver
############

Benders Decomposition Solver
=============================

The Benders decomposition solver is a powerful approach for solving large-scale stochastic programming problems by decomposing them into smaller, more manageable subproblems.

Overview
--------

Benders decomposition works by:

1. **Problem decomposition**: Separating the problem into a master problem and subproblems
2. **Iterative refinement**: Alternating between solving the master problem and subproblems
3. **Cut generation**: Adding constraints (cuts) to the master problem based on subproblem solutions
4. **Convergence**: Iterating until the master problem solution satisfies all subproblem constraints

The approach is particularly effective for problems with:

* **Block-separable structure**: Where constraints can be naturally grouped
* **Many scenarios**: That make the extensive form too large
* **Special structures**: That can be exploited in the decomposition

When to Use Benders Solver
--------------------------

The Benders solver is particularly suitable when:

* You have a large number of scenarios
* The problem has a natural block-separable structure
* The Extensive Form would be too large to solve directly
* You need to solve very large-scale problems efficiently
* The problem has complicating variables that connect different blocks

Basic Usage
-----------

Here's how to use the Benders solver with a simple example:

.. code-block:: python

   from sparow.benders import BendersSolver
   from sparow.sp.examples import simple_absolute_value

   # Create the stochastic programming application
   app = simple_absolute_value()

   # Create the Benders solver
   solver = BendersSolver()

   # Solve the problem
   results = solver.solve(app.sp)

   # Get the results
   results_dict = results.to_dict()
   solution = next(iter(results_dict["solutions"].values()))

   print(f"Objective value: {solution['objectives'][0]['value']}")

Solver Options
--------------

The Benders solver accepts various options to customize its behavior:

.. code-block:: python

   solver = BendersSolver()

   # Set the optimization solver for master and subproblems
   solver.set_options(mip_solver='gurobi')
   solver.set_options(lp_solver='gurobi')

   # Set maximum number of iterations
   solver.set_options(max_iterations=100)

   # Set convergence tolerance
   solver.set_options(tolerance=1e-4)

   # Enable verbose output
   solver.set_options(verbose=True)

   # Set cut management options
   solver.set_options(max_cuts=50)
   solver.set_options(cut_selection='most_violated')

Algorithm Details
-----------------

The Benders decomposition algorithm follows these steps:

1. **Initialization**: Solve a relaxed master problem
2. **Iteration**:
   a. Solve subproblems for each scenario using the master problem solution
   b. Generate optimality cuts and/or feasibility cuts
   c. Add cuts to the master problem
   d. Re-solve the master problem with new cuts
   e. Check for convergence
3. **Termination**: Stop when convergence criteria are met or maximum iterations reached

Key Components
~~~~~~~~~~~~~~

**Master Problem:**

* Contains the complicating variables (variables that appear in multiple subproblems)
* Initially relaxed (without all constraints)
* Gets progressively tighter as cuts are added

**Subproblems:**

* One for each scenario or block
* Fixed complicating variables from master problem
* Generate cuts based on their solutions

**Cuts:**

* **Optimality cuts**: Ensure the master problem solution is optimal
* **Feasibility cuts**: Ensure the master problem solution is feasible for subproblems

Example: Absolute Value Problem
--------------------------------

Here's how to solve a problem using Benders decomposition:

.. code-block:: python

   from sparow.benders import BendersSolver
   from sparow.sp.examples import simple_absolute_value

   # Create the application
   app = simple_absolute_value()

   # Create Benders solver with custom options
   solver = BendersSolver()
   solver.set_options(mip_solver='gurobi')
   solver.set_options(max_iterations=50)
   solver.set_options(tolerance=1e-5)
   solver.set_options(verbose=True)

   # Solve the problem
   results = solver.solve(app.sp)

   # Analyze results
   results_dict = results.to_dict()
   solution = next(iter(results_dict["solutions"].values()))

   print(f"Optimal solution: {solution['variables'][0]['value']}")
   print(f"Objective value: {solution['objectives'][0]['value']}")
   print(f"Number of iterations: {results.num_iterations}")
   print(f"Number of cuts added: {results.num_cuts}")

Advanced Features
-----------------

Cut Management
~~~~~~~~~~~~~~

Manage how cuts are generated and added:

.. code-block:: python

   # Limit the number of cuts added per iteration
   solver.set_options(max_cuts_per_iteration=5)

   # Choose which cuts to add
   solver.set_options(cut_selection='most_violated')  # Add most violated cuts first

Warm Starting
~~~~~~~~~~~~~

Provide initial solutions to warm start the algorithm:

.. code-block:: python

   # Provide initial solution guess for master problem
   initial_master_solution = {
       'x': 10.0,  # Initial guess for complicating variable
       # ... other variables
   }
   solver.set_options(initial_master_solution=initial_master_solution)

Parallel Subproblem Solving
~~~~~~~~~~~~~~~~~~~~~~~~~~

Solve subproblems in parallel for better performance:

.. code-block:: python

   solver.set_options(parallel_subproblems=True)
   solver.set_options(num_workers=4)  # Use 4 worker processes

Custom Cut Generation
~~~~~~~~~~~~~~~~~~~~

Implement custom cut generation strategies:

.. code-block:: python

   def custom_cut_generator(subproblem_results):
       # Your custom cut generation logic
       cuts = []
       for result in subproblem_results:
           # Generate cuts based on subproblem results
           cut = generate_custom_cut(result)
           cuts.append(cut)
       return cuts

   solver.set_options(custom_cut_generator=custom_cut_generator)

Comparison with Other Solvers
-----------------------------

**Benders vs EF (Extensive Form):**

* Benders decomposes the problem; EF solves it monolithically
* Benders can handle much larger problems; EF may struggle with many scenarios
* Benders is more complex to implement; EF is simpler
* Benders requires problem structure; EF works for any problem
* Benders can be more efficient for structured problems; EF has consistent performance

**Benders vs Progressive Hedging (PH):**

* Benders uses constraint decomposition; PH uses scenario decomposition
* Benders generates cuts; PH uses penalty weights
* Benders works well for problems with complicating variables; PH works for general problems
* Benders convergence depends on cut quality; PH convergence depends on weight tuning
* Benders can handle certain structures very efficiently; PH is more generally applicable

Performance Tips
----------------

1. **Identify good complicating variables** - choose variables that naturally decompose the problem
2. **Start with a reasonable number of cuts** - too many cuts can slow down the master problem
3. **Use effective cut selection** - focus on the most violated cuts
4. **Provide good initial solutions** when possible
5. **Use parallel subproblem solving** to exploit multi-core systems
6. **Monitor cut effectiveness** - remove redundant or ineffective cuts
7. **Tune solver parameters** for both master and subproblems

Troubleshooting
---------------

**Slow convergence:**

* Try different cut selection strategies
* Increase the maximum number of cuts per iteration
* Provide better initial solutions
* Check if your problem decomposition is appropriate

**Master problem becomes too large:**

* Limit the number of cuts added
* Remove redundant cuts periodically
* Consider cut aggregation techniques

**Subproblems infeasible:**

* Check that individual subproblems are feasible
* Add feasibility cuts to guide the master problem
* Relax constraints temporarily to identify issues

**Oscillating solutions:**

* Adjust the tolerance criteria
* Try different cut generation strategies
* Consider stabilizing techniques

Example Applications
-------------------

Benders decomposition is particularly effective for:

* **Facility location problems** with many potential locations and demand scenarios
* **Production planning** with complex multi-period constraints
* **Energy system optimization** with network constraints and uncertainty
* **Supply chain design** with multiple echelons and uncertainty
* **Financial planning** with complex constraints and many scenarios

For more examples of using the Benders solver, see the :doc:`../examples/facility_location` and :doc:`../examples/absolute_value` examples.

Advanced Topics
---------------

Multi-cut Benders
~~~~~~~~~~~~~~~~

Instead of aggregating subproblem information into single cuts, use multiple cuts:

.. code-block:: python

   solver.set_options(multi_cut=True)
   solver.set_options(cuts_per_subproblem=3)

Nested Benders
~~~~~~~~~~~~~~

For problems with multiple levels of decomposition:

.. code-block:: python

   solver.set_options(nested_decomposition=True)
   solver.set_options(inner_solver='ph')  # Use PH for inner decomposition

Stochastic Benders
~~~~~~~~~~~~~~~~~

For problems with stochastic subproblems:

.. code-block:: python

   solver.set_options(stochastic_subproblems=True)
   solver.set_options(subproblem_solver='ef')  # Use EF for stochastic subproblems

Best Practices
--------------

1. **Start with a simple decomposition** and gradually add complexity
2. **Validate your decomposition** with small problem instances
3. **Monitor cut quality** - effective cuts are key to good performance
4. **Balance master and subproblem complexity** - neither should be a bottleneck
5. **Use problem-specific knowledge** to guide the decomposition strategy