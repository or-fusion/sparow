############
PH Solver
############

Progressive Hedging Solver
==========================

The Progressive Hedging (PH) solver is an iterative algorithm for solving stochastic programming problems. It's particularly effective for large-scale problems where the Extensive Form approach becomes computationally expensive.

Overview
--------

Progressive Hedging works by:

1. **Decomposing the problem**: Solving each scenario independently
2. **Iterative coordination**: Gradually enforcing consistency across scenarios
3. **Convergence**: Iterating until solutions across scenarios agree

The algorithm maintains:

* **Scenario subproblems**: Independent problems for each scenario
* **Penalty terms**: To enforce non-anticipativity
* **Weight updates**: Adjusting penalties based on solution disagreement

When to Use PH Solver
---------------------

The PH solver is particularly suitable when:

* You have a large number of scenarios
* The Extensive Form would be too large to solve directly
* You can tolerate approximate solutions
* The problem has a natural decomposition structure
* You need a scalable approach for very large problems

Basic Usage
-----------

Here's how to use the PH solver with a simple example:

.. code-block:: python

   from sparow.ph import ProgressiveHedgingSolver
   from sparow.sp.examples import simple_newsvendor

   # Create the stochastic programming application
   app = simple_newsvendor()

   # Create the PH solver
   solver = ProgressiveHedgingSolver()

   # Solve the problem
   results = solver.solve(app.sp)

   # Get the results
   results_dict = results.to_dict()
   solution = next(iter(results_dict["solutions"].values()))

   print(f"Objective value: {solution['objectives'][0]['value']}")

Solver Options
--------------

The PH solver accepts various options to customize its behavior:

.. code-block:: python

   solver = ProgressiveHedgingSolver()

   # Set the optimization solver for subproblems
   solver.set_options(solver='gurobi')

   # Set maximum number of iterations
   solver.set_options(max_iterations=1000)

   # Set convergence tolerance
   solver.set_options(tolerance=1e-4)

   # Enable verbose output
   solver.set_options(verbose=True)

   # Set penalty weight parameters
   solver.set_options(initial_weight=1.0)
   solver.set_options(weight_increase_factor=1.5)

Algorithm Details
-----------------

The Progressive Hedging algorithm follows these steps:

1. **Initialization**: Set initial penalty weights and solve each scenario independently
2. **Iteration**:
   a. Solve each scenario subproblem with current penalty terms
   b. Compute scenario solutions and objective values
   c. Update penalty weights based on solution disagreement
   d. Check for convergence
3. **Termination**: Stop when convergence criteria are met or maximum iterations reached

Key Parameters
~~~~~~~~~~~~~~

* **Initial Weight**: Starting value for penalty weights
* **Weight Increase Factor**: How much to increase weights when solutions disagree
* **Maximum Iterations**: Upper limit on iterations
* **Tolerance**: Convergence criterion based on solution agreement
* **Rho Update Rule**: Strategy for updating penalty weights

Example: Newsvendor Problem
---------------------------

Here's how to solve the newsvendor problem using PH:

.. code-block:: python

   from sparow.ph import ProgressiveHedgingSolver
   from sparow.sp.examples import LF_newsvendor

   # Create the newsvendor application with more scenarios
   app = LF_newsvendor()

   # Create PH solver with custom options
   solver = ProgressiveHedgingSolver()
   solver.set_options(solver='gurobi')
   solver.set_options(max_iterations=500)
   solver.set_options(tolerance=1e-5)
   solver.set_options(verbose=True)

   # Solve the problem
   results = solver.solve(app.sp)

   # Analyze results
   results_dict = results.to_dict()
   solution = next(iter(results_dict["solutions"].values()))

   x_value = solution['variables'][0]['value']
   print(f"Optimal order quantity: {x_value}")
   print(f"Expected profit: {-solution['objectives'][0]['value']}")
   print(f"Number of iterations: {results.num_iterations}")

Advanced Features
-----------------

Warm Starting
~~~~~~~~~~~~~

You can provide initial solutions to warm start the PH algorithm:

.. code-block:: python

   # Provide initial solution guess
   initial_solution = {
       'x': 50,  # Initial guess for decision variable
       # ... other variables
   }
   solver.set_options(initial_solution=initial_solution)

Monitoring Progress
~~~~~~~~~~~~~~~~~~

Track the progress of the PH algorithm:

.. code-block:: python

   solver.set_options(verbose=True)
   solver.set_options(print_frequency=10)  # Print progress every 10 iterations

Custom Weight Updates
~~~~~~~~~~~~~~~~~~~~

Implement custom weight update strategies:

.. code-block:: python

   def custom_weight_update(iteration, current_weights, disagreements):
       # Your custom weight update logic
       new_weights = current_weights * 1.2  # Example: 20% increase
       return new_weights

   solver.set_options(custom_weight_update=custom_weight_update)

Comparison with Other Solvers
-----------------------------

**PH vs EF (Extensive Form):**

* PH is iterative; EF solves directly
* PH can handle larger problems; EF may struggle with many scenarios
* PH provides approximate solutions; EF gives exact solutions
* PH is more memory-efficient; EF creates large monolithic problems
* PH can be slower to converge; EF solves in one optimization

**PH vs Benders Decomposition:**

* PH uses scenario decomposition; Benders uses scenario and constraint decomposition
* PH is simpler to implement; Benders can be more complex
* PH works well for general problems; Benders excels with special structures
* PH convergence can be sensitive to weights; Benders has different tuning parameters

Performance Tips
----------------

1. **Start with reasonable initial weights** (typically 1.0 to 10.0)
2. **Use a moderate weight increase factor** (1.2 to 2.0)
3. **Monitor convergence** to detect if weights are too aggressive or conservative
4. **Provide good initial solutions** when possible
5. **Use efficient subproblem solvers** - PH solves many subproblems
6. **Consider parallelization** - scenario subproblems can often be solved in parallel

Troubleshooting
---------------

**Slow convergence:**

* Increase the weight increase factor
* Try different initial weights
* Provide better initial solutions
* Check if your problem has special structure that could be exploited

**Oscillating solutions:**

* Reduce the weight increase factor
* Try different weight update strategies
* Increase the tolerance slightly

**Subproblems infeasible:**

* Check that individual scenarios are feasible
* Relax constraints temporarily to identify issues
* Consider reformulating your problem

**Memory issues:**

* Reduce the number of scenarios
* Use more efficient data structures
* Consider scenario sampling or clustering

Example Applications
-------------------

PH is particularly effective for:

* **Large-scale facility location** problems with many demand scenarios
* **Energy system planning** with uncertain renewable generation
* **Supply chain optimization** under demand uncertainty
* **Financial portfolio optimization** with many market scenarios

For more examples of using the PH solver, see the :doc:`../examples/facility_location` and :doc:`../examples/farmers` examples.