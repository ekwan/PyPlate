# Experimental Design

> **Motivaton**:  
> This portion of PyPlate is meant to make the design of experiments more convenient. It provides classes to keep
> track of variables that change within an experiment and the creation of experiments with different conditions. 
> 
> **Usage**:
> 1. Define Factors and Factor rules to be used in your experimental space.
> 2. Use `space.generate_experiments()` to automatically generate Experiments or manually add them to your space with 
> `space.add_experiment()`
> 3. Verify that all experiments in your space are consistent with your factor rules with `space.check_factor_rules()` (optional if  added with 
> `generate_experiments`)
> 4. Create Recipies to implement experiments
> 5. Use `check_well_contents` to verify that the results of your Recipies match your Experiments.

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
water = Substance.solid('NaCl', 58.4428)
dmso = Substance.liquid('DMSO', 78.13, 1.1004)
triethylamine = Substance.liquid("triethylamine", mol_weight=101.19, density=0.726)

solvent_factor = Factor(name="Solvent", possible_values=[water, dmso, triethylamine])
temp_factor = Factor(name="Reaction Temperature", possible_values=[100, 150, 200])
```

## Experiment

An Experiment represents a single experiment within an experimental space. It keeps track of Factors and their 
desired values for a single run. Each experiment has a unique identifier, as well as a replicate identifier to
distinguish between Experiments conducted with the same factors in replicate. Experiments maintain a reference to the
Container they were performed in. 

**Note**: Experiments are not meant to be directly used, they should belong to an Experimental Space.

### Constructor:
```python
Experiment(factors: dict[str, [str | Substance]], experiment_id: int, replicate_idx: int,
             well: Optional[Container] = None):
```

### Instance Variables:

- `factors`: A dictionary with factor names as keys and corresponding values.

- `experiment_id`: An identifier for the experiment. By default, it is a string representation of the factors and their 
values. Custom id generators that take an Experiment object and return a string may be supplied by the user.

- `replicate_idx`: An identifier to distinguish between repeated experiments with the same factors, by default is`experiment_id-{numeric index starting from 1}`.

- `verifier`: A function that returns a boolean value if the contents of the mapped well match the desired values for
the Factors in an Experiment

- `well`: The Container an experiment corresponds to

### Methods

- `map_well(well: Container)`: Maps `well` to this Experiment. Generally for internal use.
- `check_well()`: Calls `verifier` to check that the contents of `self.well` match the values in `self.factors`

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

### Constructor:
```python
ExperimentalSpace(factors: set[Factor], experiment_id_generator: callable, factor_rules: callable)
```

### Instance Variables:

- `factors`: A list of Factor objects representing the fixed and variable factors in the experimental space.

- `blocks`: A dictionary with names as keys and values as lists containing experiments representing the generated experiments.
- `experiments`: A list of all experiments registered with the space
- `experiment_id_generator`: A function that returns an identifier for a given Experiment in the space. The function will take in an `Experiment` object, and return a string that will serve as the ID for a given experiment.
- `factor_rules`: A function that accepts an Experiment and ensures that its factors don't conflict with each other (user-defined)

### Methods:

- `generate_experiments(factors, n_replicates, block_on)`: Fully enumerates the tree of variable factors, and generates 
experiments consistent with Factor and block rules. `n_replicates` is number of replicates to be generated. If
experiments with this combination of factors exist, `n_replicates` is the number of *additional* replicates to generated.
`block_on` is a list of sets of factor names to block on (analogous to `GROUP BY` in SQL). Generated experiments are
guaranteed to be consistent with factor rules.

- `add_experiment(Experiment)`: Manually adds an experiment to the space.

- `check_factor_rules()`: Verifies that all experiments in the space follow `factor_rules`

- `check_well_contents()`: Ensures that the contents of the wells mapped to all experiments in the space match expected
contents 
  

## Example Usage

```python

# Create Factors for all experimental conditions

f1 = Factor(name="Baking Time", possible_values=[10, 20, 30])
f2 = Factor(name="Baking Temperature", possible_values=[300, 350, 400])
f3 = Factor(name="Flavor", possible_values=["Chocolate Chip", "Oatmeal Raisin", "Peanut Butter"])
f4 = Factor(name="Sugar", possible_values=[5, 10, 15])

def cookie_rules(experiment):
    return not (experiment["Flavor"] == "Oatmeal Raisin" and experiment["Sugar"] == 5)

# Create Experimental Space
space = ExperimentalSpace(factors=[f1, f2, f3, f4])
space.generate_experiments(
    factors={
        "Baking Time": [10, 30],
        "Baking Temperature": [300, 350],
        "Flavor": "all",
        "Sugar": [5, 10]
    },
    n_replicates=2,
    blocking_factors=["Baking Temperature"]
)

# returns:
[
    # Note that no Oatmeal Raisins are generated with a Sugar of 5
    # block of 300 baking temperature
    [
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 300, "Flavor": "Chocolate Chip", "Sugar": 5}),
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 300, "Flavor": "Peanut Butter", "Sugar": 5}),
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 300, "Flavor": "Chocolate Chip", "Sugar": 10}),
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 300, "Flavor": "Oatmeal Raisin", "Sugar": 10}),
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 300, "Flavor": "Peanut Butter", "Sugar": 10}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 300, "Flavor": "Chocolate Chip", "Sugar": 5}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 300, "Flavor": "Peanut Butter", "Sugar": 5}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 300, "Flavor": "Chocolate Chip", "Sugar": 10}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 300, "Flavor": "Oatmeal Raisin", "Sugar": 10}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 300, "Flavor": "Peanut Butter", "Sugar": 10})
        
    ],
    # block of 300 baking temperature
    [
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 350, "Flavor": "Chocolate Chip", "Sugar": 5}),
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 350, "Flavor": "Peanut Butter", "Sugar": 5}),
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 350, "Flavor": "Chocolate Chip", "Sugar": 10}),
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 350, "Flavor": "Oatmeal Raisin", "Sugar": 10}),
        Experiment(factors={"Baking Time": 10, "Baking Temperature": 350, "Flavor": "Peanut Butter", "Sugar": 10}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 350, "Flavor": "Chocolate Chip", "Sugar": 5}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 350, "Flavor": "Peanut Butter", "Sugar": 5}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 350, "Flavor": "Chocolate Chip", "Sugar": 10}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 350, "Flavor": "Oatmeal Raisin", "Sugar": 10}),
        Experiment(factors={"Baking Time": 30, "Baking Temperature": 350, "Flavor": "Peanut Butter", "Sugar": 10})
    ],
]
    
# Add a single experiment to the space manually
space.add_experiment(Experiment(factors={
    "Baking Time": 20, "Baking Temperature": 350, "Flavor": "Chocolate Chip", "Sugar": 5
}))
```
