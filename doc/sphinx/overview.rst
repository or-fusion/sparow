######
Overview
######

.. py:currentmodule:: sparow

Sparow is a Python package designed for formulating and solving stochastic programming applications. It provides a flexible framework for defining stochastic optimization problems and offers multiple solver implementations including:

* **Expected Value (EF) Solver**: Computes the expected value of stochastic programs
* **Progressive Hedging (PH) Solver**: An iterative algorithm for solving stochastic programs
* **Benders Decomposition Solver**: A decomposition approach for large-scale stochastic programs
* **Confidence Intervals**: Tools for computing confidence intervals for stochastic solutions

Key Features
------------

* **Flexible Problem Formulation**: Define stochastic programming problems using familiar Python syntax
* **Multiple Solver Options**: Choose the solver that best fits your problem characteristics
* **Uncertainty Quantification**: Compute confidence intervals to assess solution quality
* **Extensible Architecture**: Easy to add custom solvers and problem formulations

Basic Concepts
--------------

Stochastic Programming
~~~~~~~~~~~~~~~~~~~~~~

Stochastic programming is a framework for modeling optimization problems that involve uncertainty. Unlike deterministic optimization, stochastic programming explicitly considers that some problem parameters are uncertain and follow probability distributions.

In Sparow, a stochastic program is typically formulated with:

* **Decision variables**: Variables that represent decisions to be made
* **Uncertain parameters**: Parameters whose values are uncertain
* **Objective function**: The function to be minimized or maximized
* **Constraints**: Restrictions on the decision variables

Sparow Workflow
~~~~~~~~~~~~~~~

The typical workflow for using Sparow is:

1. **Formulate** your stochastic programming problem using Sparow's API
2. **Choose** an appropriate solver (EF, PH, or Benders)
3. **Solve** the problem using the selected solver
4. **Analyze** the results and compute confidence intervals if needed
5. **Visualize** and interpret the solution

Example Applications
--------------------

Sparow can be used for various stochastic optimization problems such as:

* **Facility Location**: Deciding where to locate facilities under uncertain demand
* **Inventory Management**: Managing inventory levels with uncertain demand
* **Financial Portfolio Optimization**: Optimizing investment portfolios with uncertain returns
* **Energy Systems**: Planning energy systems with uncertain supply and demand
* **Agricultural Planning**: Making farming decisions under weather uncertainty

Getting Help
------------

For questions, issues, or contributions, please visit our GitHub repository.