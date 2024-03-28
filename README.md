# PyPlate

[![PyPI](https://img.shields.io/pypi/v/pyplate-hte)](https://pypi.org/project/pyplate-hte)
[![Documentation Status](https://readthedocs.org/projects/pyplate-hte/badge/?version=latest)](https://pyplate-hte.readthedocs.io/en/latest/?badge=latest)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/pyplate-hte)](https://pypi.org/project/pyplate-hte)

An open-source Python tool for high-throughput chemistry.

### Introduction

PyPlate provides tools for the design and implementation of high-throughput chemistry experiments (in particular, reaction screening).  It allows the user to define a space of experimental parameters to be explored, select points in that space for experimentation, and design liquid/solid handling steps to implement those experiments in 96 well plates.

### Installation

PyPlate requires Python 3.10 or later.

`pip install pyplate-hte`

To view plate visualizations, you will need an interactive Python shell like Jupyter.

### Philosophy

All experiments are divided into a *design* phase and an *implementation* phase.

**Design Phase**: TBD

**Implementation Phase**: PyPlate mimics the physical process of dispensing solids or liquids into plates.  `Substance`s are placed into `Container`s and dispensed into `Plate`s.  The instructions for creating a set of plates are grouped into `Recipe` objects.

- add something about how to check that the implementation and design are consistent
- All objects in PyPlate are considered immutable.

## Quick Start

```python

from pyplate import Substance, Container, Plate, Recipe

triethylamine = Substance.liquid(name="triethylamine", mol_weight=101.19, density=0.726)
DMSO = Substance.liquid(name="DMSO", mol_weight=78.13, density=1.1004)

triethylamine_50mM = Container.create_solution(solute=triethylamine, solvent=DMSO, concentration='50 mM',
                                               total_quantity='10 mL')
plate = Plate(name='plate', max_volume_per_well='50 uL')

recipe = Recipe().uses(triethylamine_50mM, plate)
recipe.transfer(source=triethylamine_50mM, destination=plate[2:7, 2:11], quantity='10 uL')
results = recipe.bake()
triethylamine_50mM = results[triethylamine_50mM.name]
plate = results[plate.name]

recipe.visualize(what=plate, mode='final', unit='uL', timeframe=0)

```

![img.png](images/simple_visualization.png)

Documentation is available at [ReadTheDocs](https://pyplate-hte.readthedocs.io/en/latest/).

## License

Licensed under the Apache License, Version 2.0 (the "License")
You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0