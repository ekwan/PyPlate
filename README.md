# PyPlate: Substance and Mixture Conversion Library

PyPlate is an innovative Python library designed for scientists, researchers, and enthusiasts working in chemistry and biochemistry. It provides a comprehensive set of tools to define substances, create mixtures, and handle complex conversions between different units, all within a well-structured plate format for experiments.

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



## Getting Started

Dive into PyPlate by defining substances, creating mixtures, and more! Here's how:

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

### 2. Creating Mixtures

```python
from pyplate import Mixture

# Create a new mixture named 'Solution 1'
solution_1 = Mixture('Solution 1')

# Add substances to the mixture
solution_1 += (sodium_chloride, '10 g')  # Adding 10 grams of Sodium Chloride
solution_1 += (water, '1 L')  # Adding 1 liter of Water
```

### 3. Converting Units

```python
# Convert grams to moles for solid substance
moles_of_sodium_chloride = sodium_chloride.convert_to_unit_value('10 g')

# Convert liters to milliliters for liquid substance
milliliters_of_water = water.convert_to_unit_value('1 L')
```

## Configuration

PyPlate's functionality can be enhanced with a configuration file. For example, you can specify how volumes and moles are stored using a "pyplate.yaml" file.

```yaml
volume_storage: 'uL'  # store volumes in microliters
moles_storage: 'umol'  # store moles in micromoles
```

Adjust `config.internal_precision` for computation rounding to suit the precision needs of your experiments.
