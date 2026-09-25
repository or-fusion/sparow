####################
Multifidelity Models
####################

Multifidelity Modeling in Sparow
=================================

Multifidelity modeling is an advanced feature in Sparow that allows you to combine models of different fidelity levels. This enables efficient exploration of the solution space by balancing computational cost with solution accuracy.

What is Multifidelity?
----------------------

Multifidelity combines models with different levels of detail:

**High-Fidelity (HF) Models:**
- More complex and accurate
- Computationally expensive
- Detailed representation of the problem
- Used for final solution refinement

**Low-Fidelity (LF) Models:**
- Simpler and less accurate
- Computationally cheap
- Approximate representation of the problem
- Used for initial exploration and guidance

Key Benefits:
- **Computational efficiency**: LF models reduce overall solving time
- **Solution quality**: HF models ensure accurate final solutions
- **Flexible exploration**: Balance between speed and accuracy
- **Adaptive refinement**: Start with LF, refine with HF

Multifidelity Data Structure
----------------------------

Multifidelity data has a nested structure with separate models:

.. code-block:: python

   mf_data = {
       "HF": {  # High-fidelity model
           "scen_1": {"Demand": 3, "Probability": 0.4},
           "scen_0": {"Demand": 1, "Probability": 0.6},
       },
       "LF": {  # Low-fidelity model
           "scen_3": {"Demand": 4, "Probability": 0.2},
           "scen_2": {"Demand": 2, "Probability": 0.8},
       }
   }

Key Characteristics:
- Each model has its own scenario set
- Scenarios can have different parameters
- Probabilities are defined per scenario
- Models can have different levels of detail

Multifidelity Bundling Schemes
------------------------------

Sparow provides specialized bundling schemes for multifidelity models:

**1. Paired Bundling**

Each HF scenario is paired with an LF scenario:

.. code-block:: python

   from sparow.sp.bundling.MF_schemes import mf_paired

   # Pair HF and LF scenarios
   bundles = mf_paired(data, models=["HF", "LF"], bundle_args)

Use when:
- You have a direct correspondence between HF and LF scenarios
- Each HF scenario has a natural LF counterpart
- You want simple 1:1 pairing

**2. Random Nested Bundling**

LF scenarios are randomly nested within HF scenarios:

.. code-block:: python

   from sparow.sp.bundling.MF_schemes import mf_random_nested

   # Randomly nest LF scenarios
   bundles = mf_random_nested(data, models=["HF", "LF"], bundle_args)

Use when:
- No clear relationship between HF and LF scenarios
- You want random exploration
- Initial testing and development

**3. K-Means Similar Bundling**

LF scenarios are bundled with the closest HF scenario:

.. code-block:: python

   from sparow.sp.bundling.MF_schemes import mf_kmeans_similar

   # Bundle similar scenarios
   bundles = mf_kmeans_similar(data, models=["HF", "LF"], bundle_args)

Parameters:
- `bun_size`: Approximate size of each bundle
- `dkey`: Data key to use for distance calculation

Use when:
- LF scenarios should be grouped with similar HF scenarios
- You want to preserve scenario relationships
- Scenario data has clear similarity metrics

**4. K-Means Dissimilar Bundling**

LF scenarios are bundled with the furthest HF scenario:

.. code-block:: python

   from sparow.sp.bundling.MF_schemes import mf_kmeans_dissimilar

   # Bundle dissimilar scenarios
   bundles = mf_kmeans_dissimilar(data, models=["HF", "LF"], bundle_args)

Use when:
- You want to explore diverse scenario combinations
- LF scenarios should contrast with HF scenarios
- You need broad coverage of the solution space

**5. Custom Bundle List**

Specify your own multifidelity bundles:

.. code-block:: python

   from sparow.sp.bundling.MF_schemes import mf_bundle_from_list

   # Custom multifidelity bundles
   bundles = mf_bundle_from_list(data, models=["HF", "LF"], bundle_args={
       "bundles": [
           [("HF", "scen_1"), ("LF", "scen_3")],
           [("HF", "scen_0"), ("LF", "scen_2")]
       ]
   })

Use when:
- You have domain knowledge about scenario relationships
- You need precise control over bundling
- Default schemes don't meet your needs

Creating Multifidelity Models
-----------------------------

To create a multifidelity stochastic program:

.. code-block:: python

   from sparow.sp import stochastic_program

   # Step 1: Create stochastic program
   sp = stochastic_program(first_stage_variables=["x"])

   # Step 2: Initialize with HF model
   sp.initialize_application(app_data=app_data)
   sp.initialize_model(
       name="HF",
       model_data=hf_data,
       model_builder=hf_builder
   )

   # Step 3: Add LF model
   sp.initialize_model(
       name="LF",
       model_data=lf_data,
       model_builder=lf_builder,
       default=False  # Not the default model
   )

   # Step 4: Set multifidelity bundling
   from sparow.sp.bundling.MF_schemes import mf_kmeans_similar
   bundles = mf_kmeans_similar(
       sp.model_data,
       models=["HF", "LF"],
       bundle_args={'bun_size': 3}
   )
   sp.set_bundles(bundles)

Key Components:
- **Multiple models**: HF and LF models with different characteristics
- **Separate initialization**: Each model is initialized independently
- **Multifidelity bundling**: Specialized schemes for combining models
- **Default model**: One model is marked as default for solving

Multifidelity Bundle Structure
------------------------------

Multifidelity bundles combine scenarios from different models:

.. code-block:: python

   mf_bundles = {
       "bundle_1": {
           "scenarios": {
               "(HF, scen_1)": 0.6,  # HF scenario 1
               "(LF, scen_3)": 0.4,  # LF scenario 3
           },
           "Probability": 0.3
       },
       "bundle_2": {
           "scenarios": {
               "(HF, scen_0)": 0.5,
               "(LF, scen_2)": 0.5,
           },
           "Probability": 0.7
       }
   }

Note the special scenario keys like `"(HF, scen_1)"` that identify both the model and scenario.

Model Weights
-------------

You can assign different weights to models to control their influence:

.. code-block:: python

   # Define model weights
   model_weights = {
       "HF": 0.7,  # High-fidelity gets 70% weight
       "LF": 0.3   # Low-fidelity gets 30% weight
   }

   # Create weighted multifidelity bundles
   bundles = mf_kmeans_similar(
       sp.model_data,
       models=["HF", "LF"],
       model_weight=model_weights
   )
   sp.set_bundles(bundles)

Weight Considerations:
- Higher weight = more influence on the solution
- HF models typically get higher weights (0.6-0.8)
- LF models get lower weights (0.2-0.4)
- Weights should reflect model accuracy and importance

Practical Multifidelity Examples
--------------------------------

Newsvendor Problem
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.sp import stochastic_program
   from sparow.sp.bundling.MF_schemes import mf_kmeans_similar

   # Application data (shared by both models)
   app_data = dict(c=1.0, b=1.5, h=0.1)

   # High-fidelity model with detailed scenarios
   hf_data = {
       "scenarios": [
           {"ID": f"hf_{i}", "d": d, "Probability": 0.1}
           for i, d in enumerate([15, 60, 72, 78, 82, 65, 55, 90])
       ],
   }

   # Low-fidelity model with aggregated scenarios
   lf_data = {
       "scenarios": [
           {"ID": f"lf_{i}", "d": d, "Probability": 0.25}
           for i, d in enumerate([30, 50, 70, 90])
       ],
   }

   # Create multifidelity stochastic program
   sp = stochastic_program(first_stage_variables=["x"])
   sp.initialize_application(app_data=app_data)

   # Initialize models
   sp.initialize_model(name="HF", model_data=hf_data, model_builder=builder)
   sp.initialize_model(name="LF", model_data=lf_data, model_builder=builder, default=False)

   # Use multifidelity bundling
   bundles = mf_kmeans_similar(
       sp.model_data,
       models=["HF", "LF"],
       bundle_args={'bun_size': 3},
       model_weight={'HF': 0.7, 'LF': 0.3}
   )
   sp.set_bundles(bundles)

Facility Location Problem
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # HF model: Detailed customer demand scenarios
   hf_data = {
       "scenarios": [
           {"ID": f"hf_{i}", "demands": detailed_demands[i], "Probability": probs[i]}
           for i in range(100)
       ],
   }

   # LF model: Aggregated demand regions
   lf_data = {
       "scenarios": [
           {"ID": f"lf_{i}", "demands": aggregated_demands[i], "Probability": probs[i]}
           for i in range(10)
       ],
   }

   # Create multifidelity program
   sp = stochastic_program(first_stage_variables=["x1", "x2", "x3"])
   sp.initialize_application(app_data=facility_data)
   sp.initialize_model(name="HF", model_data=hf_data, model_builder=facility_builder)
   sp.initialize_model(name="LF", model_data=lf_data, model_builder=facility_builder, default=False)

   # Use paired bundling for direct correspondence
   bundles = mf_paired(sp.model_data, models=["HF", "LF"])
   sp.set_bundles(bundles)

When to Use Multifidelity
-------------------------

**Use multifidelity when:**
- ✅ You have expensive high-fidelity simulations
- ✅ You need to explore a large solution space efficiently
- ✅ You can create meaningful low-fidelity approximations
- ✅ You want to balance accuracy with computational cost
- ✅ You're solving complex, computationally intensive problems

**Avoid multifidelity when:**
- ❌ Your problem is already computationally cheap
- ❌ You can't create meaningful low-fidelity models
- ❌ You need exact high-fidelity solutions
- ❌ Your problem is simple and fast to solve
- ❌ The overhead of multifidelity outweighs the benefits

Advanced Multifidelity Techniques
----------------------------------

Adaptive Multifidelity
~~~~~~~~~~~~~~~~~~~~~~

Start with LF models and adaptively refine with HF:

.. code-block:: python

   # Phase 1: Solve with LF only
   sp.initialize_model(name="LF", model_data=lf_data, model_builder=lf_builder)
   solver.solve(sp)  # Fast, approximate solution

   # Phase 2: Add HF and refine
   sp.initialize_model(name="HF", model_data=hf_data, model_builder=hf_builder, default=False)
   bundles = mf_kmeans_similar(sp.model_data, models=["HF", "LF"])
   sp.set_bundles(bundles)
   solver.solve(sp)  # Refined solution

Progressive Multifidelity
~~~~~~~~~~~~~~~~~~~~~~~~

Gradually increase the fidelity during solving:

.. code-block:: python

   # Start with mostly LF
   bundles = mf_kmeans_similar(sp.model_data, models=["HF", "LF"],
                               model_weight={'HF': 0.2, 'LF': 0.8})
   sp.set_bundles(bundles)

   # Gradually increase HF weight
   for iteration in range(10):
       hf_weight = 0.2 + iteration * 0.08
       bundles = mf_kmeans_similar(sp.model_data, models=["HF", "LF"],
                                   model_weight={'HF': hf_weight, 'LF': 1-hf_weight})
       sp.set_bundles(bundles)
       results = solver.solve(sp)

Multiple Fidelity Levels
~~~~~~~~~~~~~~~~~~~~~~~~

Use more than two fidelity levels:

.. code-block:: python

   # Add medium-fidelity model
   sp.initialize_model(name="MF", model_data=mf_data, model_builder=mf_builder, default=False)

   # Bundle all three levels
   bundles = mf_kmeans_similar(sp.model_data, models=["HF", "MF", "LF"],
                               model_weight={'HF': 0.5, 'MF': 0.3, 'LF': 0.2})
   sp.set_bundles(bundles)

Best Practices for Multifidelity
--------------------------------

1. **Create Meaningful LF Models**:
   - LF models should approximate HF behavior
   - Preserve key characteristics of the problem
   - Be significantly faster to solve

2. **Start with HF**:
   - Begin with high-fidelity to understand the problem
   - Then add low-fidelity for efficiency

3. **Gradually Add LF**:
   - Introduce low-fidelity models incrementally
   - Test the impact on solution quality

4. **Test Weights**:
   - Experiment with different model weights
   - Start with HF-heavy weights (70-80%)
   - Adjust based on results

5. **Validate Results**:
   - Compare multifidelity results with pure HF
   - Check that key decisions are preserved
   - Validate that objective values are reasonable

6. **Monitor Performance**:
   - Track computational time savings
   - Measure solution quality impact
   - Find the optimal balance

7. **Document Your Approach**:
   - Record which models and weights you used
   - Document the rationale for your choices
   - Note any limitations or assumptions

Performance Considerations
--------------------------

**Computational Impact:**
- LF models can reduce solving time by 50-90%
- HF models ensure solution accuracy
- Find the right balance for your problem

**Memory Impact:**
- Multifidelity may increase memory usage
- But enables solving larger problems overall

**Solver Impact:**
- Different solvers may respond differently
- Test multifidelity with your chosen solver
- Progressive Hedging often benefits most

**Validation:**
- Always compare multifidelity solutions with HF-only baseline
- Check that key decisions are preserved
- Validate that objective values are reasonable
- Test sensitivity to model weights

Multifidelity vs Single-Fidelity
--------------------------------

**Single-Fidelity:**
- ✅ Simpler to implement
- ✅ Exact solutions
- ❌ Can be computationally expensive
- ❌ Limited by scenario count

**Multifidelity:**
- ✅ Computationally efficient
- ✅ Can handle larger problems
- ✅ Balances speed and accuracy
- ❌ More complex to set up
- ❌ Requires careful validation

Choosing the Right Approach
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Consider multifidelity when:
- Your HF model is computationally expensive
- You can create meaningful LF approximations
- You need to solve large-scale problems
- You're doing exploratory analysis

Stick with single-fidelity when:
- Your problem is already fast to solve
- You need exact scenario-level solutions
- You have a small number of scenarios
- The overhead isn't justified

Multifidelity modeling is a powerful technique in Sparow that can significantly improve the efficiency of solving complex stochastic programming problems. By understanding when and how to use multifidelity models, you can achieve substantial computational savings while maintaining solution quality.