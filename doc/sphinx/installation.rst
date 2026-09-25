############
Installation
############

Prerequisites
-------------

Sparow requires:

* Python 3.7 or higher
* Pyomo (for mathematical optimization)
* NumPy (for numerical operations)
* SciPy (for scientific computing)
* Matplotlib (for visualization, optional)

Installing from PyPI
--------------------

The recommended way to install Sparow is using pip:

.. code-block:: bash

   pip install sparow

Installing from Source
----------------------

To install the latest development version from source:

.. code-block:: bash

   git clone https://github.com/sandialabs/sparow.git
   cd sparow
   pip install .

Dependencies
------------

Sparow will automatically install the required dependencies. For a complete installation including optional dependencies:

.. code-block:: bash

   pip install sparow[all]

Verifying Installation
----------------------

After installation, you can verify that Sparow is working correctly:

.. code-block:: python

   import sparow
   print(sparow.__version__)

Troubleshooting
---------------

If you encounter any issues during installation:

1. **Permission Issues**: Use `pip install --user sparow` to install in user space
2. **Missing Dependencies**: Ensure you have Python development headers installed
3. **Solver Issues**: Make sure you have appropriate solvers (e.g., GLPK, CPLEX, Gurobi) installed and configured

For Windows users, we recommend using the Anaconda distribution which includes many of the required scientific computing packages.