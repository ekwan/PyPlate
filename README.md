# PyPlate: Substance and Mixture Conversion Library

PyPlate is an innovative Python library designed for scientists, researchers, and enthusiasts working in chemistry and biochemistry. It provides a comprehensive set of tools to define substances, create mixtures, and handle complex conversions between different units, all within a well-structured plate format for experiments.

## Key Features

- **Substance Definition**: Easily define substances with properties such as state (solid, liquid, enzyme) and molecular weight. Each substance is treated as an immutable entity, ensuring consistency throughout your experiments.
- **Container Creation**: Combine different substances into mixtures and specify quantities in various units. PyPlate handles the complex backend calculations for these combinations.
[//]: # (- **Unit Conversion**: Seamlessly convert between different units like grams, liters, moles, molar concentrations, and activity units &#40;AUs&#41;. This feature is invaluable for maintaining accuracy in experimental protocols.)
- **Plate Experiment Design**: Organize your substances and mixtures in a plate format, perfect for high-throughput screening or analysis. The library supports a spatially ordered collection of containers in a rectangular arrangement, commonly used in 96-well plates.
- **Recipe Transformation**: Not just limited to static designs, PyPlate allows you to create dynamic recipes for transforming one set of containers into another, enabling advanced experimental workflows.

## Installation

Before you start using PyPlate, you need to install it. Here's how you can install it:

```bash
pip install pyplate
```



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

### 3. Creating solutions and diluting

Concentration can be any of "0.1 M", "0.1 m", "0.1 g/mL", "0.01 umol/10 uL", "5 %v/v", "5 %w/v", "5 %w/w"

```python
from pyplate import Container

# Create 0.1 Molar salt water
salt_water = Container.create_solution(sodium_chloride, '0.1 M', water, '10 mL')

# Dilute to 0.05 Molar
salt_water = salt_water.dilute(sodium_chloride, '0.05 M', water, name='Sodium Chloride 0.05 M Water')
# Results in 20 mL of 0.05 Molar salt water

salt_water_50mM, salt_water_10mM = Container.create_solution_from(salt_water, sodium_chloride, '0.01 M', water, '5 mL')
# Results in 19 mL of 0.05 Molar salt water and 5 mL of 0.01 Molar salt water

# Add enough water to make up 1 liter of solution
salt_water_1L = salt_water_50mM.fill_to(water, '1 L')

```

## Configuration

PyPlate's functionality can be enhanced with a configuration file. For example, you can specify how volumes and moles are stored using a "pyplate.yaml" file.

```yaml
volume_storage: 'uL'  # store volumes in microliters
moles_storage: 'umol'  # store moles in micromoles
```

Adjust `config.internal_precision` for computation rounding to suit the precision needs of your experiments.
