################
Scenario Bundles
################

Bundling in Sparow
==================

Bundling is a powerful feature in Sparow that groups scenarios together for more efficient solving. This is particularly useful when working with large numbers of scenarios.

What is Bundling?
-----------------

Bundling combines multiple scenarios into groups (bundles) that are solved together. This reduces the computational burden while maintaining solution quality.

Key Benefits:
- **Reduced computational cost**: Fewer bundles mean fewer solver iterations
- **Maintained solution quality**: Proper bundling preserves important scenario characteristics
- **Flexible configuration**: Multiple bundling schemes for different use cases
- **Automatic validation**: Sparow ensures bundle probabilities are correct

How Bundling Works in Sparow
-----------------------------

When you initialize a model, Sparow automatically creates bundles using a default scheme (single scenario). You can customize this behavior:

.. code-block:: python

   from sparow.sp import stochastic_program

   # Initialize model with default bundling (single_scenario)
   sp.initialize_model(model_data=model_data, model_builder=builder)

   # Initialize with custom bundling scheme
   from sparow.sp.bundling.bundling_functions import kmeans_similar
   bundles = kmeans_similar(sp.model_data, models=[None], bundle_args={'num_clusters': 10})
   sp.set_bundles(bundles)

Bundle Structure
---------------

Bundles have a specific structure in Sparow:

.. code-block:: python

   bundles = {
       "bundle_1": {
           "scenarios": {
               "scenario_1": 0.5,  # Scenario probability within bundle
               "scenario_2": 0.5,
           },
           "Probability": 0.3  # Bundle probability
       },
       "bundle_2": {
           "scenarios": {
               "scenario_3": 0.4,
               "scenario_4": 0.6,
           },
           "Probability": 0.7
       }
   }

Key Components:
- **Bundle ID**: Unique identifier for each bundle (e.g., "bundle_1")
- **Scenarios**: Dictionary mapping scenario IDs to their probabilities within the bundle
- **Bundle Probability**: Overall probability of the bundle in the stochastic program

Bundling Schemes
----------------

Sparow provides several bundling schemes through the `sparow.sp.bundling` module:

Single-Fidelity Schemes
~~~~~~~~~~~~~~~~~~~~~~

**1. Single Scenario (default)**

Each scenario is treated as its own bundle. This is the simplest approach and provides the most accurate results:

.. code-block:: python

   from sparow.sp.bundling.bundling_functions import single_scenario

   # Each scenario becomes its own bundle
   bundles = single_scenario(data, models, bundle_args)

Use when:
- You have a small number of scenarios
- You need exact scenario-level solutions
- Scenarios are highly distinct

**2. Single Bundle**

All scenarios are combined into one bundle. This is the most aggressive bundling:

.. code-block:: python

   from sparow.sp.bundling.bundling_functions import single_bundle

   # All scenarios in one bundle
   bundles = single_bundle(data, models, bundle_args)

Use when:
- You need the fastest possible solution
- Scenario differences are minimal
- You're doing initial exploration

**3. Random Bundling**

Scenarios are randomly grouped into bundles of specified size:

.. code-block:: python

   from sparow.sp.bundling.bundling_functions import sf_random

   # Randomly group scenarios into bundles of size 5
   bundles = sf_random(data, models, bundle_args={'bun_size': 5})

Parameters:
- `bun_size`: Number of scenarios per bundle

Use when:
- Scenarios have no natural grouping
- You want a simple, fast bundling approach
- Scenario characteristics are uniformly distributed

**4. K-Means Clustering**

Scenarios are grouped by similarity using k-means clustering:

.. code-block:: python

   from sparow.sp.bundling.bundling_functions import kmeans_similar

   # Group similar scenarios together
   bundles = kmeans_similar(data, models, bundle_args={'num_clusters': 10})

Parameters:
- `num_clusters`: Number of bundles to create
- `dkey`: Data key to use for clustering (default: first numeric key found)

Use when:
- Scenarios have natural groupings
- You want to preserve scenario diversity
- Scenario data has clear clusters

**5. Custom Bundle List**

Specify your own bundles:

.. code-block:: python

   from sparow.sp.bundling.bundling_functions import bundle_from_list

   # Custom bundles
   bundles = bundle_from_list(data, models, bundle_args={
       "bundles": [
           ["scen_1", "scen_2"],
           ["scen_3", "scen_4", "scen_5"]
       ]
   })

Use when:
- You have domain knowledge about scenario relationships
- You need precise control over bundling
- Default schemes don't meet your needs

Working with Bundles
--------------------

Accessing Bundle Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once bundles are created, you can inspect them:

.. code-block:: python

   # Access bundle information
   print(f"Number of bundles: {len(sp.bundles.bundle)}")

   # Iterate through bundles
   for bundle_name, bundle_data in sp.bundles.bundle.items():
       print(f"Bundle {bundle_name}:")
       print(f"  Probability: {bundle_data['Probability']}")
       print(f"  Scenarios: {list(bundle_data['scenarios'].keys())}")
       print(f"  Scenario probabilities: {bundle_data['scenarios']}")

Bundle Validation
~~~~~~~~~~~~~~~~

Sparow automatically validates bundles to ensure:
- Bundle probabilities sum to 1
- Scenario probabilities within bundles sum to 1

.. code-block:: python

   # This will raise an error if probabilities don't sum correctly
   try:
       sp.set_bundles(invalid_bundles)
   except RuntimeError as e:
       print(f"Bundle validation error: {e}")

Custom Bundling Schemes
-----------------------

Creating Custom Schemes
~~~~~~~~~~~~~~~~~~~~~~~

You can create your own bundling schemes:

.. code-block:: python

   def custom_bundling_scheme(data, models, bundle_args):
       """
       Custom bundling logic.

       Parameters
       ----------
       data : dict
           Model and scenario data
       models : list
           List of model names
       bundle_args : dict
           Custom arguments

       Returns
       -------
       dict
           Bundles in Sparow format
       """
       # Extract scenario data
       scenarios = data[models[0]]

       # Your custom bundling logic here
       bundles = {}

       # Example: Group scenarios by demand range
       low_demand = []
       high_demand = []

       for scen_id, scen_data in scenarios.items():
           if scen_data['d'] < 50:
               low_demand.append(scen_id)
           else:
               high_demand.append(scen_id)

       # Create bundles
       if low_demand:
           bundles['low_demand'] = {
               'scenarios': {s: 1.0/len(low_demand) for s in low_demand},
               'Probability': sum(scenarios[s]['Probability'] for s in low_demand)
           }

       if high_demand:
           bundles['high_demand'] = {
               'scenarios': {s: 1.0/len(high_demand) for s in high_demand},
               'Probability': sum(scenarios[s]['Probability'] for s in high_demand)
           }

       # Normalize bundle probabilities
       total_prob = sum(b['Probability'] for b in bundles.values())
       for b in bundles.values():
           b['Probability'] /= total_prob

       return bundles

Registering Custom Schemes
~~~~~~~~~~~~~~~~~~~~~~~~~~

To make your custom scheme available:

.. code-block:: python

   from sparow.sp.bundling.bundling_functions import scheme

   # Register custom scheme
   scheme["custom_demand"] = custom_bundling_scheme

   # Use custom scheme
   bundles = scheme["custom_demand"](data, models, bundle_args)

Bundle Arguments
----------------

Most bundling schemes accept additional arguments through `bundle_args`:

.. code-block:: python

   # K-means with specific number of clusters
   bundles = kmeans_similar(
       data,
       models=["model1"],
       bundle_args={
           'num_clusters': 8,
           'dkey': 'Demand',  # Specify data key for clustering
           'pkey': 'Probability'  # Specify probability key
       }
   )

   # Random bundling with specific bundle size
   bundles = sf_random(
       data,
       models=["model1"],
       bundle_args={'bun_size': 5}
   )

Common Bundle Arguments:
- `num_clusters`: Number of clusters for k-means
- `bun_size`: Bundle size for random bundling
- `dkey`: Data key to use for clustering
- `pkey`: Probability key in scenario data
- `bundles`: List of bundles for custom bundling

Practical Bundling Examples
---------------------------

Newsvendor Problem
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from sparow.sp import stochastic_program
   from sparow.sp.bundling.bundling_functions import kmeans_similar

   # Newsvendor with k-means bundling
   app_data = dict(c=1.0, b=1.5, h=0.1)

   # Demand scenarios
   model_data = {
       "scenarios": [
           {"ID": 1, "d": 15, "Probability": 0.1},
           {"ID": 2, "d": 60, "Probability": 0.6},
           {"ID": 3, "d": 72, "Probability": 0.2},
           {"ID": 4, "d": 78, "Probability": 0.05},
           {"ID": 5, "d": 82, "Probability": 0.05},
       ],
   }

   # Create stochastic program
   sp = stochastic_program(first_stage_variables=["x"])
   sp.initialize_application(app_data=app_data)

   # Use k-means bundling with 2 clusters
   bundles = kmeans_similar(
       model_data,
       models=[None],
       bundle_args={'num_clusters': 2}
   )
   sp.initialize_model(model_data=model_data, model_builder=builder)
   sp.set_bundles(bundles)

Facility Location Problem
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Facility location with custom bundling by region
   def regional_bundling(data, models, bundle_args):
       scenarios = data[models[0]]

       # Group by region
       regions = {}
       for scen_id, scen_data in scenarios.items():
           region = scen_data['region']
           if region not in regions:
               regions[region] = []
           regions[region].append(scen_id)

       # Create bundles
       bundles = {}
       for region, scens in regions.items():
           bundles[f'region_{region}'] = {
               'scenarios': {s: 1.0/len(scens) for s in scens},
               'Probability': sum(scenarios[s]['Probability'] for s in scens)
           }

       # Normalize
       total_prob = sum(b['Probability'] for b in bundles.values())
       for b in bundles.values():
           b['Probability'] /= total_prob

       return bundles

   # Apply regional bundling
   sp.set_bundles(regional_bundling(sp.model_data, [None], {}))

When to Use Different Bundling Schemes
--------------------------------------

**Single Scenario:**
- ✅ Small number of scenarios (< 50)
- ✅ Need exact scenario solutions
- ✅ Scenarios are highly distinct
- ❌ Large scenario sets (slow)

**Single Bundle:**
- ✅ Need fastest possible solution
- ✅ Scenarios are very similar
- ✅ Initial exploration
- ❌ Need scenario-level accuracy

**Random Bundling:**
- ✅ No natural scenario grouping
- ✅ Uniform scenario distribution
- ✅ Simple, fast approach needed
- ❌ Scenarios have clear clusters

**K-Means Bundling:**
- ✅ Scenarios have natural groupings
- ✅ Want to preserve diversity
- ✅ Scenario data has clear clusters
- ❌ Need exact control over bundles

**Custom Bundling:**
- ✅ Domain knowledge available
- ✅ Need precise control
- ✅ Default schemes insufficient
- ❌ No specific requirements

Best Practices for Bundling
---------------------------

1. **Start Simple**: Begin with single-scenario bundling to understand your problem
2. **Test Different Schemes**: Try k-means, random, and custom bundling
3. **Monitor Solution Quality**: Check if bundling affects your results significantly
4. **Balance Bundle Size**: Too large = less accurate, too small = inefficient
5. **Validate Probabilities**: Ensure probabilities sum correctly
6. **Consider Problem Structure**: Use domain knowledge for custom bundling
7. **Test Bundle Stability**: Try different random seeds for random bundling
8. **Document Your Approach**: Record which bundling scheme you used and why

Performance Considerations
--------------------------

**Computational Impact:**
- Fewer bundles = fewer solver iterations = faster solution
- But too few bundles may reduce solution quality
- Find the right balance for your problem

**Memory Impact:**
- Bundling reduces memory usage by grouping scenarios
- Particularly important for very large scenario sets

**Solver Impact:**
- Different solvers may respond differently to bundling
- Test bundling with your chosen solver
- Progressive Hedging often benefits from bundling

**Validation:**
- Always compare bundled solutions with unbundled baseline
- Check that key decisions are preserved
- Validate that objective values are reasonable

Bundling is a powerful tool in Sparow that can significantly improve the efficiency of solving stochastic programming problems. By understanding the different bundling schemes and when to use them, you can optimize your formulations for both solution quality and computational efficiency.