"""
pyplate: a tool for designing chemistry experiments in plate format

Substance: An abstract chemical or biological entity (e.g., reagent, solvent, etc.).
           Immutable. 

Container: Stores specified quantities of Substances in a vessel with a given maximum volume. Immutable.

Plate: A spatially ordered collection of Containers, like a 96 well plate.
       The spatial arrangement must be rectangular. Immutable.

Recipe: A list of instructions for transforming one set of containers into another.

Storage format is defined in pyplate.yaml for volumes and moles.

    Example:
        # 1e-6 means we will store volumes as microliters
        volume_storage: 'uL'

        # 1e-6 means we will store moles as micromoles.
        moles_storage: 'umol'

All classes in this package are friends and use private methods of other classes freely.

All internal computations are rounded to config.internal_precision to maintain sanity.
    Rounding errors quickly compound.
All values returned to the user are rounded to config.precisions for ease of use.
"""

# This is necessary to instantiate the config instance; the unit tests fail without it
from pyplate.config import config, Config

from pyplate.container import Container
from pyplate.plate import Plate
from pyplate.recipe import Recipe, RecipeStep
from pyplate.substance import Substance
from pyplate.unit import Unit 
  # noqa: E402
__all__ = ['Substance', 'Container', 'Plate', 'Recipe', 'Unit', 'RecipeStep']
