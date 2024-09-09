# Allow typing reference while still building classes
from __future__ import annotations

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
                 density:float = None, molecule=None):
        """
        Create a new substance.

        Arguments:
            name: Name of substance.
            mol_type: Substance.SOLID or Substance.LIQUID.
            molecule: (optional) A cctk.Molecule.

        If  cctk.Molecule is provided, molecular weight will automatically populate.
        Note: Support for isotopologues will be added in the future.

        """
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")
        if not isinstance(mol_type, int):
            raise TypeError("Type must be an int.")
        if len(name) == 0:
            raise ValueError("Name must not be empty.")

        self.name = name
        self._type = mol_type
        self.mol_weight = None
        self.density = density if density is not None else config.default_solid_density
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
              density: float, molecule=None) -> Substance:
        """
        Creates a solid substance.

        Arguments:
            name: Name of substance.
            mol_weight: Molecular weight in g/mol
            density: Density in g/mL
            molecule: (optional) A cctk.Molecule

        Returns: New substance.

        """
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")
        if not isinstance(mol_weight, (int, float)):
            raise TypeError("Molecular weight must be a float.")
        if not isinstance(density, (int, float)):
            raise TypeError("Density must be a float.")

        if not mol_weight > 0:
            raise ValueError("Molecular weight must be positive.")
        
        if not density > 0:
            raise ValueError("Density must be positive.")

        substance = Substance(name, Substance.SOLID, molecule)
        substance.mol_weight = mol_weight
        substance.density = density
        return substance

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

        Returns: New substance.

        """
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")
        if not isinstance(mol_weight, (int, float)):
            raise TypeError("Molecular weight must be a float.")
        if not isinstance(density, (int, float)):
            raise TypeError("Density must be a float.")

        if not mol_weight > 0:
            raise ValueError("Molecular weight must be positive.")
        if not density > 0:
            raise ValueError("Density must be positive.")

        substance = Substance(name, Substance.LIQUID, molecule)
        substance.mol_weight = mol_weight  # g / mol
        substance.density = density  # g / mL
        return substance

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
