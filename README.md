# PyPlate: Substance and Mixture Conversion Library

PyPlate is an innovative Python library designed for scientists, researchers, and enthusiasts working in chemistry and biochemistry. It provides a comprehensive set of tools to define substances, create mixtures, and handle complex conversions between different units, all within a well-structured plate format for experiments.

## Contents
- [Key Features](#key-features)
- [Installation](#installation)
- [How to Use](#how-to-use)
  - [Units](#units)
  - [Substance](#substance)
  - [Container](#container)
  - [Plate](#plate)
  - [Recipe](#recipe)
  - [PlateSlicer](#plateslicer)
- [Getting Started](#getting-started)
- [Configuration](configuration)

## Key Features

- **Substance Definition**: Easily define substances with properties such as state (solid, liquid, enzyme) and molecular weight. Each substance is treated as an immutable entity, ensuring consistency throughout your experiments.
- **Mixture Creation**: Combine different substances into mixtures and specify quantities in various units. PyPlate handles the complex backend calculations for these combinations.
- **Unit Conversion**: Seamlessly convert between different units like grams, liters, moles, molar concentrations, and arbitrary units (AUs). This feature is invaluable for maintaining accuracy in experimental protocols.
- **Plate Experiment Design**: Organize your substances and mixtures in a plate format, perfect for high-throughput screening or analysis. The library supports a spatially ordered collection of containers in a rectangular arrangement, commonly used in 96-well plates.
- **Recipe Transformation**: Not just limited to static designs, PyPlate allows you to create dynamic recipes for transforming one set of containers into another, enabling advanced experimental workflows.

## Installation

Before you start using PyPlate, you need to install it. Here's how you can install it:

\```bash
pip install pyplate
\```

## How to Use
We will need the following imports 
```python
from pyplate.slicer import Slicer

from pyplate import config
```

### Units

The 'Unit' class provides utility functions related to unit conversions, for SI prefixes and standardized units. 
The key methods include 
**convert_prefix_to_multiplier :** For converting SI prefix into its multiplier  
**parse_quantity:**  To split a quantity string into value and unit
**convert_to_unit_value :** To convert quantities into a standard unit based on substance type  
**convert_to_storage and convert_from_storage** For converting values to and from a storage format 
```python
# Converting an SI prefix to its multiplier
milli_multiplier = Unit.convert_prefix_to_multiplier("m")
print(milli_multiplier)  # Output: 0.001

# Parsing a quantity string
value, unit = Unit.parse_quantity('10 mL')
print(value, unit)  # Output: 10 mL

# Converting a quantity to its standard unit for a given substance
converted_value = Unit.convert_to_unit_value(some_substance, '50 g')
print(converted_value)  # Output: Depends on the substance type and its properties
```

### Substance
The subtance is a chemical or biological entity like a reagenet, enzyme, solvent, etc. 
#### Factory Methods:
1. **`solid`**: Creates a solid substance.
2. **`liquid`**: Creates a liquid substance.
3. **`enzyme`**: Creates an enzyme.

#### Example Usage:
```python
# Creating a solid substance
sodium_chloride = Substance.solid(name="Sodium Chloride", mol_weight=58.44)

# Creating a liquid substance
water = Substance.liquid(name="Water", mol_weight=18.01528, density=1.0)

# Creating an enzyme
enzymeX = Substance.enzyme(name="Enzyme X")
```

### Container
The container is used to store specific quantitites of substances within a vessel, which has a predefined maximum volume
#### Factory Methods:
1. **`add`**: Adds a specified substance quantity of a substance to a container
2. **`transfer`**: Transfers a specified volume from one container to another container
3. **`create_stock_solution`**: Creates a stock solution containing a solute and solvent to achieve a desired concentration
```python
# Create a stock solution
solute = Substance.solid("NaCl", 58.44)
solvent = Substance.liquid("Water", 18.01528, 1.0)
stock_solution = Container.create_stock_solution(solute, 1.0, solvent, 100.0)
```
###  Plate
A plate is an ordered collection of containters. It is similar to a 96 well plate.
Creating a new plate:
```python
plate = Plate(name="96-Well Plate", max_volume_per_well=200.0, rows=8, columns=12)
```
Adding substance to a plate
```python
# Assuming sodium_chloride is a Substance object
new_plate = Plate.add(source=sodium_chloride, destination=plate, quantity="5 mol")
```
Transferring substance between plates
```python
# Assuming flask is a Container object
transferred_plate = Plate.transfer(source=flask, destination=plate, volume="50 mL")
```
###  Recipe
The recipe is a sequence of instructions for transforming one set of containters into another. 
#### Factory methods:
1. **`uses`** Declare containers being used for the recipe. This could be a flasks, beakers etc
2. **`add`** Add a recipe to a container
3. **`transfer`** Transfer a specified volume of the recipe from one container to another
4. **`create_container`** Creates a new container with specified contents.
5. **`create_stock_solution`** Creaetes a stock solution containing a solvent and solute
6. **`bake`** This function completes all the steps that are stored in the recipe
Sample uses
```python
recipe.uses(flask, beaker)
# Assume sodium_chloride is a Substance object
recipe.add(source=sodium_chloride, destination=flask, quantity="5 mol")
# Transfer 50 mL from flask to beaker
recipe.transfer(source=flask, destination=beaker, volume="50 mL")
# Create a new container with initial contents
new_container = recipe.create_container(name="New Container", max_volume=500, initial_contents=[(sodium_chloride, "2 mol")])
# Assuming water is a Substance object
stock_solution = recipe.create_stock_solution(what=sodium_chloride, concentration=1.0, solvent=water, volume=100)
#Complete all the steps stored in the recipe
result_containers = recipe.bake()
```
###  PlateSlicer
This is used to selective access and manipulate portions of a plate to perform operations on individual cells within a plate
#### Factory Methods
1. **`add`** Adds a specified quantity of a substance to each container specified in the slice
2. **`transfer`** Transfers a specified volume from a source to each container specified by a slice


## Getting Started

Dive into PyPlate by defining substances, creating containers, and more! Here's how:

### 1. Defining Substances

```python
from pyplate import Substance

# Define a solid substance
sodium_chloride = Substance.solid(name='Sodium Chloride', mol_weight=58.44)

# Define a liquid substance
water = Substance.liquid(name='Water', mol_weight=18.01528, density=1.0)

# Define an enzyme substance
enzyme = Substance.enzyme(name='Enzyme X')
```

### 2. Creating Containers

```python
from pyplate import Container

# Create a new container named 'Solution 1' with a maximum volume of two liters
solution_1 = Container('Solution 1', max_volume='2 L')

# Creating stock containers by providing initial contents of container
sodium_chloride_stock = Container("sodium chloride", initial_contents=[(sodium_chloride, '100 g')])
water_stock = Container('water', initial_contents=[(water, '2 L')])

# Add substances to the container
sodium_chloride_stock, solution_1 = Container.transfer(sodium_chloride_stock, solution_1, '10 g')
water, solution_1 = Container.transfer(water, solution_1, '1 L')
```

### 3. Creating and manipulating solutions

Concentration can be any of "0.1 M", "0.1 m", "0.1 g/mL", "0.01 umol/10 uL", "5 %v/v", "5 %w/v", "5 %w/w"

```python
from pyplate import Container

# Create 0.1 Molar salt water
salt_water = Container.create_solution(sodium_chloride, '0.1 M', water, '10 mL')

# Dilute to 0.05 Molar
salt_water = salt_water.dilute(sodium_chloride, '0.05 M', water, name='Sodium Chloride 0.05 M Water')
# Results in 20 mL of 0.05 Molar salt water

# Create a diluted solution from another solution
salt_water_50mM, salt_water_10mM = Container.create_solution_from(salt_water, sodium_chloride, '0.01 M', water, '5 mL')
# Results in 19 mL of 0.05 Molar salt water and 5 mL of 0.01 Molar salt water

# Add enough water to make up 1 liter of solution
salt_water_1L = salt_water_50mM.fill_to(water, '1 L')

# Remove all liquids from the container.
just_sodium_chloride = salt_water_1L.remove()
# Specific substances can be removed as can classes of substances such as Substance.SOLID and Substance.ENZYME. 
```

### 4. Creating and manipulating plates

```python
from pyplate import Plate

# Create a generic 96 well plate.
plate1 = Plate('plate1', '50 uL')

# Transfer 10 uL of 0.01 M salt water to each well in the plate.
salt_water_10mM, plate1 = Plate.transfer(salt_water_10mM, plate1, '10 uL')

# Get the total volume in the plate
plate1.volume(unit='uL')
# 960.0

# Transfer 10 uL of 0.01 M salt water to the first three rows of the plate.
salt_water_10mM, plate1 = Plate.transfer(salt_water_10mM, plate1[:3], '10 uL')

# Display volumes in each well of the plate.
plate1.volumes_dataframe(unit='uL').data
#       1     2     3     4     5     6     7     8     9    10    11    12
# A  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0
# B  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0
# C  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0  20.0
# D  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0
# E  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0
# F  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0
# G  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0
# H  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0  10.0

# Fill_to and remove work on plates and slices just like containers
plate1 = plate1.fill_to(water, '40 uL')
plate1.volume(unit='uL')
# 3840.0  ==  40 uL * 96

# Fill first three columns to 50 uL
plate1 = plate1[:,:3].fill_to(water, '50 uL')
plate1.volumes_dataframe(unit='uL').data
#       1     2     3     4     5     6     7     8     9    10    11    12
# A  50.0  50.0  50.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0
# B  50.0  50.0  50.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0
# C  50.0  50.0  50.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0
# D  50.0  50.0  50.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0
# E  50.0  50.0  50.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0
# F  50.0  50.0  50.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0
# G  50.0  50.0  50.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0
# H  50.0  50.0  50.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0  40.0
```

### 5. Recipes



## Configuration

PyPlate's functionality can be enhanced with a configuration file. For example, you can specify how volumes and moles are stored using a "pyplate.yaml" file.

```yaml
volume_storage: 'uL'  # store volumes in microliters
moles_storage: 'umol'  # store moles in micromoles
```

Adjust `config.internal_precision` for computation rounding to suit the precision needs of your experiments.

