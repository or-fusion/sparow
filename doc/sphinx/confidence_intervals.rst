####################
Confidence Intervals
####################

Computing Confidence Intervals for Stochastic Solutions
=======================================================

Sparow provides tools for computing confidence intervals to assess the quality and reliability of stochastic programming solutions. Confidence intervals help quantify the uncertainty in your solutions and provide bounds on the true optimal value.

Overview
--------

Confidence intervals in stochastic programming are used to:

* **Assess solution quality**: Determine how close your solution is to the true optimum
* **Quantify uncertainty**: Understand the range of possible outcomes
* **Compare algorithms**: Evaluate different solution approaches
* **Make robust decisions**: Account for uncertainty in decision-making

Key Concepts
------------

Types of Confidence Intervals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sparow supports several types of confidence intervals:

* **Objective Value Confidence Intervals**: Bounds on the true optimal objective value
* **Solution Quality Confidence Intervals**: Bounds on how close your solution is to optimal
* **Variable Confidence Intervals**: Bounds on optimal variable values
* **Gap Confidence Intervals**: Bounds on the optimality gap

Statistical Methods
~~~~~~~~~~~~~~~~~~

Common statistical methods used:

* **Normal approximation**: For large sample sizes
* **Bootstrap methods**: Resampling-based approaches
* **Student's t-distribution**: For small sample sizes
* **Asymptotic methods**: Based on central limit theorem

Basic Usage
-----------

Here's how to compute confidence intervals for a stochastic solution:

.. code-block:: python

   from sparow.conf_intervals import compute_confidence_intervals
   from sparow.ef import ExtensiveFormSolver
   from sparow.sp.examples import simple_newsvendor

   # Solve the problem
   app = simple_newsvendor()
   solver = ExtensiveFormSolver()
   results = solver.solve(app.sp)

   # Compute confidence intervals
   ci_results = compute_confidence_intervals(results, app.sp)

   # Display confidence intervals
   print(f"Objective value: {ci_results.objective_estimate}")
   print(f"95% CI: [{ci_results.lower_bound}, {ci_results.upper_bound}]")
   print(f"Confidence interval width: {ci_results.width}")
   print(f"Relative gap: {ci_results.relative_gap}%")

Computing Confidence Intervals
-------------------------------

Objective Value Confidence Intervals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.conf_intervals import objective_ci

   # After solving your problem
   obj_ci = objective_ci(results, confidence_level=0.95)

   print(f"95% confidence interval for objective: [{obj_ci.lower}, {obj_ci.upper}]")

Solution Quality Confidence Intervals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.conf_intervals import solution_quality_ci

   # Compute solution quality confidence interval
   sq_ci = solution_quality_ci(results, true_optimum=known_optimum)

   print(f"Solution quality 95% CI: [{sq_ci.lower}, {sq_ci.upper}]")

Variable Confidence Intervals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.conf_intervals import variable_ci

   # Compute confidence intervals for specific variables
   var_ci = variable_ci(results, variable_name='x', confidence_level=0.95)

   print(f"95% CI for variable x: [{var_ci.lower}, {var_ci.upper}]")

Advanced Options
----------------

Customizing Confidence Interval Computation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.conf_intervals import ConfidenceIntervalOptions

   # Create options object
   ci_options = ConfidenceIntervalOptions(
       confidence_level=0.99,  # 99% confidence
       method='bootstrap',      # Use bootstrap method
       num_samples=1000,       # Number of bootstrap samples
       random_seed=42          # For reproducibility
   )

   # Compute confidence intervals with custom options
   ci_results = compute_confidence_intervals(results, app.sp, options=ci_options)

Different Statistical Methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Normal approximation (default for large samples)
   ci_normal = compute_confidence_intervals(results, app.sp, method='normal')

   # Bootstrap method (more robust but computationally expensive)
   ci_bootstrap = compute_confidence_intervals(results, app.sp, method='bootstrap', num_samples=500)

   # Student's t-distribution (better for small samples)
   ci_t = compute_confidence_intervals(results, app.sp, method='t-distribution')

Interpreting Results
--------------------

Understanding Confidence Interval Output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A typical confidence interval result includes:

* **Point estimate**: The estimated value (e.g., objective value)
* **Lower bound**: The lower end of the confidence interval
* **Upper bound**: The upper end of the confidence interval
* **Width**: The width of the confidence interval (upper - lower)
* **Confidence level**: The probability that the true value lies within the interval
* **Standard error**: The standard error of the estimate
* **Margin of error**: Half the width of the confidence interval

Example Interpretation
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   print(f"We are 95% confident that the true optimal objective value")
   print(f"lies between {ci_results.lower_bound} and {ci_results.upper_bound}")
   print(f"The width of this interval is {ci_results.width}")
   print(f"This means our estimate could be off by as much as {ci_results.margin_of_error}")

Assessing Solution Quality
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Compute optimality gap confidence interval
   gap_ci = ci_results.optimality_gap_ci

   print(f"We are 95% confident that the optimality gap is")
   print(f"between {gap_ci.lower*100:.2f}% and {gap_ci.upper*100:.2f}%")

   if gap_ci.upper < 0.05:  # If upper bound of gap is less than 5%
       print("The solution is likely within 5% of optimal")
   else:
       print("The solution may not be sufficiently close to optimal")

Best Practices
--------------

Choosing Confidence Levels
~~~~~~~~~~~~~~~~~~~~~~~~~~

* **90% confidence**: Good for initial exploration, wider intervals
* **95% confidence**: Standard choice for most applications
* **99% confidence**: More conservative, for critical decisions
* **Higher confidence**: Leads to wider intervals, less precision

Sample Size Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Small samples (< 30)**: Use t-distribution or bootstrap methods
* **Medium samples (30-100)**: Normal approximation may work well
* **Large samples (> 100)**: Normal approximation is usually appropriate
* **Very large samples**: Consider computational efficiency

Method Selection
~~~~~~~~~~~~~~~~

* **Normal approximation**: Fast, good for large samples with normal-like distributions
* **Bootstrap**: More robust, handles non-normal distributions, but computationally expensive
* **Analytical methods**: Fastest, but require specific assumptions
* **Hybrid approaches**: Combine methods for better performance

Example: Newsvendor Problem
----------------------------

Here's a complete example showing confidence interval computation for the newsvendor problem:

.. code-block:: python

   from sparow.ef import ExtensiveFormSolver
   from sparow.conf_intervals import compute_confidence_intervals
   from sparow.sp.examples import simple_newsvendor
   import numpy as np

   # Set random seed for reproducibility
   np.random.seed(42)

   # Create and solve the newsvendor problem
   app = simple_newsvendor()
   solver = ExtensiveFormSolver()
   solver.set_options(solver='highs')
   results = solver.solve(app.sp)

   # Compute confidence intervals
   ci_results = compute_confidence_intervals(results, app.sp, confidence_level=0.95)

   # Display results
   print("Newsvendor Problem Confidence Intervals")
   print("=" * 40)
   print(f"Estimated objective value: {ci_results.objective_estimate:.2f}")
   print(f"95% Confidence Interval: [{ci_results.lower_bound:.2f}, {ci_results.upper_bound:.2f}]")
   print(f"Interval width: {ci_results.width:.2f}")
   print(f"Relative width: {ci_results.relative_width*100:.1f}%")

   # Compute variable confidence intervals
   var_ci = ci_results.variable_cis['x']
   print(f"\n95% CI for order quantity: [{var_ci.lower:.2f}, {var_ci.upper:.2f}]")

   # Assess solution quality
   if ci_results.relative_width < 0.1:  # If relative width < 10%
       print("\nThe solution is reasonably precise.")
   else:
       print("\nThe solution has significant uncertainty.")

Advanced Topics
---------------

Variance Reduction Techniques
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reduce the variance of your estimates to get tighter confidence intervals:

.. code-block:: python

   from sparow.conf_intervals import VarianceReductionOptions

   vr_options = VarianceReductionOptions(
       use_antithetic_variates=True,
       use_control_variates=True,
       use_stratified_sampling=True
   )

   ci_results = compute_confidence_intervals(
       results, app.sp,
       variance_reduction=vr_options
   )

Batch Means Method
~~~~~~~~~~~~~~~~~

For time-series or correlated data:

.. code-block:: python

   ci_results = compute_confidence_intervals(
       results, app.sp,
       method='batch_means',
       batch_size=10
   )

Confidence Intervals for Different Solvers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compare confidence intervals across different solvers:

.. code-block:: python

   from sparow.ef import ExtensiveFormSolver
   from sparow.ph import ProgressiveHedgingSolver
   from sparow.benders import BendersSolver

   # Solve with different solvers
   ef_solver = ExtensiveFormSolver()
   ef_results = ef_solver.solve(app.sp)
   ef_ci = compute_confidence_intervals(ef_results, app.sp)

   ph_solver = ProgressiveHedgingSolver()
   ph_results = ph_solver.solve(app.sp)
   ph_ci = compute_confidence_intervals(ph_results, app.sp)

   # Compare confidence intervals
   print(f"EF solver 95% CI: [{ef_ci.lower_bound:.2f}, {ef_ci.upper_bound:.2f}]")
   print(f"PH solver 95% CI: [{ph_ci.lower_bound:.2f}, {ph_ci.upper_bound:.2f}]")

Visualizing Confidence Intervals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import matplotlib.pyplot as plt

   # Compute confidence intervals for different sample sizes
   sample_sizes = [10, 30, 50, 100, 200]
   ci_widths = []

   for n in sample_sizes:
       # Solve with n scenarios
       app_n = simple_newsvendor(num_scenarios=n)
       results_n = solver.solve(app_n.sp)
       ci_n = compute_confidence_intervals(results_n, app_n.sp)
       ci_widths.append(ci_n.width)

   # Plot confidence interval width vs sample size
   plt.figure(figsize=(10, 6))
   plt.plot(sample_sizes, ci_widths, 'o-')
   plt.xlabel('Number of Scenarios')
   plt.ylabel('Confidence Interval Width')
   plt.title('Confidence Interval Width vs Sample Size')
   plt.grid(True)
   plt.show()

Common Issues and Solutions
---------------------------

Wide Confidence Intervals
~~~~~~~~~~~~~~~~~~~~~~~~~

If your confidence intervals are too wide:

* **Increase sample size**: More scenarios lead to narrower intervals
* **Use variance reduction**: Techniques like antithetic variates can help
* **Improve solver accuracy**: Tighter solver tolerances may help
* **Check problem formulation**: Ensure your model is correctly specified

Non-convergence
~~~~~~~~~~~~~~

If confidence intervals don't converge:

* **Check solver convergence**: Ensure your solver is finding good solutions
* **Increase iterations**: For iterative solvers like PH
* **Debug your model**: Look for formulation errors
* **Try different methods**: Some statistical methods may work better

Inconsistent Results
~~~~~~~~~~~~~~~~~~~~

If you get different results on different runs:

* **Set random seeds**: For reproducibility
* **Use more samples**: Reduces random variation
* **Check solver settings**: Ensure deterministic behavior when needed
* **Investigate numerical issues**: Look for instability in your model

For more examples of computing confidence intervals, see the :doc:`examples/newsvendor` and :doc:`examples/facility_location` examples.