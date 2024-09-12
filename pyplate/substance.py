# Allow typing reference while still building classes
from __future__ import annotations

import warnings

from pyplate.unit import Unit
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
            raise ValueError("Substance type unsupported. " + 
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
                self.density == other.density and \
                self.molecule == other.molecule

    def __hash__(self):
        return hash((self.name, self._type, self.mol_weight, self.density)) # pragma: no cover

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

    def convert_from(self, quantity: float, from_unit: str, 
                                            to_unit: str) -> float:
        """
        Convert quantity of substance between units.

        Arguments:
            quantity (float): The uantity of substance.
            from_unit (str): Unit to convert quantity from (e.g. 'mL').
            to_unit (str): Unit to convert quantity to (e.g. 'mol').

        Returns: 
            result (float): The converted value.
        """

        if not isinstance(quantity, (int, float)):
            raise TypeError("Quantity must be a float.")
        if not isinstance(from_unit, str):
            raise TypeError("'From unit' must be a str.")
        if not isinstance(to_unit, str):
            raise TypeError("'To unit' must be a str.")

        from_base_unit, from_mult = Unit.parse_prefixed_unit(from_unit)
        to_base_unit, to_mult = Unit.parse_prefixed_unit(to_unit)

        result = None

        match from_base_unit, to_base_unit:
            case 'g', 'g':
                result = quantity
            case 'mol', 'mol':
                result = quantity
            case 'L', 'L':
                result = quantity

            case 'g', 'mol':
                # g / (g/mol)
                result = quantity / self.mol_weight
            case 'g', 'L':
                # g / (g/mL)
                result_in_mL = quantity / self.density
                result = result_in_mL / 1000

            case 'mol', 'g':
                # mol * g/mol
                result = quantity * self.mol_weight
            case 'mol', 'L':
                # mol * g/mol / (g/mL)
                result_in_mL = quantity * self.mol_weight / self.density
                result = result_in_mL / 1000.

            case 'L', 'g':
                # L * (1000 mL/L) * g/mL
                result = quantity * 1000. * self.density
            case 'L', 'mol':
                value_in_mL = quantity * 1000.  # L * mL/L
                # mL * g/mL / (g/mol)
                result = value_in_mL * self.density / self.mol_weight

        assert result is not None, f"{self} {quantity} {from_unit} {to_unit}"

        return result * from_mult / to_mult
    

    def convert(self, quantity: str, unit: str) -> float:
        """
        Converts a quantity of this substance to different units.

        Arguments:
            quantity (str): The quantity of the substance to convert.
                                E.g. '10 mL'
            unit (str): Unit to which the quantity should be converted.
                                E.g. 'mol'

        Returns: 
            result (float): The converted value.
        """

        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a string.")
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")

        value, quantity_unit = Unit.parse_quantity(quantity)
        
        return self.convert_from(value, quantity_unit, unit)