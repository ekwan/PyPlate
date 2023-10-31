# PyPlate

A Python tool for designing chemistry experiments in plate format.

### Introduction

PyPlate is an open-source Python program for designing chemistry experiments to be run in plate format. 
These experiments could be chemical reactions, calibrations for quantitation, assays, etc.
PyPlate provides a simple API for adding reagents to the plate.
After being given these user-provided instructions for creating the plate, visualizations are generated using pandas DataFrames.

### Installation

PyPlate requires Python 3.10 or later. It can be installed by typing:

`pip install pyplate-hte`

To view visualizations, you will need an interactive Python shell like Jupyter.

## How to Use

The philosophy behind PyPlate is to mimic the physical process of dispensing substances into plates as closely as possible. 
Dispensing is performed by first creating stock containers of substances and then transferring from these containers onto plates.

### Imports

From a typical design, we will need:

`from pyplate import Substance, Container, Plate`

### Substances

A Substance is a solid, liquid, or enzyme that will be used in a design.

```python
sodium_chloride = Substance.solid(name="Sodium Chloride", mol_weight=58.44)
water = Substance.liquid(name="Water", mol_weight=18.01528, density=1.0)
enzymeX = Substance.enzyme(name="Enzyme X")
```

### Containers

A Container holds substances for dispensing.

```python
sodium_chloride_stock = Container("sodium_chloride_stock", initial_contents=[(sodium_chloride, "10 g")])
empty = Container("empty", max_volume="1 L")
sodium_chloride_stock, some_sodium_chloride = Container.transfer(sodium_chloride_stock, empty, "10 mg")

sodium_chloride_10mM= Container.create_solution(sodium_chloride, "0.01 M", water, "10 mL")
sodium_chloride_10mM, sodium_chloride_5mM = Container.create_solution_from(sodium_chloride_10mM, sodium_chloride, "5 mM", water, "10 mL")
```

### Manipulating Containers

Containers can be diluted to a desired concentration or filled to a desired volume.

```python
salt_water = salt_water.dilute(sodium_chloride_10mM, '5 mM', water)
salt_water = salt_water.fill_to(water, '50 mL')
```

### Creating a Plate

To create a generic 96-well plate:

`plate = Plate("test plate", max_volume_per_well="50 uL")`

Custom plates can be created with different number of rows, columns, and different labels.

### Locations on a Plate and slices

There are a few different ways to denote locations of wells on a plate.

- In quotes with the row label followed by a colon and a column label.
  - For example: "A:1", "E:2"
- As a tuple, with a row position or label and a column position or label.
  - For example: (1, '3'), ('A', '3'), ('A', 5)
- Either of these notations can be used to list a number of wells: `plate[['A:1', (1, '3')]]`
- In addition, you can provide python slices of wells with 1-based indexes:
  - `plate[:3], plate[:, :3], plate['C':], plate[1, '3':]`

### Transfers

Amounts can be transferred between containers, plates, or slices of plates.

```python
sodium_chloride_10mM, second_container = Container.transfer(sodium_chloride_10mM, second_container, '1 mL')
sodium_chloride_10mM, plate = Container.transfer(sodium_chloride_10mM, plate[1,1], '10 uL')
plate, third_container = Plate.transfer(plate[1,1], third_container, '1 uL')
```

### Recipes

All manipulations above can be done using a recipe. When a recipe is `baked` it ensures each step in the is valid and
locks the recipe from further modification. Instructions and visualizations are provided for each step as appropriate.

```python
plate = Plate('plate', max_volume_per_well='50 uL')
recipe = Recipe()
recipe.uses(plate)
triethylamine_50mM = recipe.create_solution(triethylamine, '0.05 M', DMSO, quantity='10.0 mL')
recipe.transfer(triethylamine_50mM, plate[:3], '10 uL')
triethylamine_50mM, plate = recipe.bake()
last_step = recipe.steps[-1]
for df in last_step.visualize('destination', 'delta', 'umol'):
    display.display_html(df)
```
![Example Visualizations](images/example_visualization.png)
