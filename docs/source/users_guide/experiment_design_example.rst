.. _experiment_design_example:

Cross Coupling Experiment Design Example
----------------------------------------

This example demonstrates how to design a cross coupling experiment using the experiment design features available in PyPlate. |br|

Experiment Description
======================
Suppose you have a cross-coupling reaction of the form  X + Y --> Z. |br|
You have 8 variations of coupling partner X1, X2, ..., X8 and 12 variations of coupling partner Y1, Y2, ..., Y12. |br|
Together, the full product of these would make 96 potential products Z. |br|
Additionally, let's run this reaction at 4 temperatures. |br|
|br|
This would make a total of 384 potential experiments. |br|

Factor Definition
=================
Let's create the factors for this experiment. The factors are the coupling partners X and Y, as well as the temperature we run the reaction at. |br|
|br|
The levels of the two factors are the variations of the coupling partners, and the possible temperature values respectively. |br|

::

        X_values = ['X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'X8']
        Y_values = ['Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y6', 'Y7', 'Y8', 'Y9', 'Y10', 'Y11', 'Y12']
        temp_values = [100, 200, 300, 400]
        X_factor = Factor(name='X', possible_values=X_values)
        Y_factor = Factor(name='Y', possible_values=Y_values)
        temp_factor = Factor(name='Temperature', possible_values=temp_values)

Experiment Generation
=====================
Next, let's define the Experimental Space for this experiment. |br|
|br|
In an Experimental Space, all Experiments may not be valid. In this example, let us say that X1 cannot be used at a temperature of 400.
We can restrict the generation of these experiments by defining a factor rules function that returns false for such combinations. |br|
|br|
Additionally, we'll block on the temperature factor, so that all experiments in a given block are run at the same temperature. |br|

::

        def invalid_X_temp_combo(experiment):
            if experiment['X'] == 'X1' and experiment['Temperature'] == 400:
                return False
            return True

        exp_space = ExperimentalSpace(
        factors={
            'X': "all",
            'Y': "all",
            'Temperature': [100, 200, 400]
        },
        factor_rules=invalid_X_temp_combo,
        block_on=['Temperature'])

        blocks = exp_space.generate_experiments()

We can explore the generated blocks to see the experiments that will be run. |br|
Each block can be accessed using the factor combination it was blocked upon. |br|
For example, let's examine the 200 temp block. |br|

>>> block = blocks[(200,)]
[
    Experiment(X='X1', Y='Y1', Temperature=200),
    Experiment(X='X1', Y='Y2', Temperature=200),
    Experiment(X='X1', Y='Y3', Temperature=200),
    Experiment(X='X1', Y='Y4', Temperature=200),
    ...
    Experiment(X='X8', Y='Y9', Temperature=200),
    Experiment(X='X8', Y='Y10', Temperature=200),
    Experiment(X='X8', Y='Y11', Temperature=200),
    Experiment(X='X8', Y='Y12', Temperature=200)
]

We can see that the block contains all the possible combinations of X and Y at a temperature of 200. |br|
|br|
Now, if we examine the 400 temp block, we will see that X1 is not present in the block due to the factor rules we specified earlier. |br|

>>> block = blocks[(400,)]
[
    Experiment(X='X2', Y='Y1', Temperature=400),
    Experiment(X='X2', Y='Y2', Temperature=400),
    Experiment(X='X2', Y='Y3', Temperature=400),
    Experiment(X='X2', Y='Y4', Temperature=400),
    ...
    Experiment(X='X8', Y='Y9', Temperature=400),
    Experiment(X='X8', Y='Y10', Temperature=400),
    Experiment(X='X8', Y='Y11', Temperature=400),
    Experiment(X='X8', Y='Y12', Temperature=400)
]

Manually Adding Experiments
===========================
If you have specific experiments that you want to run that were not specified in generate_experiments, you can add them to the Experimental Space manually. |br|
|br|
For example, let's say we want to run the reaction with X1 and Y1 at 300 degrees. |br|

>>> exp_space.add_experiment(Experiment(X='X1', Y='Y1', Temperature=300))

However, if you try to add an experiment that violates the factor rules, it will raise an error. |br|
|br|
For example, if you try to add the experiment X1, Y1, 400, it will raise an error. |br|

>>> exp_space.add_experiment(Experiment(X='X1', Y='Y1', Temperature=400))
ValueError: Experiment violates factor rules

This will raise an error since we have specified that X1 cannot be used at 400 degrees in our factor rules when defining the space. |br|

Implementing Experiments
========================
Once you have generated the experiments, you can implement them using the liquid handling features available in PyPlate. |br|
|br|
Let us assume the Recipes for each of the experiments has been defined, and they have been mapped to their respective Experiments. |br|
See :ref:`cross_coupling_liquid_handling` for more information on how to define and map Recipes. |br|