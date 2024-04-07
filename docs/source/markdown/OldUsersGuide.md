# User's Guide

### Substances

A `Substance` is a solid, liquid, or enzyme:

```python
# solid
sodium_chloride = Substance.solid(name="Sodium Chloride", mol_weight=58.44)

# liquid
water = Substance.liquid(name="Water", mol_weight=18.01528, density=1.0)

# enzyme
enzyme_X = Substance.enzyme(name="Enzyme X")
```

Enzymes are like solids, but are specified in *units of activity* instead of moles.  The default density for substances is 1.0.

### Containers

A `Container` holds defined amounts of a set of `Substance`s and has a maximum volume.

Placing 10 g of NaCl in a 1 L container:

```python
sodium_chloride_stock = Container(name = "sodium_chloride_stock",
                                  max_volume = "1 L",
                                  initial_contents =
                                      [(sodium_chloride, "10 g")])
```

Making 10 mL of a 0.01 M stock solution of NaCl in water:

```python
sodium_chloride_10mM = Container.create_solution(
                           solute = sodium_chloride,
                           solvent = water,
                           concentration = "0.01 M",
                           total_quantity = "10 mL")
```

Diluting the above solute to 0.005 M:

```python
sodium_chloride_10mM, sodium_chloride_5mM = Container.create_solution_from(source=sodium_chloride_10mM, solute=sodium_chloride, concentration="5 mM", solvent=water, quantity="10 mL")
```

### Manipulating Containers

`Container`s can be diluted to a desired concentration or filled to a desired volume.

```python
salt_water = salt_water.dilute(solute=sodium_chloride_10mM, concentration='5 mM', solvent=water)
salt_water = salt_water.fill_to(solvent=water, quantity='50 mL')
```

### Creating a Plate

`Plate`s are rectangular arrays of `Container`s.

To create a generic 96 well plate:

`plate = Plate(name="test plate", max_volume_per_well="50 uL")`

Custom plates can be created with different numbers of rows and columns as well as different labels:

`plate = Plate(name="custom plate", max_volume_per_well="50 uL", rows=16, columns=24)`

or

`plate = Plate(name="custom plate", max_volume_per_well="50 uL", rows=['i', 'ii', 'iii'], columns=['a', 'b', c'])`

### Locations on a Plate and slices

PyPlate follows the `pandas` convention of having both integer- and label-based indices for referencing wells in `Plate`s.  When row or column specifiers are provided as integers, they are assumed to be integer indices (1, 2, 3, ...).  When specifiers are provided as strings, they are assumed to be label indices ("A", "B", "C", ...).

By default, rows in plates are given alphabetical labels "A", "B", "C", ... and columns in plates are given numerical labels "1", "2", "3".  However, rows and columns are always given integer indices 1, 2, 3, ....  For example, "B:3" and (2,3) both refer to well B3.

Here are some ways to refer to a specific well:

- **String Method**: "A:1"
- **Tuple Method**: ('A', 1)

You can refer to multiple wells as a list:

`plate[[('A', 1), ('B', 2), ('C', 3), 'D:4']]`


Slicing syntax is supported:


- In addition, you can provide python slices of wells with 1-based indexes:
  - `plate[:3], plate[:, :3], plate['C':], plate[1, '3':]`

### Recipes

A `Recipe` is a set of instructions for transforming one set of containers into another.

```python
plate = Plate(name='plate', max_volume_per_well='50 uL')
recipe = Recipe()
```

`Container`s and `Plate`s must be declared in the `Recipe` before use. Each object used in a recipe must be uniquely named.

```python
recipe.uses(plate)
```

It can be convenient to create solutions and declare them for use in the same step:

```python
triethylamine_50mM = recipe.create_solution(solute=triethylamine, solvent=DMSO, concentration='0.05 M', total_quantity='10.0 mL')
```

(Note that solutions made in this way are not actually created until `recipe.bake()` is called.)

Performing transfer steps:

```python
recipe.transfer(source=triethylamine_50mM, destination=plate[:3], quantity='10 uL')
```

When `recipe.bake()` is called, a dictionary of object names to resulting objects is returned (leaving the input objects, if any, unchanged.)

```
results = recipe.bake()
plate = results[plate.name]
triethylamine_50mM = results[triethylamine_50mM.name]
```


Each operation called on a recipe is stored as a step. You can retrieve the steps for a recipe using `recipe.steps`.
Each step has instructions as to what happened during the step (`step.instruction`).

### Stages

Stages are a method of breaking a recipe into addressable parts.
A recipe can be broken into stages using `start_stage(name)` and `end_stage(name)`. You must end a stage before starting a new stage. These stage names can be used for visualizations.

### Visualizations

A visualization is represented as a dataframe consisting of floats, which denotes the quantity of substances that are added to or removed from different parts of a plate during a recipe. By default, all substances are tracked, but it is possible to request tracking for a specific substance.

Visualizations can be prepared for the plates that are modified during the recipe, either for a specific recipe step or across a stage. In a recipe, each step is numbered, starting at zero. 
There are two modes for determining visualization: 'final' state and 'delta' of the changes made during the step or stage. Additionally, the unit in which the data is returned must be specified.

```
recipe.visualize(what=plate, mode='delta', timeframe=1, substance=triethylamine, unit='umol')
```
![Example Visualizations](images/example_visualization.png)

### Units

The basic units of pyplate are moles, grams, liters, and activity units. ('mol', 'g', 'L', 'U')

Any time units are required, metric prefixes may be specified. ('mg', 'umol', 'dL', ...)

All quantities are specified as strings with a value and a unit. ('1 mmol', '10 g', '10 uL' ...)

Concentration can be define in molarity, molality, or in ratio of units:
  - Examples:
    - '0.1 M'
    - '0.1 m'
    - '0.1 g/mL'
    - '0.01 umol/10 uL'
    - '5 %v/v'
    - '5 %w/v'
    - '5 %w/w'
For '%w/v', the units are defined in the configuration file.


### Configuration

Many of the default settings for PyPlate can be changed by modifying the configuration file.
The configuration file is 'pyplate.yaml' and can be located in the user's home directory, the current working 
directory of the user's project, or in a location defined by the PYPLATE_CONFIG environment variable.

The configuration file is a YAML file with the following structure:

```yaml
# How many digits of precision to maintain in internal calculations
internal_precision: 10
# How many digits of precision to return to the user
precisions:
  default: 3
  uL: 1
  umol: 1
# How to store volumes and moles internally
# uL means we will store volumes as microliters
volume_storage: uL
# umol means we will store moles as micromoles
moles_storage: umol
# density in g/mL or U/mL. Can be set to float('inf') for no density
default_density: 1
# units for %w/v
default_weight_volume_units: g/mL

# default units to be returned to the user
default_moles_unit: mol
default_volume_unit: uL

# default colormap to be used in visualizations
default_colormap: Purples
default_diverging_colormap: PuOr
```

### Building documentation

Documentation can be build by executing `make html` in the docs directory.
The resulting documentation will be in the `docs\build` folder.

### Running tests

Tests can be run by executing `pytest`.