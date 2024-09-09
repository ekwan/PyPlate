# Allow typing reference while still building classes
from __future__ import annotations

import warnings

from pyplate.config import config

class Substance:
    """
    An abstract chemical or biological entity (e.g., reagent, solvent, etc.). Immutable.

    Attributes:
        name: Name of substance.
        mol_weight: Molecular weight (g/mol).
        density: Density if `Substance` is a liquid (g/mL).
        concentration: Calculated concentration if `Substance` is a liquid (mol/mL).
        molecule: `cctk.Molecule` if provided.
    """

    SOLID = 1
    LIQUID = 2

    classes = {SOLID: 'Solids', LIQUID: 'Liquids'}

    def __init__(self, name: str, mol_type: int, 
                 mol_weight: float, density: float, 
                 molecule=None):
        """
        Create a new substance.

        Arguments:
            name: Name of substance.
            mol_type: Substance.SOLID or Substance.LIQUID.
            mol_weight: The molecular weight of the substance in g/mol.
            density: The density of the substance in g/mL.
            molecule: (optional) A cctk.Molecule.

        If  cctk.Molecule is provided, molecular weight will automatically populate.
        Note: Support for isotopologues will be added in the future.

        """
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")
        
        if not isinstance(mol_type, int):
            raise TypeError("Type must be an int.")
        
        if not isinstance(mol_weight, (int, float)):
            raise TypeError("Molecular weight must be a float.")
        if not isinstance(density, (int, float)):
            raise TypeError("Density must be a float.")


        if len(name) == 0:
            raise ValueError("Name must not be empty.")
        if mol_type not in Substance.classes.keys():
            #TODO: Maybe improve this error message for users
            raise ValueError("Molecular type unsupported. " + 
                             f"Type must be one of: {Substance.classes}") 
        if not mol_weight > 0:
            raise ValueError("Molecular weight must be positive.")
        if not density > 0:
            raise ValueError("Density must be positive.")

        self.name = name
        self._type = mol_type
        self.mol_weight = mol_weight
        self.density = density
        self.molecule = molecule

    def __repr__(self):
        return f"{self.name} ({'SOLID' if self.is_solid() else 'LIQUID'})"

    def __eq__(self, other):
        if not isinstance(other, Substance):
            return False
        return self.name == other.name and \
                self._type == other._type and \
                self.mol_weight == other.mol_weight and \
                self.density == other.density 

    def __hash__(self):
        return hash((self.name, self._type, self.mol_weight, self.density))

    @staticmethod
    def solid(name: str, mol_weight: float, 
              density: float = None, molecule=None) -> Substance:
        """
        Creates a solid substance.

        Arguments:
            name: Name of substance.
            mol_weight: Molecular weight in g/mol
            density: Density in g/mL. If not provided, a warning will be raised,
                     and a default value will be used.
            molecule: (optional) A cctk.Molecule

        Returns: A new solid substance with the specified properties.
        """
        if density is None:
            warning_msg = (
                f"Density not provided; using default value of {config.default_solid_density} g/mL. "
                "This may result in unexpected volumes for quantities of this substance and "
                "solutions containing it."
            )
            warnings.warn(warning_msg, stacklevel=2)
            density = config.default_solid_density
        return Substance(name, Substance.SOLID, mol_weight, density, molecule)


    @staticmethod
    def liquid(name: str, mol_weight: float, 
               density: float, molecule=None) -> Substance:
        """
        Creates a liquid substance.

        Arguments:
            name: Name of substance.
            mol_weight: Molecular weight in g/mol
            density: Density in g/mL
            molecule: (optional) A cctk.Molecule

        Returns: A new liquid substance with the specified properties.
        """
        return Substance(name, Substance.LIQUID, mol_weight, density, molecule)

    def is_solid(self) -> bool:
        """
        Return true if `Substance` is a solid.
        """
        return self._type == Substance.SOLID

    def is_liquid(self) -> bool:
        """
        Return true if `Substance` is a liquid.
        """
        return self._type == Substance.LIQUID
