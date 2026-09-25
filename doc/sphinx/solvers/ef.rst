############
EF Solver
############

Expected Value (Extensive Form) Solver
=======================================

The Expected Value (EF) solver, also known as the Extensive Form solver, is one of the fundamental approaches for solving stochastic programming problems in Sparow. It transforms the stochastic program into a large deterministic equivalent problem and solves it directly.

Overview
--------

The EF solver works by:

1. **Creating the deterministic equivalent**: Combining all scenarios into a single large optimization problem
2. **Adding non-anticipativity constraints**: Ensuring that decisions made before uncertainty is revealed are consistent across scenarios
3. **Solving the extensive form**: Using standard optimization solvers to find the optimal solution

When to Use EF Solver
---------------------

The EF solver is particularly suitable when:

* You have a relatively small number of scenarios
* The problem size (after combining all scenarios) is manageable for your solver
* You need exact solutions rather than iterative approximations
* The problem has a simple structure without complex uncertainty patterns

Basic Usage
-----------

Here's how to use the EF solver with a simple example:

.. code-block:: python

   from sparow.ef import ExtensiveFormSolver
   from sparow.sp.examples import simple_newsvendor

   # Create the stochastic programming application
   app = simple_newsvendor()

   # Create the EF solver
   solver = ExtensiveFormSolver()

   # Solve the problem
   results = solver.solve(app.sp)

   # Get the results
   results_dict = results.to_dict()
   solution = next(iter(results_dict["solutions"].values()))

   print(f"Objective value: {solution['objectives'][0]['value']}")

Solver Options
--------------

The EF solver accepts various options to customize its behavior:

.. code-block:: python

   solver = ExtensiveFormSolver()

   # Set the optimization solver (e.g., 'gurobi', 'cplex', 'highs', 'glpk')
   solver.set_options(solver='gurobi')

   # Enable or disable verbose output
   solver.set_options(verbose=True)

   # Set other solver-specific options
   solver.set_options(mipgap=0.01)  # 1% optimality gap for MIP problems

Advanced Features
-----------------

Returning the Extensive Form
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can get the extensive form model for inspection or modification:

.. code-block:: python

   results = solver.solve_and_return_EF(app.sp)
   ef_model = results.model

   # You can now inspect or modify the extensive form model
   print(ef_model.display())

Handling Large Problems
~~~~~~~~~~~~~~~~~~~~~~

For larger problems, consider:

* **Using efficient solvers**: Commercial solvers like Gurobi or CPLEX often handle large problems better
* **Reducing scenarios**: Use scenario reduction techniques if you have many similar scenarios
* **Warm starts**: Provide initial solutions to help the solver
* **Parallel solving**: Some solvers support parallel optimization

Example: Newsvendor Problem
---------------------------

The newsvendor problem is a classic stochastic programming example that demonstrates the EF solver:

.. code-block:: python

   from sparow.ef import ExtensiveFormSolver
   from sparow.sp.examples import simple_newsvendor

   # Create the newsvendor application
   app = simple_newsvendor()

   # Set up and solve with EF
   solver = ExtensiveFormSolver()
   solver.set_options(solver='highs')  # Use Highs solver
   results = solver.solve(app.sp)

   # Analyze results
   results_dict = results.to_dict()
   solution = next(iter(results_dict["solutions"].values()))

   # Extract decision variables
   x_value = solution['variables'][0]['value']
   print(f"Optimal order quantity: {x_value}")
   print(f"Expected profit: {-solution['objectives'][0]['value']}")

Comparison with Other Solvers
-----------------------------

**EF vs Progressive Hedging (PH):**

* EF solves the problem directly as one large optimization
* PH uses an iterative approach that can handle larger problems
* EF gives exact solutions; PH provides approximate solutions
* EF may be slower for very large problems; PH can be more scalable

**EF vs Benders Decomposition:**

* EF creates one monolithic problem; Benders decomposes by scenarios
* EF is simpler to implement; Benders can be more efficient for certain structures
* EF works well for moderate-sized problems; Benders excels with block-separable structures

Performance Tips
----------------

1. **Start with a subset of scenarios** to test your formulation
2. **Use warm starts** when solving similar problems repeatedly
3. **Monitor solver progress** to identify performance bottlenecks
4. **Consider problem structure** - some problems are naturally better suited for EF
5. **Profile your code** to identify where time is being spent

Troubleshooting
---------------

**Problem too large:**

* Reduce the number of scenarios
* Consider using PH or Benders solvers instead
* Check if your problem has special structure that can be exploited

**Solver fails to find solution:**

* Check that your problem is feasible
* Relax constraints temporarily to identify infeasibilities
* Try different solver options (e.g., different algorithms)

**Slow performance:**

* Try a different solver (commercial solvers often perform better)
* Adjust solver parameters (e.g., tolerances, algorithms)
* Consider reformulating your problem

For more examples of using the EF solver, see the :doc:`../examples/newsvendor` example.