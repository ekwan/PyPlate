
# Proposal for PyPlate Experimental Design

## Factor

Represents an experimental condition that is under the experimenter's control.

### Instance Variables:

- `name`: A string representing the name of the factor, must be unique within an Experimental Space.

- `possible_values`: A list of strings, numerics, or Substances representing the possible values of the factor.

- `verifier`: A function that takes a Well object and a possible value. It returns a boolean value if the contents of the well match the desired value provided. In addition, it verifies the provided value is in `possible_values`.

## Experiment

Represents a single experiment.

### Instance Variables:

- `factors`: A dictionary with factor names as keys and corresponding values.

- `experiment_id`: Some arbitrary identifier for the experiment, may be auto generated or specified by the user.

- `replicate_idx`: An identifier to distinguish between repeated experiments with the same factors, by default is `experiment_id-{numeric idx starting from 1}`. 

- `well`: A pointer to the `Well` an experiment corresponds to

### Methods

-`map_well(Well)`: Maps a given `Well` to this `Experiment`.


## ExperimentalSpace

Represents the experimental space, including fixed and variable factors.  

### Instance Variables:

- `factors`: A list of Factor objects representing the fixed and variable factors in the experimental space.

- `blocks`: A dictionary with names as keys and values as lists containing experiments representing the generated experiments.
-`experiments`: A list of all experiments registered with the space
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
        "Baking Time": [10, 30],
        "Baking Temperature": [300, 350],
        "Flavor": "all"
    },
    n_replicates=2,
    blocking_factors=["Baking Temperature"]
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
