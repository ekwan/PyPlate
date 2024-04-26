.. _experiment_design_guide:

Experiment Design Guide
========================

PyPlate provides convenience methods to make designing experiments easier. Classes are provided to keep track of variables
that change within an experiment and to generate experiments under various conditions.

Glossary
~~~~~~~~
Factor:
    A variable under the control of the experimenter that may change across experiments.
Experiment:
   An Experiment represents a particular combination of Factors. Generally, Experiments are implemented in a single well (Container) on a Plate.
Experimental Space:
   An Experimental Space is the set of all valid Experiments given a set of Factors.

Workflow
~~~~~~~~~~~~~~~~~~~~~~~~
#. Define Factors and Factor rules to be used in your experimental space.
#. Use ``space.generate_experiments()`` to automatically generate Experiments or manually add them to your space with ``space.add_experiment()``
#. Create Recipes to implement experiments
#. Use ``check_well_contents`` to verify that the results of your Recipies match your Experiments.

Refer to :ref:`experiment_design_example` for a complete example.


Factor
------
- A factor is a variable that is under the control of the experimenter
- Factors have names which must be unique to a given experimental space and a list of possible values
- Possibles values for each Factor may include Substances, numerics, strings, or None

::

    water = Substance.solid('NaCl', 58.4428)
    dmso = Substance.liquid('DMSO', 78.13, 1.1004)
    triethylamine = Substance.liquid("triethylamine", mol_weight=101.19, density=0.726)

    solvent_factor = Factor(name="Solvent", possible_values=[water, dmso, triethylamine])
    temp_factor = Factor(name="Reaction Temperature", possible_values=[100, 150, 200])


Experiment
----------
.. note::
    Experiments are not meant to be used as a standalone object. They are meant to be used in the context of an Experimental Space.

- An Experiment represents a single experiment within an experimental space.
- It keeps track of Factors and their desired values for a single run.
- Each experiment has a unique identifier, as well as a replicate identifier to distinguish between Experiments conducted with the same factors in replicate.
- Experiments maintain a reference to the well (Container) they were performed in.

::

    water = Substance.solid('NaCl', 58.4428)
    dmso = Substance.liquid('DMSO', 78.13, 1.1004)
    triethylamine = Substance.liquid("triethylamine", mol_weight=101.19, density=0.726)

    solvent_factor = Factor(name="Solvent", possible_values=[water, dmso, triethylamine], verifier=verify_substance)
    temp_factor = Factor(name="Reaction Temperature", possible_values=[100, 150, 200], verifier=None)

    exp_1 = Experiment(factors={"Solvent": water, "Reaction Temperature": 100})

Experimental Space
------------------
- An experimental space is a collection of experiments that share the same factors
- Experiments within a space may be blocked together based on their factors use
- The generation of Experiments may be constrained by factor rules, which is a function that accepts an Experiment and ensures the factor combination is valid
- When creating an Experimental Space, you must provide a dictionary of Factors and possible values that will be used in the space, as well as a function which represents the rules for the space
- Experiments are primarily generated using the ``generate_experiments`` method, which will generate all possible experiments given a set of Factors and possible values for each Factor
- When providing possible values for a factor, the string ``"all"`` may be passed to specify all possible values for the Factor
- Additionally, when generating experiments, you may provide a list of Factors to block on, which allows for grouping of experiments by the provided Factors
- Once generated, Experiments are stored in a dictionary of lists where each block can be accessed by a tuple of the factor values for that block

::

    water = Substance.solid('NaCl', 58.4428)
    dmso = Substance.liquid('DMSO', 78.13, 1.1004)
    triethylamine = Substance.liquid("triethylamine", mol_weight=101.19, density=0.726)

    solvent_factor = Factor(name="Solvent", possible_values=[water, dmso, triethylamine], verifier=verify_substance)
    temp_factor = Factor(name="Reaction Temperature", possible_values=[100, 150, 200], verifier=None)

    def factor_rules(exp):
        if exp.factors["Solvent"] == water and exp.factors["Reaction Temperature"] == 100:
            return False
        return True

    space = ExperimentalSpace(
    factors={
        'Solvent' : "all",
        'Reaction Temperature' :    "all"
    },
    factor_rules=factor_rules
    )
    blocks = space.generate_experiments()

>>> blocks[(100,)]
[
    Experiment(factors={"Solvent": dmso, "Reaction Temperature": 100}),
    Experiment(factors={"Solvent": triethylamine, "Reaction Temperature": 100})
]

>>> blocks[(200,)]
[
    Experiment(factors={"Solvent": water, "Reaction Temperature": 200}),
    Experiment(factors={"Solvent": dmso, "Reaction Temperature": 200}),
    Experiment(factors={"Solvent": triethylamine, "Reaction Temperature": 200})
]