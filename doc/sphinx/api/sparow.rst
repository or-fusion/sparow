########
API Reference
########

Sparow API Documentation
=========================

This section provides an overview of Sparow's main classes and functions. For detailed API documentation, refer to the docstrings in the source code.

Main Classes
------------

Stochastic Program
~~~~~~~~~~~~~~~~~~

The ``StochasticProgram`` class is the main container for stochastic programming problems:

* ``sparow.sp.StochasticProgram`` - Main class for defining stochastic programs
* ``sparow.sp.ScenarioTree`` - Represents the uncertainty structure

Solvers
-------

Sparow provides three main solvers:

* ``sparow.ef.ExtensiveFormSolver`` - Solves the deterministic equivalent
* ``sparow.ph.ProgressiveHedgingSolver`` - Uses iterative scenario decomposition
* ``sparow.benders.BendersSolver`` - Uses Benders decomposition

Confidence Intervals
--------------------

* ``sparow.conf_intervals.compute_confidence_intervals`` - Compute confidence intervals for solutions
* ``sparow.conf_intervals.objective_ci`` - Confidence intervals for objective values
* ``sparow.conf_intervals.variable_ci`` - Confidence intervals for variables

Examples
--------

For practical examples of using these classes and functions, see the :doc:`../examples` section.

Additional Documentation
-----------------------

For more detailed information about specific functions and classes, refer to the docstrings in the source code or use Python's help system:

.. code-block:: python

   import sparow
   help(sparow.ExtensiveFormSolver)

   # Or for specific methods
   help(sparow.ExtensiveFormSolver.solve)

The API is designed to be intuitive and follows Python conventions. Most classes provide comprehensive docstrings with examples.