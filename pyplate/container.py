# Allow typing reference while still building classes
from __future__ import annotations

from typing import Iterable, Tuple, Dict, TYPE_CHECKING

from functools import cache
from copy import deepcopy, copy

import numpy as np
import pandas
from tabulate import tabulate

from pyplate.config import config
from pyplate.substance import Substance
from pyplate.unit import Unit

# Allows for proper type checking of Plate and PlateSlicer parameters without
# creating circular references during module loading
if TYPE_CHECKING:
    from pyplate.plate import Plate, PlateSlicer
else:
    Plate = PlateSlicer = None

class Container:
    """
    Stores specified quantities of Substances in a vessel with a given maximum volume. Immutable.

    Attributes:
        name: Name of the Container.
        contents: A dictionary of Substances to floats denoting how much of each Substance is the Container.
        volume: Current volume held in the Container in storage format.
        max_volume: Maximum volume Container can hold in storage format.
    """

    def __init__(self, name: str, max_volume: str = 'inf L',
                 initial_contents: Iterable[Tuple[Substance, str]] = None):
        """
        Create a Container.

        Arguments:
            name: Name of container
            max_volume: Maximum volume that can be stored in the container in mL
            initial_contents: (optional) Iterable of tuples of the form (Substance, quantity)
        """
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")
        if len(name) == 0:
            raise ValueError("Name must not be empty.")

        if not isinstance(max_volume, str):
            raise TypeError("Maximum volume must be a str, ('10 mL').")
        max_volume, _ = Unit.parse_quantity(max_volume)
        if max_volume <= 0:
            raise ValueError("Maximum volume must be positive.")
        self.name = name
        self.contents: Dict[Substance, float] = {}
        self.volume = 0.0
        self.max_volume = Unit.convert_to_storage(max_volume, 'L')
        self.experimental_conditions = {}
        if initial_contents:
            if not isinstance(initial_contents, Iterable):
                raise TypeError("Initial contents must be iterable.")
            for entry in initial_contents:
                if not isinstance(entry, Iterable) or not len(entry) == 2:
                    raise TypeError("Element in initial_contents must be a (Substance, str) tuple.")
                substance, quantity = entry
                if not isinstance(substance, Substance) or not isinstance(quantity, str):
                    raise TypeError("Element in initial_contents must be a (Substance, str) tuple.")
                self._self_add(substance, quantity)
            contents = []
            for substance, quantity in self.contents.items():
                quantity, unit = Unit.convert_from_storage_to_standard_format(substance, quantity)
                precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                contents.append(f"{round(quantity, precision)} {unit} of {substance.name}")
            self.instructions = f"Add {', '.join(contents)}"
            if self.max_volume != float('inf'):
                unit = "L"
                max_volume = Unit.convert_from_storage(self.max_volume, unit) # TODO: Add back in a "standard format"
                precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                self.instructions += f" to a {round(max_volume, precision)} {unit} container."
            else:
                self.instructions += " to a container."
        else:
            if self.max_volume != float('inf'):
                unit = "L"
                max_volume = Unit.convert_from_storage(self.max_volume, unit) # TODO: Add back in a "standard format"
                precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                self.instructions = f"Create a {round(max_volume, precision)} {unit} container."
            else:
                self.instructions = "Create a container."

    def __eq__(self, other):
        if not isinstance(other, Container):
            return False
        return self.name == other.name and self.contents == other.contents and \
            self.volume == other.volume and self.max_volume == other.max_volume

    def __hash__(self):
        return hash((self.name, self.volume, self.max_volume, *tuple(map(tuple, self.contents.items()))))

    def _self_add(self, source: Substance, quantity: str) -> None:
        """

        Adds `Substance` to current `Container`, mutating it.
        Only to be used in the constructor and immediately after copy.

        Arguments:
            source: Substance to add.
            quantity: How much to add. ('10 mol')

        """
        if not isinstance(source, Substance):
            raise TypeError("Source must be a Substance.")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")

        volume_to_add = Unit.convert(source, quantity, config.volume_storage_unit)
        amount_to_add = Unit.convert(source, quantity, config.moles_storage_unit)
        if self.volume + volume_to_add > self.max_volume:
            raise ValueError("Exceeded maximum volume")
        self.volume = round(self.volume + volume_to_add, config.internal_precision)
        self.contents[source] = round(self.contents.get(source, 0) + amount_to_add, config.internal_precision)

    def _transfer(self, source_container: Container, quantity: str) -> Tuple[Container, Container]:
        """
        Move quantity ('10 mL', '5 mg') from container to self.

        Arguments:
            source_container: `Container` to transfer from.
            quantity: How much to transfer.

        Returns: New source and destination container.
        """

        if not isinstance(source_container, Container):
            raise TypeError("Invalid source type.")
        quantity_to_transfer, unit = Unit.parse_quantity(quantity)

        if unit == 'L':
            volume_to_transfer = Unit.convert_to_storage(quantity_to_transfer, 'L')
            volume_to_transfer = round(volume_to_transfer, config.internal_precision)

            if volume_to_transfer > source_container.volume:
                raise ValueError(f"Not enough mixture left in source container ({source_container.name}). " +
                                 f"Only {Unit.convert_from_storage(source_container.volume, 'mL')} mL available, " +
                                 f"{Unit.convert_from_storage(volume_to_transfer, 'mL')} mL needed.")
            ratio = volume_to_transfer / source_container.volume

        elif unit == 'g':
            mass_to_transfer = round(quantity_to_transfer, config.internal_precision)
            total_mass = 0
            for substance, amount in source_container.contents.items():
                total_mass += Unit.convert_from(substance, amount, config.moles_storage_unit, "g")
            ratio = mass_to_transfer / total_mass
        elif unit == 'mol':
            moles_to_transfer = Unit.convert_to_storage(quantity_to_transfer, 'mol')
            total_moles = sum(amount for _, amount in source_container.contents.items())
            ratio = moles_to_transfer / total_moles
        else:
            raise ValueError("Invalid quantity unit.")

        source_container, to = deepcopy(source_container), deepcopy(self)
        for substance, amount in source_container.contents.items():
            to_transfer = amount * ratio
            to.contents[substance] = round(to.contents.get(substance, 0) + to_transfer,
                                           config.internal_precision)
            source_container.contents[substance] = round(source_container.contents[substance] - to_transfer,
                                                         config.internal_precision)
            # if quantity to remove is the same as the current amount plus a very small delta,
            # we will get a negative 0 answer.
            if source_container.contents[substance] == -0.0:
                source_container.contents[substance] = 0.0
        if source_container.has_liquid():
            transfer = Unit.convert_from_storage(ratio * source_container.volume, 'L')
            transfer, unit = Unit.get_human_readable_unit(transfer, 'L')
        else:
            # total mass in source container times ratio
            mass = sum(Unit.convert(substance, f"{amount} {config.moles_storage_unit}", "mg") \
                                    for substance, amount in source_container.contents.items())
            transfer, unit = Unit.get_human_readable_unit(mass * ratio, 'mg')
        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        to.instructions += f"\nTransfer {round(transfer, precision)} {unit} of {source_container.name} to {to.name}"
        to.volume = 0
        for substance, amount in to.contents.items():
            to.volume += Unit.convert(substance, f"{amount} {config.moles_storage_unit}", config.volume_storage_unit)
        to.volume = round(to.volume, config.internal_precision)
        if to.volume > to.max_volume:
            raise ValueError(f"Exceeded maximum volume in {to.name}.")
        source_container.volume = 0
        for substance, amount in source_container.contents.items():
            source_container.volume += Unit.convert(substance, f"{amount} {config.moles_storage_unit}", config.volume_storage_unit)
        source_container.volume = round(source_container.volume, config.internal_precision)

        return source_container, to

    def _transfer_slice(self, source_slice: Plate | PlateSlicer, quantity: str) -> Tuple[Plate, Container]:
        """
        Move quantity ('10 mL', '5 mg') from each well in a slice to self.

        Arguments:
            source_slice: Slice or Plate to transfer from.
            quantity: How much to transfer.

        Returns:
            A new plate and a new container, both modified.
        """
        # These lines are needed to ensure that the calls to 'is_instance()' inside this function will work correctly. 
        # By the time this function is called, the modules have already been loaded, so no circular dependencies 
        # are created.
        if not TYPE_CHECKING:
            from pyplate.plate import Plate, PlateSlicer

        def helper_func(elem):
            """ Moves volume from elem to to_array[0]"""
            elem, to_array[0] = Container.transfer(elem, to_array[0], quantity)
            return elem

        if isinstance(source_slice, Plate):
            source_slice = source_slice[:]
        if not isinstance(source_slice, PlateSlicer):
            raise TypeError("Invalid source type.")
        to = deepcopy(self)
        source_slice = copy(source_slice)
        source_slice.plate = deepcopy(source_slice.plate)

        to_array = [to]
        source_slice.apply(helper_func)
        to = to_array[0]
        return source_slice.plate, to

    @cache
    def dataframe(self) -> pandas.DataFrame:
        df = pandas.DataFrame(columns=['Volume', 'Mass', 'Moles'])
        if self.max_volume == float('inf'):
            df.loc['Maximum Volume'] = ['∞', '-', '-']
        else:
            unit = "L"
            volume = Unit.convert_from_storage(self.max_volume, unit) # TODO: Add back in a "standard format"
            volume = round(volume,
                           config.precisions[unit] if unit in config.precisions else config.precisions['default'])
            df.loc['Maximum Volume'] = [volume, '-', '-']
        totals = {'L': 0, 'g': 0, 'mol': 0}
        for substance, value in self.contents.items():
            columns = []
            for unit in ['L', 'g', 'mol']:
                converted_value = Unit.convert_from(substance, value, config.moles_storage_unit, unit)
                totals[unit] += converted_value
                converted_value, unit = Unit.get_human_readable_unit(converted_value, unit)
                precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                columns.append(f"{round(converted_value, precision)} {unit}")
            df.loc[substance.name] = columns
        columns = []
        for unit in ['L', 'g', 'mol']:
            value = totals[unit]
            value, unit = Unit.get_human_readable_unit(value, unit)
            precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
            columns.append(f"{round(value, precision)} {unit}")
        df.loc['Total'] = columns

        df.columns.name = self.name
        return df

    @cache
    def _repr_html_(self):
        return self.dataframe().to_html(notebook=True)

    @cache
    def __repr__(self):
        df = self.dataframe()
        return tabulate(df, headers=[self.name] + list(df.columns), tablefmt='pretty')

    @cache
    def has_liquid(self) -> bool:
        """
        Returns: True if any substance in the container is a liquid.
        """
        return any(substance.is_liquid() for substance in self.contents)

    @cache
    def get_substances(self):
        """

        Returns: A set of substances present in the container.

        """
        return set(self.contents.keys())

    def _add(self, source: Substance, quantity: str) -> Container:
        """
        Add the given quantity ('10 mol') of the source substance to the container.

        Arguments:
            source: Substance to add to `destination`.
            quantity: How much `Substance` to add.

        Returns:
            A new container with added substance.
        """
        destination = deepcopy(self)
        destination._self_add(source, quantity)
        return destination

    @staticmethod
    def transfer(source: Container | Plate | PlateSlicer, destination: Container, quantity: str) \
            -> Tuple[Container | Plate | PlateSlicer, Container]:
        """
        Move quantity ('10 mL', '5 mg') from source to destination container,
        returning copies of the objects with amounts adjusted accordingly.

        Arguments:
            source: Container, plate, or slice to transfer from.
            destination: Container to transfer to:
            quantity: How much to transfer.

        Returns:
            A tuple of (T, Container) where T is the type of the source.
        """
        # These lines are needed to ensure that the calls to 'is_instance()' inside this function will work correctly. 
        # By the time this function is called, the modules have already been loaded, so no circular dependencies 
        # are created.
        if not TYPE_CHECKING:
            from pyplate.plate import Plate, PlateSlicer
        
        if not isinstance(destination, Container):
            raise TypeError("You can only use Container.transfer into a Container")
        if isinstance(source, Container):
            return destination._transfer(source, quantity)
        if isinstance(source, (Plate, PlateSlicer)):
            return destination._transfer_slice(source, quantity)
        raise TypeError("Invalid source type.")

    def get_concentration(self, solute: Substance, units: str = 'M') -> float:
        """
        Get the concentration of solute in the current solution.

        Args:
            solute: Substance interested in.
            units: Units to return concentration in, defaults to Molar.

        Returns: Concentration

        """
        if not isinstance(solute, Substance):
            raise TypeError("Solute must be a Substance.")
        if not isinstance(units, str):
            raise TypeError("Units must be a str.")

        mult, *units = Unit.parse_concentration('1 ' + units)

        numerator = Unit.convert_from(solute, self.contents.get(solute, 0), config.moles_storage_unit, units[0])

        if numerator == 0:
            return 0

        if units[1].endswith('L'):
            denominator = self.get_volume(units[1])
        else:
            denominator = 0
            for substance, amount in self.contents.items():
                denominator += Unit.convert_from(substance, amount, config.moles_storage_unit, units[1])

        return round(numerator / denominator / mult, config.internal_precision)

    def get_volume(self, unit: str = None) -> float:
        """
        Get the volume of the container.

        Args:
            unit: Unit to return volume in. Defaults to volume_display_unit from config.

        Returns: Volume of the container.

        """
        if unit is None:
            unit = config.volume_display_unit

        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")

        return Unit.convert_from_storage(self.volume, unit)

    @staticmethod
    def create_solution(solute: Substance | Iterable[Substance], solvent: Substance | Container,
                        name: str = None, **kwargs) -> Container:
        """
        Create a solution.

        Two out of concentration, quantity, and total_quantity must be specified.

        Multiple solutes can be, optionally, provided as a list. Each solute will have the desired concentration
        or quantity in the final solution.

        If one value is specified for concentration or quantity and multiple solutes are provided, the value will be
        used for all solutes.

        Arguments:
            solute: What to dissolve. Can be a single Substance or a list of Substances.
            solvent: What to dissolve with. Can be a Substance or a Container.
            name: Optional name for new container.
            concentration: Desired concentration(s). ('1 M', '0.1 umol/10 uL', etc.)
            quantity: Desired quantity of solute(s). ('3 mL', '10 g')
            total_quantity: Desired total quantity. ('3 mL', '10 g')


        Returns:
            New container with desired solution.
        """

        if not isinstance(solvent, (Substance, Container)):
            raise TypeError("Solvent must be a Substance or a Container.")
        if name and not isinstance(name, str):
            raise TypeError("Name must be a str.")

        if isinstance(solute, Substance):
            solute = [solute]
        elif not isinstance(solute, list) or any(not isinstance(substance, Substance) for substance in solute):
            raise TypeError("Solute(s) must be a Substance.")

        concentration = kwargs.get('concentration', None)
        quantity = kwargs.get('quantity', None)
        total_quantity = kwargs.get('total_quantity', None)

        original_solvent = solvent
        if isinstance(solvent, Container):
            # Calculate mol_weight and density of solvent
            # get total mass of solvent
            total_mass = sum(Unit.convert_from(substance, amount, 'mol', 'g')
                             for substance, amount in solvent.contents.items())
            total_moles = Unit.convert_from_storage(sum(solvent.contents.values()), 'mol')
            total_volume = solvent.get_volume('mL')
            if total_moles == 0 or total_volume == 0:
                raise ValueError("Solvent must contain a non-zero amount of substance.")
            # mol_weight = g/mol, density = g/mL
            solvent = Substance.liquid('fake solvent',
                                       mol_weight=total_mass / total_moles, density=total_mass / total_volume)

        if (concentration is not None) + (quantity is not None) + (total_quantity is not None) != 2:
            raise ValueError("Must specify two values out of concentration, quantity, and total quantity.")

        if total_quantity and not isinstance(total_quantity, str):
            raise TypeError("Total quantity must be a str.")

        if not name:
            name = f"Solution of {','.join(substance.name for substance in solute)} in {solvent.name}"

        def convert_one(substance: Substance, u: str) -> float:
            """ Converts 1 mol or U to unit `u` for a given substance. """
            return Unit.convert_from(substance, 1, 'mol', u)

        # result of linalg.solve will be moles (or 'U') for all solutes solvent

        n = len(solute)
        a = np.zeros((n * 2, n + 1), dtype=float)
        b = np.zeros(n * 2, dtype=float)
        index = 0
        identity = np.identity(n + 1)[0]
        if concentration is not None:
            if isinstance(concentration, str):
                concentration = [concentration] * len(solute)
            elif not isinstance(concentration, Iterable):
                raise TypeError("Concentration(s) must be a str.")

            if len(concentration) != n:
                raise ValueError("Number of concentrations must match number of solutes.")

            bottom_arrays = {}
            for i, (c, substance) in enumerate(zip(concentration, solute)):
                if not isinstance(c, str):
                    raise TypeError("Concentration(s) must be a str.")
                try:
                    c, numerator, denominator = Unit.parse_concentration(c)
                except ValueError:
                    raise ValueError(f"Invalid concentration. ({c})")

                if denominator not in bottom_arrays:
                    bottom = np.array(list(convert_one(substance, denominator) for substance in solute + [solvent]))
                    bottom_arrays[denominator] = bottom
                else:
                    bottom = bottom_arrays[denominator]

                # c = top/bottom
                a[index] = c * bottom - np.roll(identity, i) * convert_one(substance, numerator)
                index += 1

        if quantity is not None:
            if isinstance(quantity, str):
                quantity = [quantity] * len(solute)
            elif not isinstance(quantity, Iterable):
                raise TypeError("Quantity(s) must be a str.")

            if len(quantity) != n:
                raise ValueError("Number of quantities must match number of solutes.")

            for i, (q, substance) in enumerate(zip(quantity, solute)):
                if not isinstance(q, str):
                    raise TypeError("Quantity(s) must be a str.")
                q, unit = Unit.parse_quantity(q)
                a[index] = np.roll(identity, i) * convert_one(substance, unit)
                b[index] = q
                index += 1

        if total_quantity is not None:
            total_quantity, total_quantity_unit = Unit.parse_quantity(total_quantity)
            a[index] = np.array(
                list(convert_one(substance, total_quantity_unit) for substance in solute + [solvent]))
            b[index] = total_quantity

        xs = np.linalg.solve(a[:n + 1], b[:n + 1])
        if any(x <= 0 for x in xs):
            raise ValueError("Solution is impossible to create.")

        for i in range(len(a)):
            if abs(sum(a[i] * xs) - b[i]) > 1e-6:
                raise ValueError("Solution is impossible to create.")

        initial_contents = list((substance, f"{x} mol") for x, substance in zip(xs, solute + [solvent]))
        if isinstance(original_solvent, Container):
            result = Container(name, initial_contents=initial_contents[:-1])
            contents = []
            for substance, value in result.contents.items():
                value, unit = Unit.convert_from_storage_to_standard_format(substance, value)
                precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                contents.append(f"{round(value, precision)} {unit} of {substance.name}")
            _, solvent_amount = initial_contents[-1]
            solvent_volume = Unit.convert_from(solvent, xs[-1], 'mol', 'L')
            solvent_volume, volume_unit = Unit.get_human_readable_unit(solvent_volume, 'L')
            solvent_volume = round(solvent_volume,
                                   config.precisions[volume_unit] if volume_unit in config.precisions else
                                   config.precisions['default'])

            original_solvent, result = Container.transfer(original_solvent, result, solvent_amount)
            result.instructions = ("Add " + ", ".join(contents) +
                                   f" to {solvent_volume} {volume_unit} of {original_solvent.name}.")
            return original_solvent, result
        else:
            result = Container(name, initial_contents=initial_contents)
            contents = []
            for substance, value in result.contents.items():
                value, unit = Unit.convert_from_storage_to_standard_format(substance, value)
                precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                contents.append(f"{round(value, precision)} {unit} of {substance.name}")
            result.instructions = "Add " + ", ".join(contents) + " to a container."
            return result

    @staticmethod
    def _dilute_to_quantity(source: Container, solute: Substance, concentration: str, solvent: Substance | Container,
                            quantity: str, name=None) -> (Tuple[Container, Container] |
                                                            Tuple[Container, Container, Container]):
        """
        Create a diluted solution from an existing solution or solutions.


        Arguments:
            source: Solution to dilute.
            solute: What to dissolve.
            concentration: Desired concentration. ('1 M', '0.1 umol/10 uL', etc.)
            solvent: What to dissolve with (if it is a Container, it can contain some solute).
            quantity: Desired total quantity. ('3 mL', '10 g')
            name: Optional name for new container.

        Returns:
            Residual from the source container (and possibly the solvent container)
             and a new container with the desired solution.

        Raises:
            ValueError: If the solution is impossible to create.
        """

        if not isinstance(source, Container):
            raise TypeError("Source must be a Container.")
        if not isinstance(solute, Substance):
            raise TypeError("Solute must be a Substance.")
        if not isinstance(concentration, str):
            raise TypeError("Concentration must be a str.")
        if not isinstance(solvent, (Substance, Container)):
            raise TypeError("Solvent must be a Substance or Container.")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")
        if name and not isinstance(name, str):
            raise TypeError("Name must be a str.")

        quantity_value, quantity_unit = Unit.parse_quantity(quantity)
        if quantity_value <= 0:
            raise ValueError("Quantity must be positive.")

        if solute not in source.contents:
            raise ValueError(f"Source container does not contain {solute.name}.")

        if solvent == solute:
            raise ValueError("Solute and solvent must be different.")

        if not name:
            name = f"solution of {solute.name} in {solvent.name}"

        # x is amount of source solution in mL, y is amount of solvent in mL
        mass = sum(Unit.convert_from(substance, value, config.moles_storage_unit, 'g') for substance, value in
                   source.contents.items())
        moles = sum(Unit.convert_from(substance, value, config.moles_storage_unit, 'mol') for substance, value in
                    source.contents.items())
        volume = Unit.convert_from_storage(source.volume, 'mL')
        d_x = mass / volume
        mw_x = mass / moles
        m_x = Unit.convert_from_storage(source.contents.get(solute, 0), 'mol') / (volume / 1000)

        if isinstance(solvent, Container):
            mass = sum(Unit.convert_from(substance, value, config.moles_storage_unit, 'g') for substance, value in
                       solvent.contents.items())
            moles = sum(Unit.convert_from(substance, value, config.moles_storage_unit, 'mol') for substance, value in
                        solvent.contents.items())
            volume = Unit.convert_from_storage(solvent.volume, 'mL')
            d_y = mass / volume
            mw_y = mass / moles
            m_y = Unit.convert_from_storage(solvent.contents.get(solute, 0), 'mol') / (volume / 1000)
        else:
            d_y = solvent.density
            mw_y = solvent.mol_weight
            m_y = 0  # no solute in solvent

        mw_s = solute.mol_weight
        d_s = solute.density

        concentration, numerator, denominator = Unit.parse_concentration(concentration)
        a = np.array([[0., 0.], [0., 0.]])
        b = np.array([0., 0.])

        if numerator == 'mol':
            top = np.array([m_x / 1000., m_y / 1000.])
        elif numerator == 'g':
            top = np.array([m_x * mw_s / 1000., m_y * mw_s / 1000.])
        elif numerator == 'L':
            # (mL/1000) * mol/L * g/mol * mL/g = mL / 1000 = L
            top = np.array([m_x * mw_s / (d_s * 1e6), m_y * mw_s / (d_s * 1e6)])
        else:
            raise ValueError("Invalid numerator.")
        if denominator == 'mol':
            bottom = np.array([d_x / mw_x, d_y / mw_y])
        elif denominator == 'g':
            bottom = np.array([d_x, d_y])
        elif denominator == 'L':
            bottom = np.array([1 / 1000., 1 / 1000.])
        else:
            raise ValueError("Invalid denominator.")

        # concentration = top / bottom -> concentration * bottom - top = 0
        a[0] = concentration * bottom - top

        quantity_value, quantity_unit = Unit.parse_quantity(quantity)

        if quantity_unit == 'g':
            a[1] = np.array([d_x, d_y])
        elif quantity_unit == 'L':
            a[1] = np.array([1 / 1000., 1 / 1000.])
        elif quantity_value == 'mol':
            a[1] = np.array([d_x / mw_x, d_y / mw_y])

        b[1] = quantity_value
        x, y = np.linalg.solve(a, b)
        if x < 0 or y < 0:
            raise ValueError("Solution is impossible to create.")

        if isinstance(solvent, Substance):
            if y:
                new_solution = Container(name, initial_contents=[(solvent, f"{y} mL")])
            else:
                new_solution = Container(name)
            if x:
                source, new_solution = Container.transfer(source, new_solution, f"{x} mL")
        else:
            new_solution = Container(name)
            if x:
                source, new_solution = Container.transfer(source, new_solution, f"{x} mL")
            if y:
                solvent, new_solution = Container.transfer(solvent, new_solution, f"{y} mL")

        precision = config.precisions['mL'] if 'mL' in config.precisions else config.precisions['default']
        new_solution.instructions = f"Add {round(y, precision)} mL of {solvent.name} to" + \
                                    f" {round(x, precision)} mL of {source.name}."

        if isinstance(solvent, Substance):
            return source, new_solution
        else:
            return source, solvent, new_solution

    def remove(self, what: (Substance | int) = Substance.LIQUID) -> Container:
        """
        Removes substances from `Container`

        Arguments:
            what: What to remove. Can be a type of substance or a specific substance. Defaults to LIQUID.

        Returns: New Container with requested substances removed.

        """
        new_container = deepcopy(self)
        new_container.contents = {substance: value for substance, value in self.contents.items()
                                  if what not in (substance._type, substance)}
        new_container.volume = 0
        for substance, value in new_container.contents.items():
            new_container.volume += Unit.convert_from(substance, value, config.moles_storage_unit, config.volume_storage_unit)

        new_container.instructions = self.instructions
        classes = {Substance.SOLID: 'solid', Substance.LIQUID: 'liquid'}
        if what in classes:
            new_container.instructions += f"Remove all {classes[what]}s."
        else:
            new_container.instructions += f"Remove all {what.name}s."
        return new_container

    def dilute(self, solute: Substance, concentration: str, solvent: (Substance | Container),
               quantity=None, name=None) -> Container:
        """
        Dilutes `solute` in solution to `concentration`.

        Args:
            solute: Substance which is subject to dilution.
            concentration: Desired concentration.
            solvent: What to dilute with. Can be a Substance or a Container.
            quantity: Optional total quantity of solution.
            name: Optional name for new container.

        Returns: A new (updated) container with the remainder of the original container, and the diluted solution.

        If solvent is a container, the remainder of the solvent will also be returned.

        """
        if not isinstance(solute, Substance):
            raise TypeError("Solute must be a Substance.")
        if not isinstance(concentration, str):
            raise TypeError("Concentration must be a str.")
        if not isinstance(solvent, Substance) and not isinstance(solvent, Container):
            raise TypeError("Solvent must be a substance or container.")
        if name and not isinstance(name, str):
            raise TypeError("New name must be a str.")
        if solute not in self.contents:
            raise ValueError(f"Container does not contain {solute.name}.")

        if quantity is not None:
            return self._dilute_to_quantity(self, solute, concentration, solvent, quantity, name)

        new_ratio = Unit.calculate_concentration_ratio(solute, concentration, solvent)[0]

        current_ratio = self.contents[solute] / sum(self.contents.values())

        if new_ratio <= 0:
            raise ValueError("Solution is impossible to create.")

        if abs(new_ratio - current_ratio) <= 1e-6:
            return deepcopy(self)

        if new_ratio > current_ratio:
            raise ValueError("Desired concentration is higher than current concentration.")

        original_solvent = solvent
        if isinstance(solvent, Container):
            # Calculate mol_weight and density of solvent
            # get total mass of solvent
            total_mass = sum(Unit.convert_from(substance, amount, 'mol', 'g')
                             for substance, amount in solvent.contents.items())
            total_moles = Unit.convert_from_storage(sum(solvent.contents.values()), 'mol')
            total_volume = solvent.get_volume('mL')
            if total_moles == 0 or total_volume == 0:
                raise ValueError("Solvent must contain a non-zero amount of substance.")
            # mol_weight = g/mol, density = g/mL
            solvent = Substance.liquid('fake solvent',
                                       mol_weight=total_mass / total_moles, density=total_mass / total_volume)

        current_umoles = Unit.convert_from_storage(self.contents.get(solvent, 0), 'umol')
        required_umoles = Unit.convert_from_storage(self.contents[solute], 'umol') / new_ratio - current_umoles
        new_volume = self.volume + Unit.convert(solvent, f"{required_umoles} umol", config.volume_storage_unit)

        if new_volume > self.max_volume:
            raise ValueError("Dilute solution will not fit in container.")

        if name:
            # Note: this copies the container twice
            destination = deepcopy(self)
            destination.name = name
        else:
            destination = self

        needed_umoles = f"{required_umoles} umol"
        needed_volume = Unit.convert(solvent, needed_umoles, 'L')
        if isinstance(original_solvent, Container):
            result = Container.transfer(original_solvent, destination, f"{needed_volume} L")
        else:
            result = destination._add(solvent, needed_umoles)
        needed_volume, unit = Unit.get_human_readable_unit(needed_volume, 'L')
        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        result.instructions += f"\nDilute with {round(needed_volume, precision)} {unit} of {solvent.name}."
        return result

    def fill_to(self, solvent: Substance, quantity: str) -> Container:
        """
        Fills container with `solvent` up to `quantity`.

        Args:
            solvent: Substance to use to fill.
            quantity: Desired final quantity in container.

        Returns: New Container with desired final `quantity`

        """
        if not isinstance(solvent, Substance):
            raise TypeError("Solvent must be a Substance.")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")

        quantity, quantity_unit = Unit.parse_quantity(quantity)
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        if quantity_unit not in ('L', 'g', 'mol'):
            raise ValueError("We can only fill to mass or volume.")

        current_quantity = sum(Unit.convert(substance, f"{value} {config.moles_storage_unit}", quantity_unit)
                               for substance, value in self.contents.items())

        required_quantity = quantity - current_quantity
        result = self._add(solvent, f"{required_quantity} {quantity_unit}")
        required_volume = Unit.convert(solvent, f"{required_quantity} {quantity_unit}", 'L')
        required_volume, unit = Unit.get_human_readable_unit(required_volume, 'L')
        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        result.instructions += f"\nFill with {round(required_volume, precision)} {unit} of {solvent.name}."
        return result
