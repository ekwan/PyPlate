#TODO: Add plain-english descripton/motivation for various elements of experimental design.
# Experimental Design

> **Motivaton**:  
> This portion of `pyplate` is meant to make the design of experiments more convenient. It provides classes to keep
> track of variables that change within an experiment and the creation of experiments with different conditions. 

## Glossary:  
- **Factor**: A Factor is a variable that is under the control of the experimenter.   
- **Experiment**: An Experiment represents a particular combination of Factors. Generally, Experiments are
implemented in a single well (Container) on a Plate.
- **Experimental Space**: An Experimental Space is the set of all valid Experiments given a set of Factors.
- **replicate**: When multiple Experiments have the same values across their Factors, they are considered replicates.

## Factor

A factor is a variable that is under the control of the experimenter. It has a name (must be unique to a given
experimental space), a list of possible values, and a verifier function. The verifier takes a well object and a desired 
value and returns True if the well is consistent with the description.
 
### Constructor:
```python
Factor(name: str, possible_values: list[str | float | int | Substance], verifier: callable[[Container | Plate, Any], bool])
```

### Instance Variables:

- `name`: A string with the name of the factor, names must be unique within an Experimental Space.

- `possible_values`: A list of strings, numerics, or Substances representing the possible values of the factor.

### Example
```python
def verify_substance(well: Container, expected_value: Substance):
    return expected_value in well.contents.keys()

water = Substance.solid('NaCl', 58.4428)
dmso = Substance.liquid('DMSO', 78.13, 1.1004)
triethylamine = Substance.liquid("triethylamine", mol_weight=101.19, density=0.726)

solvent_factor = Factor(name="Solvent", possible_values=[water, dmso, triethylamine], verifier=verify_substance)
temp_factor = Factor(name="Reaction Temperature", possible_values=[100, 150, 200], verifier=None)
```

## Experiment

An Experiment represents a single experiment within an experimental space. It keeps track of Factors and their 
desired values for a single run. Each experiment has a unique identifier, as well as a replicate identifier to
distinguish between Experiments conducted with the same factors in replicate. Experiments maintain a reference to the
Container they were performed in. 

Note: Experiments are not meant to be directly used, they should belong to an Experimental Space.

### Instance Variables:

- `factors`: A dictionary with factor names as keys and corresponding values.

- `experiment_id`: An identifier for the experiment. By default, it is a string representation of the factors and their 
values. Custom id generators that take an Experiment object and return a string may be supplied by the user.

- `replicate_idx`: An identifier to distinguish between repeated experiments with the same factors, by default is`experiment_id-{numeric index starting from 1}`.

- `verifier`: A function that returns a boolean value if the contents of the mapped well match the desired values for
the Factors in an Experiment

- `well`: The Container an experiment corresponds to

### Methods

- `map_well(well: Container)`: Maps `well` to this Experiment.
- `verify() -> bool`: Calls `verifier` to check that the contents of `self.well` match the values in `self.factors`

### Example
```python
water = Substance.solid('NaCl', 58.4428)
dmso = Substance.liquid('DMSO', 78.13, 1.1004)
triethylamine = Substance.liquid("triethylamine", mol_weight=101.19, density=0.726)

solvent_factor = Factor(name="Solvent", possible_values=[water, dmso, triethylamine], verifier=verify_substance)
temp_factor = Factor(name="Reaction Temperature", possible_values=[100, 150, 200], verifier=None)

exp_1 = Experiment(factors={"Solvent": water, "Reaction Temperature": 100})
```

## ExperimentalSpace

An experimental space is a collection of experiments that share the same factors. Experiments within a space may be
blocked together based on their factors use.

### Instance Variables:

- `factors`: A list of Factor objects representing the fixed and variable factors in the experimental space.

- `blocks`: A dictionary with names as keys and values as lists containing experiments representing the generated experiments.
- `experiments`: A list of all experiments registered with the space
- `experiment_id_generator`: A function that returns an identifier for a given Experiment in the space. The function will take in an `Experiment` object, and return a string that will serve as the ID for a given experiment.

### Methods:

- `generate_experiments(factors, n_replicates, block_on)`: Fully enumerates the tree of variable factors, generates experiments with well/plate indices that respect blocking rules, and stores them in the instance variable. `n_replicates` is number of replicates to be generated. If experiments with this combination of factors exist, `n_replicates` is the number of *additional* replicates to generated. `block_on` is a list of sets of factor names to block on (analogous to `GROUP BY` in SQL). Automatically adds all experiments to the space.

- `is_valid(Experiment)`: Checks if a given experiment is valid. If `generate_experiments` has run, simply checks if the experiment is in the list. Otherwise, manually checks if values are in a Factor's possible values.

- `add_experiment(Experiment)`: Manually adds an experiment to the space. Checks for validity of the experiment.

  

## Example Usage

```python

# Create Factors for all experimental conditions

f1 = Factor(name="Baking Time", possible_values=[10, 20, 30], verifier=verify_time)
f2 = Factor(name="Baking Temperature", possible_values=[300, 350, 400], verifier=verify_temperature)
f3 = Factor(name="Flavor", possible_values=["Chocolate Chip", "Oatmeal Raisin", "Peanut Butter"], verifier=verify_flavor)

# Create Experimental Space
space = ExperimentalSpace(factors=[f1, f2, f3])
space.generate_experiments(
    factors={
        "toppings": [],
        "Baking Time": [10, 30],
        "Baking Temperature": [300, 350],
        "Flavor": "all"
    },
    n_replicates=2,
    blocking_factors=["Baking Temperature", "Flavor"]
)

# returns:
[
    # block of 300 baking temperature
    [
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 300, "Flavor": "Chocolate Chip"}),
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 300, "Flavor": "Oatmeal Raisin"}),
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 300, "Flavor": "Peanut Butter"}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 300, "Flavor": "Chocolate Chip"}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 300, "Flavor": "Oatmeal Raisin"}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 300, "Flavor": "Peanut Butter"})
    ],
    
    # block of 350 baking temperature
    [
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 350, "Flavor": "Chocolate Chip"}),
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 350, "Flavor": "Oatmeal Raisin"}),
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 350, "Flavor": "Peanut Butter"}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 350, "Flavor": "Chocolate Chip"}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 350, "Flavor": "Oatmeal Raisin"}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 350, "Flavor": "Peanut Butter"})
        
    ]
]

# Add a single experiment to the space manually
space.add_experiment(Experiment(factors={"Baking Time": 20, "Baking Temperature": 350, "Flavor": "Chocolate Chip"}))
```
