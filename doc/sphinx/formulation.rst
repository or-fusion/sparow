############
Formulation
############

Formulating Stochastic Programs with Sparow
=============================================

Sparow provides a flexible framework for formulating stochastic programming problems. This guide will walk you through the key concepts and show you how to formulate your own stochastic programs.

Basic Structure
---------------

A typical Sparow formulation consists of:

1. **Problem Definition**: Define the stochastic program structure
2. **Scenario Definition**: Specify the uncertain scenarios
3. **Variable Declaration**: Declare decision variables
4. **Objective Function**: Define what to optimize
5. **Constraints**: Specify the problem constraints

Simple Example
--------------

Here's a simple example showing the basic structure:

.. code-block:: python

   import sparow
   from sparow import ScenarioTree

   # Create a scenario tree
   scenario_tree = ScenarioTree(num_stages=2)

   # Add scenarios
   scenario_tree.add_scenario("scenario_1", probability=0.5)
   scenario_tree.add_scenario("scenario_2", probability=0.5)

   # Define the model
   model = sparow.Model(scenario_tree=scenario_tree)

   # Add variables
   x = model.add_variable("x", lower_bound=0)
   y = model.add_variable("y", lower_bound=0)

   # Define objective
   model.set_objective(sparow.minimize(x + y))

   # Add constraints
   model.add_constraint(x + y >= 10)
   model.add_constraint(x <= 20)
   model.add_constraint(y <= 20)

Key Components
--------------

Scenario Trees
~~~~~~~~~~~~~~

Scenario trees represent the uncertainty structure in stochastic programming. They consist of:

* **Stages**: Time periods or decision points
* **Nodes**: Points in the scenario tree
* **Scenarios**: Specific realizations of uncertainty
* **Probabilities**: Likelihood of each scenario

.. code-block:: python

   from sparow import ScenarioTree

   # Create a 2-stage scenario tree
   tree = ScenarioTree(num_stages=2)

   # Add scenarios with probabilities
   tree.add_scenario("high_demand", probability=0.3)
   tree.add_scenario("medium_demand", probability=0.5)
   tree.add_scenario("low_demand", probability=0.2)

Variables
~~~~~~~~~

Variables represent the decisions to be made. They can be:

* **First-stage variables**: Decisions made before uncertainty is revealed
* **Second-stage variables**: Decisions made after some uncertainty is revealed
* **Recourse variables**: Decisions that can adapt to realized scenarios

.. code-block:: python

   # First-stage variable (here-and-now decision)
   x = model.add_variable("production", lower_bound=0)

   # Second-stage variable (wait-and-see decision)
   y = model.add_variable("inventory", lower_bound=0, stage=2)

Objectives
~~~~~~~~~~

The objective function defines what you want to optimize. Common objectives include:

* Minimizing cost
* Maximizing profit
* Minimizing risk
* Maximizing reliability

.. code-block:: python

   # Minimize total cost
   model.set_objective(sparow.minimize(production_cost + inventory_cost))

   # Maximize expected profit
   model.set_objective(sparow.maximize(expected_revenue - expected_cost))

Constraints
~~~~~~~~~~~

Constraints define the feasible region of the problem. They can be:

* **Deterministic constraints**: Must hold in all scenarios
* **Stochastic constraints**: May involve uncertain parameters
* **Non-anticipativity constraints**: Ensure consistency across scenarios

.. code-block:: python

   # Production capacity constraint
   model.add_constraint(production <= capacity)

   # Demand satisfaction constraint (stochastic)
   model.add_constraint(inventory + production >= demand)

Advanced Formulation Patterns
-----------------------------

Multi-Stage Problems
~~~~~~~~~~~~~~~~~~~~

For problems with multiple decision stages:

.. code-block:: python

   # Create a 3-stage scenario tree
   tree = ScenarioTree(num_stages=3)

   # Add variables at different stages
   x1 = model.add_variable("x1", stage=1)  # First-stage decision
   x2 = model.add_variable("x2", stage=2)  # Second-stage decision
   x3 = model.add_variable("x3", stage=3)  # Third-stage decision

Risk Measures
~~~~~~~~~~~~

Incorporate risk measures into your formulation:

.. code-block:: python

   # Expected value objective
   objective = sparow.ExpectedValue(cost)

   # Conditional Value-at-Risk (CVaR)
   risk_measure = sparow.CVaR(cost, alpha=0.95)
   model.set_objective(sparow.minimize(objective + 0.1 * risk_measure))

Best Practices
--------------

1. **Start Simple**: Begin with a simple formulation and gradually add complexity
2. **Validate Scenarios**: Ensure your scenarios adequately represent the uncertainty
3. **Check Feasibility**: Verify that your problem has feasible solutions
4. **Test with Small Instances**: Debug with small problem instances before scaling up
5. **Document Assumptions**: Clearly document your modeling assumptions

For more examples, see the :doc:`examples` section.