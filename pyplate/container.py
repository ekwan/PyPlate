# Allow typing reference while still building classes
from __future__ import annotations

from typing import Iterable, Tuple, Dict, TYPE_CHECKING

from functools import cache
from copy import deepcopy, copy

import math
import numpy as np
import pandas
from tabulate import tabulate

from pyplate.config import config
from pyplate.substance import Substance
from pyplate.unit import Unit

# Allows for proper type checking of Plate and PlateSlicer parameters without
# creating circular references during module loading
if TYPE_CHECKING:
    from pyplate.plate import Plate, PlateSlicer # pragma: no cover
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

        # Ensure name argument satisfies type and value pre-conditions
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")
        if len(name) == 0:
            raise ValueError("Name must not be empty.")
        if len(name.strip()) == 0:
            raise ValueError("Name must contain non-whitespace characters.")
        
        # Ensure max volume satisfies type requirement
        if not isinstance(max_volume, str):
            raise TypeError("Maximum volume must be a str.")
        
        # Attempt to parse max_volume argument into a quantity 
        # (raises ValueError on failure)
        max_volume, max_volume_unit = Unit.parse_quantity(max_volume)
        
        # Ensure the quantity represents a valid volume for a container
        if max_volume_unit != 'L':
            raise ValueError("Maximum volume must have volume units (e.g. L, mL, uL, etc.).")
        if not max_volume > 0:
            raise ValueError("Maximum volume must be positive.")
        
        # Set container attributes based on arguments
        self.name = name
        self.contents: Dict[Substance, float] = {}
        self.volume = 0.0
        self.max_volume = Unit.convert_to_storage(max_volume, 'L')
        self.experimental_conditions = {}

        # Set starting state of container based on the initial contents
        if initial_contents:
            # If the initial contents are not iterable, raise a type error
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

        # Check argument types
        if not isinstance(source, Substance):
            raise TypeError("Source must be a Substance.")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")

        # Parse the quantity and get the volume/amount to be added. Round to the 
        # internal precision to avoid float-precision bugs
        volume_to_add = source.convert(quantity, config.volume_storage_unit)
        volume_to_add = round(volume_to_add, config.internal_precision)

        amount_to_add = source.convert(quantity, config.moles_storage_unit)
        amount_to_add = round(amount_to_add, config.internal_precision)

        # Ensure the quantity to add is finite.
        if not math.isfinite(volume_to_add):
            raise ValueError("Cannot add a non-finite amount of a substance." + \
                            f" Quantity: {quantity}")

        # Ensure that the quantity to be transferred is either positive or zero.
        if volume_to_add < 0:
            raise ValueError("Cannot add a negative amount of a substance." + \
                             f" Quantity: {quantity}")

        # Ensure the volume to add does not exceed the maximum volume .
        if self.volume + volume_to_add > self.max_volume:
            raise ValueError("Exceeded maximum volume")
        
        # If the volume rounds to 0, return without adding anything to the 
        # container's contents.
        if round(volume_to_add, config.internal_precision) == 0:
            return

        # Set the volume to the sum of the previous volume and the new volume
        # to be added
        self.volume = round(self.volume + volume_to_add, config.internal_precision)
        
        # Adjust the container's contents to reflect the resulting amount of the
        # newly added substance
        self.contents[source] = round(self.contents.get(source, 0) + amount_to_add, 
                                      config.internal_precision)

    def _transfer(self, source_container: Container, quantity: str) -> Tuple[Container, Container]:
        """
        Move quantity ('10 mL', '5 mg') from container to self.

        Arguments:
            source_container: `Container` to transfer from.
            quantity: How much to transfer.

        Returns: New source and destination container.
        """

        # Check argument types to ensure they are correct.
        if not isinstance(source_container, Container):
            raise TypeError("Invalid source type.")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be str.")

        # Parse quantity into value-unit pair.
        quantity_to_transfer, unit = Unit.parse_quantity(quantity)

        # Ensure the quantity to add is finite.
        if not math.isfinite(quantity_to_transfer):
            raise ValueError("Cannot transfer a non-finite amount of a substance." + \
                            f" Quantity: {quantity}")

        # Ensure that the quantity to be transferred is either positive or zero.
        if quantity_to_transfer < 0:
            raise ValueError("Cannot transfer a negative amount of a substance." + \
                             f" Quantity: {quantity}")

        # Define an error raising hlper function for cases where the transfer
        # quantity exceeds the total quantity of the container's contents.
        def transfer_exceeds_contents_error_helper(container_quantity : float,
                                                   quantity_to_transfer : float,
                                                   unit : str):
            precision = config.precisions['default']
            raise ValueError( 
                    f"Not enough mixture left in source container" +
                    f"'{source_container.name}'. Only " +
                    f"{container_quantity, precision} {unit} available, but " + 
                    f"{quantity_to_transfer, precision} {unit} needed."
                    )

        # Compute the fraction of the container's total contents that will be
        # transferred (different logic for volume vs. mass vs. moles).
        #
        # NOTE: These three branches are very similar, there may be a way to 
        # refactor this into a simpler structure.
        if unit == 'L':
            # Convert the volume to transfer into storage volume units
            volume_to_transfer = Unit.convert_to_storage(quantity_to_transfer, 'L')

            # Ensure the 'volume to transfer' does not exceed the total volume 
            # of the container's current contents (round to avoid float 
            # arithmetic errors).
            volume_delta = volume_to_transfer - source_container.volume
            if round(volume_delta, config.internal_precision) > 0:
                # Get readable representation of container volume.
                container_volume, unit = Unit.get_human_readable_unit(source_container.volume, 
                                                                    config.volume_storage_unit)
                # Convert 'volume to transfer' to equivalent unit.
                volume_to_transfer = Unit.convert_from_storage(volume_to_transfer, unit)

                # Round to reading-friendly precision
                volume_to_transfer = round(volume_to_transfer, config.precisions['default'])

                # Raise error which describes the reason for the failure to transfer
                transfer_exceeds_contents_error_helper(container_volume,
                                                       volume_to_transfer, 
                                                       unit)
            
            # Compute the fraction of the container's contents that need to be
            # transferred based on the volume to transfer and the total volume
            # of the container's contents.
            ratio = min(volume_to_transfer / source_container.volume, 1)

        elif unit == 'g':
            # Round the transfer quantity to avoid float arithmetic errors.
            mass_to_transfer = round(quantity_to_transfer, config.internal_precision)

            # Compute the total mass of the container's current contents in grams.
            total_mass = 0
            for substance, amount in source_container.contents.items():
                total_mass += substance.convert_from(amount, 
                                                config.moles_storage_unit, "g")

            # Ensure the 'mass to transfer' does not exceed the total mass of
            # the container's current contents (round to avoid float arithmetic
            # errors).
            mass_delta = mass_to_transfer - total_mass
            if round(mass_delta, config.internal_precision) > 0:
                # Get readable representation of container mass.
                container_mass, new_unit = Unit.get_human_readable_unit(total_mass, 
                                                                    "g")

                # Convert 'mass to transfer' to equivalent unit.
                mass_to_transfer /= Unit.convert_prefix_to_multiplier(new_unit[:-1])

                # Round to 'reading-friendly' precision
                mass_to_transfer = round(mass_to_transfer, config.precisions['default'])

                # Raise error which describes the reason for the failure to transfer
                transfer_exceeds_contents_error_helper(container_mass,
                                                       mass_to_transfer, 
                                                       unit)

            # Compute the fraction of the container's contents that need to be
            # transferred based on the 'mass to transfer' and the total mass of
            # the container's contents.
            ratio = min(mass_to_transfer / total_mass, 1)

        elif unit == 'mol':
            # Compute the 'storage unit equivalent' for the moles to transfer.
            # E.g. if the storage units for molar amount is set to 'umol', this 
            # would multiply by 1e6
            moles_to_transfer = Unit.convert_to_storage(quantity_to_transfer, 'mol')

            # Compute the total moles of the container's current contents.
            total_moles = sum(amount for _, amount in source_container.contents.items())

            # Ensure the 'moles to transfer' does not exceed the total moles of
            # the container's current contents (round to avoid float arithmetic
            # errors).
            moles_delta = moles_to_transfer - total_moles
            if round(moles_delta, config.internal_precision) > 0:
                # Get readable representation of container moles.
                container_moles, unit = Unit.get_human_readable_unit(total_moles, 
                                                                    "mol")
                # Convert 'moles to transfer' to equivalent unit.
                moles_to_transfer /= Unit.convert_prefix_to_multiplier(unit[:-3])

                # Raise error which describes the reason for the failure to transfer
                transfer_exceeds_contents_error_helper(container_moles,
                                                       moles_to_transfer, 
                                                       unit)

            # Compute the fraction of the container's contents that need to be
            # transferred based on the 'moles to transfer' and the total moles
            # of the container's contents.
            # 
            # NOTE: This value is capped at 1 to avoid float arithmetic errors
            ratio = min(moles_to_transfer / total_moles, 1)

        # If the units are not among the base units, raise an errorr. This
        # should never be encountered in practice, as this would have been 
        # caught by the earlier call to Unit.parse_quantity().
        else:
            raise ValueError(f"Invalid quantity unit '{unit}'.")

        # Make copies of the source container and destination container which
        # will be modified based on the transfer results and returned to the
        # user
        source_container, to = deepcopy(source_container), deepcopy(self)

        # Create a list for storing substances that should be removed from the
        # source container's contents.
        substances_to_remove = []

        # Loop through each substance in the container and transfer the
        # appropriate amount of that substance
        for substance, amount in source_container.contents.items():
            # Compute the amount of the current substance that needs to be 
            # transferred to the new container
            to_transfer = amount * ratio
            
            # Compute the new amount for the substance in the destination container
            # based on the starting amount (0 if the substance was not present in
            # the destination container) and the amount to transfer (round to 
            # avoid float arithmetic errors)
            to.contents[substance] = round(to.contents.get(substance, 0) + to_transfer,
                                           config.internal_precision)

            # Compue the new amount for the substance in the source container based
            # on the starting amount and the amount to transfer
            source_container.contents[substance] = round(source_container.contents[substance] - to_transfer,
                                                         config.internal_precision)
            
            # Ensure that the contents of the source container never get below
            # zero. If so raise a ValueError. This error should never happen,
            # so it is excluded from code coverage.
            if source_container.contents[substance] < 0:
                raise ValueError(f"Transfer resulted in negative quantity of " + \
                                 f"{substance} in source container. This " + \
                                 "error should never be encountered. If you " + \
                                 "are reading this, please report the issue " + \
                                 "at https://github.com/ekwan/PyPlate/issues.") \
                                 # pragma: no cover
            
            # If all of the substance has been removed from the container, 
            # add it to the list of substances to be removed from the contents
            # of the source container
            if source_container.contents[substance] == 0.0:
                substances_to_remove.append(substance)

        # Remove all substances from the source container which were flagged
        # during the loop
        for substance in substances_to_remove:
            source_container.contents.pop(substance)

        # If the source container contains a liquid, the transfer will be recorded 
        # in terms of volume. Compute the transfer volume in reader-friendly units.
        if source_container.has_liquid():
            transfer = Unit.convert_from_storage(ratio * source_container.volume, 'L')
            transfer, unit = Unit.get_human_readable_unit(transfer, 'L')
        
        # Otherwise, the transfer will be recorded in terms of mass. Compute 
        # the transfer mass in reader-friendly units.
        else:
            # Compute the total mass by summing the masses of the individual components of the
            # original source container.
            mass = sum(substance.convert(f"{amount} {config.moles_storage_unit}", "mg") \
                                    for substance, amount in source_container.contents.items())
            
            # Compute the transfer mass as the product of the total mass of the 
            # components and the previously computed ratio.
            transfer, unit = Unit.get_human_readable_unit(mass * ratio, 'mg')

        # Report the transfer instructions in terms of unit-specific precision
        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        to.instructions += f"\nTransfer {round(transfer, precision)} {unit} of {source_container.name} to {to.name}"
        
        # Compute the total volume of the contents of the post-transfer 
        # destination container. Round to the internal precision.
        to.volume = 0
        for substance, amount in to.contents.items():
            to.volume += substance.convert(f"{amount} {config.moles_storage_unit}", config.volume_storage_unit)
        to.volume = round(to.volume, config.internal_precision)

        # If the total volume exceeds the maxmimum volume of the container,
        # raise a ValueError.
        if to.volume > to.max_volume:
            raise ValueError(f"Exceeded maximum volume in {to.name}.")
        
        # Compute the total volume of the contents of the post-transfer source
        # container. Round to the internal precision.
        source_container.volume = 0
        for substance, amount in source_container.contents.items():
            source_container.volume += substance.convert(f"{amount} {config.moles_storage_unit}", config.volume_storage_unit)
        source_container.volume = round(source_container.volume, config.internal_precision)

        # Return the post-transfer source and destination containers.
        return source_container, to

    def _transfer_slice(self, source_slice: Plate | PlateSlicer, 
                        quantity: str) -> Tuple[Plate, Container]:
        """
        Move quantity ('10 mL', '5 mg') from each well in a slice to self.

        Arguments:
            source_slice: Slice or Plate to transfer from.
            quantity: How much to transfer.

        Returns:
            A new plate and a new container, both modified.
        """
        # These lines are needed to ensure that the calls to 'isinstance()' 
        # inside this function will work correctly. By the time this function 
        # is called, the modules have already been loaded, so no circular 
        # dependencies are created.
        if not TYPE_CHECKING:
            from pyplate.plate import Plate, PlateSlicer

        def helper_func(elem):
            """ Moves volume from elem to to_array[0]"""
            elem, to_array[0] = to_array[0]._transfer(elem, quantity)
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
                converted_value = substance.convert_from(value, config.moles_storage_unit, unit)
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

    @cache
    def get_mass(self, unit: str = 'g', substance: Substance = None) -> float:
        """
        Returns the mass of the container's contents or a specific substance
        in the specified unit.
  
        Args:
            unit (str, optional): The unit in which the mass should be returned (default: 'g').
            substance (Substance, optional): The specific substance for which to retrieve the mass.
                                           If not provided, returns the total mass.
    
        Returns:
            mass (float): The mass in the specified unit.
        """
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")
        if substance is not None and not isinstance(substance, Substance):
            raise TypeError("Substance argument must be a Substance or None.")
        
        # Ensure the unit is a valid mass unit.
        if unit[-1:] != 'g':
            raise ValueError(f"Invalid mass unit '{unit}'.")

        return self.get_quantity(unit, substance)

    @cache
    def get_moles(self, unit: str = 'mol', substance: Substance = None) -> float:
        """
        Returns the moles of the container's contents or a specific substance
        in the specified unit.
  
        Args:
            unit (str, optional): The unit in which the moles should be returned (default: 'mol').
            substance (Substance, optional): The specific substance for which to retrieve the moles.
                                           If not provided, returns the total moles.
    
        Returns:
            moles (float): The moles in the specified unit.
        """
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")
        if substance is not None and not isinstance(substance, Substance):
            raise TypeError("Substance argument must be a Substance or None.")
        
        # Ensure the unit is a valid mole unit.
        if unit[-3:] != 'mol':
            raise ValueError(f"Invalid mole unit '{unit}'.")

        # Get either the specific amount of the substance if it is specified, or
        # the total amount in the container by summing all its contents.
        amount = self.contents.get(substance, 0) if substance else \
                    sum(self.contents.values())
        
        return Unit.convert_from_storage(amount, unit)

    @cache
    def get_volume(self, unit: str = 'L', substance: Substance = None) -> float:
        """
        Returns the volume of the container's contents or a specific substance
        in the specified unit.
  
        Args:
            unit (str, optional): The unit in which the volume should be returned (default: 'L').
            substance (Substance, optional): The specific substance for which to retrieve the volume.
                                           If not provided, returns the total volume.
    
        Returns:
            volume (float): The volume in the specified unit.
        """
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")
        if substance is not None and not isinstance(substance, Substance):
            raise TypeError("Substance argument must be a Substance or None.")
        
        # Ensure the unit is a valid volume unit.
        if unit[-1:].upper() != 'L' or unit[-3:].lower() == "mol":
            raise ValueError(f"Invalid volume unit '{unit}'.")

        if not substance:
            return Unit.convert_from_storage(self.volume, unit)
        
        return substance.convert_from(self.contents.get(substance,0),
                                     config.moles_storage_unit, unit)
    
    @cache
    def get_quantity(self, unit: str, substance: Substance = None):
        """
        Returns the quantity of the container's contents or a specific substance
        in the specified unit.
  
        Args:
            unit (str, optional): The unit in which the quantity should be returned.
            substance (Substance, optional): The specific substance for which to retrieve the quantity.
                                           If not provided, returns the total quantity of the container's
                                           contents.
    
        Returns:
            quantity (float): The quantity in the specified unit.
        """
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")
        if substance is not None and not isinstance(substance, Substance):
            raise TypeError("Substance argument must be a Substance or None.")
        
        if not substance:
            return sum(
                sub.convert_from(value, config.moles_storage_unit, unit)
                    for sub, value in self.contents.items()
                )
        else:
            return substance.convert_from(self.contents.get(substance,0),
                                     config.moles_storage_unit, unit)

    @cache
    def get_concentration(self, solute: Substance, units: str = 'M') -> float:
        """
        Get the concentration of solute in the current solution.

        Args:
            solute (Substance): Substance interested in.
            units (str, optional): Units to return concentration in, 
                                   defaults to Molar.

        Returns: 
            concentration (float): The concentration of the substance in this
                                   container.

        """
        if not isinstance(solute, Substance):
            raise TypeError("Solute must be a Substance.")
        if not isinstance(units, str):
            raise TypeError("Units must be a str.")

        mult, *units = Unit.parse_concentration('1 ' + units)

        numerator = solute.convert_from(self.contents.get(solute, 0), 
                                      config.moles_storage_unit, units[0])

        if numerator == 0:
            return 0

        if units[1].endswith('L'):
            denominator = self.get_volume(units[1])
        else:
            denominator = 0
            for substance, amount in self.contents.items():
                denominator += substance.convert_from(amount, 
                                                 config.moles_storage_unit,
                                                   units[1])

        return round(numerator / denominator / mult, config.internal_precision)
    
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
    def transfer(source: Container | Plate | PlateSlicer, 
                 destination: Container, quantity: str) \
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
        # These lines are needed to ensure that the calls to 'isinstance()' 
        # inside this function will work correctly. By the time this function 
        # is called, the modules have already been loaded, so no circular 
        # dependencies are created.
        if not TYPE_CHECKING:
            from pyplate.plate import Plate, PlateSlicer
        
        if not isinstance(destination, Container):
            if isinstance(destination, Plate):
                message = "Destination must be a Container. " + \
                          "Use 'Plate.transfer()' to transfer to a Plate."
            else:
                message = "Destination must be a Container."
            raise TypeError(message)
        if isinstance(source, Container):
            return destination._transfer(source, quantity)
        if isinstance(source, (Plate, PlateSlicer)):
            return destination._transfer_slice(source, quantity)
        raise TypeError("Invalid source type.")

    def _auto_generate_solution_name(solute : Iterable[Substance],
                                     solvent : Substance | Container):
        
        """
        Automatically generates a name for a solution based on the specified
        contents of the solution.

        Args:
            - solute - The set of solutes of the solution.
            - solvent - The solvent of the solution, can be either a Substance
            or a Container.

        Returns:
            - The auto-generated name (as a 'str').
        """
        # Check argument types
        if isinstance(solute, Substance):
            solute = [solute]
        if not isinstance(solute, Iterable) or \
            not any(isinstance(sub, Substance) for sub in solute):
            raise TypeError("Solute(s) must be a Substance.")
        
        if not isinstance(solvent, (Substance, Container)):
            raise TypeError("Solvent must be a Substance or Container.")
        
        # Create a list of the solute names separated by commas
        solute_names = ', '.join(substance.name for substance in solute)
        name = f"Solution of {solute_names} in "
        
        # If the solvent is a substance, append the name of the substance
        # to the end of the solution name.
        #   E.g. if solute=salt and solvent=water, 
        #        name="Solution of salt in water"
        if isinstance(solvent, Substance):
            name += solvent.name

        # If the solvent is a Container containing only one substance, 
        # append the name of the substance to the end of the solution name.
        #    E.g. if solute=salt and solvent=Container('water_stock')
        #         name="Solution of salt in water"
        elif len(solvent.contents) == 1:
            name += next(iter(solvent.contents.keys())).name

        # If the solvent is a Container conataining multiple substances,
        # append the phrase "contents of Container 'CONTAINER_NAME'" to the 
        # end of the solution name.
        #   E.g. if solute=salt and solvent=Container('salt_water_stock'), 
        #        name="Solution of salt in contents of Container 
        #              'salt_water_stock'"
        else:
            name += f"contents of Container \'{solvent.name}\'"

        # Return the auto-generated name
        return name

    def _compute_solution_contents(solute : Iterable[Substance],
                                   solvent : Substance | Container,
                                   **kwargs) -> Iterable[float]:
        """
        Computes the moles of each substance in the solution that is defined by
        the specified constraints.

        Two out of 'concentration', 'quantity', and total_quantity must be 
        specified.

        Multiple solutes can be, optionally, provided as a list. Each solute 
        will have the desired concentration or quantity in the final solution.

        If one value is specified for concentration or quantity and multiple 
        solutes are provided, the value will be used for all solutes.

        Arguments:
            solute: What to dissolve. Can be a single Substance or a list of 
                    Substances.
            solvent: What to dissolve with. Can be a Substance or a Container.
            concentration: Desired concentration(s). ('1 M', '0.1 umol/10 uL', 
                           etc.)
            quantity: Desired quantity of solute(s). ('3 mL', '10 g')
            total_quantity: Desired total quantity. ('3 mL', '10 g')
        """

        # Check that solute is an iterable set of substances. Because this is
        # an internal hidden function, it is the responsibility of the functions
        # that call this function to make an iterable object from a single 
        # substance.
        if not isinstance(solute, Iterable) or \
             any(not isinstance(substance, Substance) for substance in solute):
            raise TypeError("Solute(s) must be a Substance.")

        # Ensure that the solutes are all distinct; raise a ValueError if there
        # are repeated solutes.
        previous_substances = {}
        for current_solute in solute:
            if current_solute in previous_substances:
                raise ValueError("Solute substances cannot repeat. Found more" +
                                 f" than one occurrence of {current_solute}")
            previous_substances[current_solute] = 1

        # Check that the solvent is a substance (Container solvents should be
        # transformed into pseudo-solvent substances before calling this hidden
        # function).
        if not isinstance(solvent, (Substance | Container)):
            raise TypeError("Solvent must be a Substance or Container.")
        
        # To avoid later isinstance() checks, store the type of solvent with a 
        # boolean variable
        is_pure_solvent = isinstance(solvent, Substance)

        concentration = kwargs.get('concentration', None)
        quantity = kwargs.get('quantity', None)
        total_quantity = kwargs.get('total_quantity', None)

        # NOTE: Type checking for these keyword arguments is done below.

        # Ensure that at least two of the three arguments have been specified.
        if (concentration is not None) + (quantity is not None) + (total_quantity is not None) != 2:
            raise ValueError("Must specify two values out of concentration, quantity, and total quantity.")

        # Define a helper function for mole-to-unit conversions. Most of the
        # coefficients in the system of equations below are direct outputs of
        # this function.
        def convert_one(substance: Substance, u: str) -> float:
            """ Converts 1 mol to unit `u` for a given substance. """
            return substance.convert_from(1, 'mol', u)

        # If the solvent is not a pure substance, define a helper function for 
        # mole-to-unit conversions for containers. This is the equivalent of the
        # above function, but for containers instead of pure substances.
        if not is_pure_solvent:
            def convert_one_container(container: Container, u: str):
                """
                Converts 1 mol of a container's contents to unit `u`.
                """
                # TODO: Refactor this to handle prefixes as outputs of 
                # Unit.parse_quantity (currently unhandled). Maybe even make a
                # function for Containers to automatically handle these kinds of
                # calculations. May also need optimizations.
                if u == 'g':
                    return container.get_mass('g') / container.get_moles()
                elif u == 'mol':
                    return 1
                elif u == 'L':
                    return container.get_volume('L') / container.get_moles()

        # Check for solutes that overlap the solvent, and compute their
        # mole fractions within the solvent if so.
        num_solutes = len(solute)
        solute_mole_fractions = np.zeros((num_solutes))

        # If the solvent is a substance, check if it matches any of the 
        # solute substances, and if so set the coefficient to 1. Because solutes
        # must not repeat, the loop can be terminated early if a matching 
        # solute is found. 
        #
        # NOTE: This is handling an extrmely likely scenario of adding the same
        # compound as both a solute and solvent (e.g. a solution of water in
        # water). In practice, this will maintain all zeroes for the mole 
        # fractions.
        if is_pure_solvent:
            for idx, current_solute in enumerate(solute):
                if solvent == current_solute:
                    solute_mole_fractions[idx] = 1
                    break

        # If the solvent is a container, compute the total amount of all the 
        # solvent container's contents in 'molar storage units'. Then, compute
        # the mole fraction of any overlapping solutes.
        else:
            total_solvent_amt = sum(solvent.contents.values())
            for idx, current_solute in enumerate(solute):
                if current_solute in solvent.contents:
                    solute_mole_fractions[idx] = solvent.contents[current_solute] / total_solvent_amt
            

        # We now define a system of equations which will be used to solve for 
        # the moles of each substance that must be added to create the desired 
        # solution. 
        # 
        # This function assumes that the experimenter can add as much of the
        # specified solutes and the solvent as needed to create the solution
        # (if the solvent is a Container, and the transfer would exceed the
        # maximum volume, this function will not detect it). Thus, the degrees
        # of freedom in the system should be the number of solutes (n) + 1. This
        # matches the number of columns in the NumPy arrays defined below.
        # 
        # TODO: The number of rows corresponds to the number of equations that
        # are used to solve the system. Assuming the equations are not linearly
        # dependent, this should also be n + 1, otherwise the system will be 
        # overconstrained. At present, this is only true in the case of one 
        # solute, and so for more than one solute, it is possible to 
        # overconstrain the system.
        #
        # There are three supported solution constraints:
        #  - concentration (referring to solute concentrations)
        #  - quantity (referring to solute quantities)
        #  - total_quantity (referring to total quantity)
        # 
        # Each of these constraints is used to create one equation for the
        # system (if multiple solutes are included, each specified value
        # corresponds to one equation). Thus, by specifying two constraints, the
        # overall system of equations will have at least n + 1 equations, which
        # is enough to solve for the moles of the solution.
        #
        # First, we define a blank system of equations which will be filled in
        # with the appropriate values corresponding to the constraints. 
        a = np.zeros((num_solutes * 2, num_solutes + 1), dtype=float)
        b = np.zeros(num_solutes * 2, dtype=float)

        # Define an index for tracking the current equation's row in the system
        # of equations. This index should be increased any time the function 
        # has finished an equation and is moving onto the next one.
        equation_index = 0

        # The concentration constraint equations represent the amount of moles 
        # of each of the solutes and of the solvent needed to achieve the
        # specified concentrations of the solutes.
        #
        # For a solution with a single specified solute, the equation will look
        # like:
        # 
        #    [f  g] = [0]
        #
        # The terms in this equation have a similar derivation to those in 
        # create_dilution(), please refer to the explanatory comment in that
        # section for more details.
        # 
        # TODO: Finish writing this explanation   
        
        # If the concentration constraint has been specified, define the 
        # equations that correspond to the specified concentrations.   
        if concentration is not None:
            # Ensure that the concentration argument has the correct type (this 
            # is only part of the type checking, type checking for each 
            # concentration is performed later as part of the loop)
            if isinstance(concentration, str):
                concentration = [concentration] * len(solute)
            elif not isinstance(concentration, Iterable):
                raise TypeError("Concentration(s) must be a str.")

            # Ensure that the number of specified concentrations matches the
            # number of specified solutes.
            if len(concentration) != num_solutes:
                raise ValueError("Number of concentrations must match number of solutes.")

            # Define a dictionary for caching the calculated coefficients for
            # each solute's contribution to the 'total quantity' represented in 
            # the denominator of the parsed concentration. If the concentrations
            # are specified in the same units, these coefficients can be reused
            # for subsequent iterations.
            bottom_arrays = {}
            for solute_idx, (c, current_solute) in enumerate(zip(concentration, solute)):
                # Ensure that the concentration is the correct type
                if not isinstance(c, str):
                    raise TypeError("Concentration(s) must be a str.")
                
                # Try to parse the concentration, raising an error if parsing
                # was unsuccessful.
                try:
                    c, numerator, denominator = Unit.parse_concentration(c)
                except ValueError:
                    raise ValueError(f"Invalid concentration. ({c})")

                # Compute the terms of the 'bottom' part of the concentration
                # constraint equation

                # If the 'total quantity' coefficients have not already been 
                # found, compute the mole-to-unit values for each of the solutes
                #  and the solvent. 
                if denominator not in bottom_arrays:
                    # Create an num_solutes + 1 size array for storing the 
                    # coefficients
                    bottom = np.zeros((num_solutes + 1))
                    # Compute the mole-to-unit solute coefficients
                    bottom[:-1] = list(convert_one(substance, denominator) 
                                           for substance in solute)
                    # Compute the mole-to-unit solvent coefficient using the
                    # appropriate helper function.
                    if is_pure_solvent:
                        bottom[-1] = convert_one(solvent, denominator) 
                    else:
                        bottom[-1] = convert_one_container(solvent, denominator)

                    # Cache the result for future iterations
                    bottom_arrays[denominator] = bottom
                
                # Otherwise, used the cached results. 
                else:
                    bottom = bottom_arrays[denominator]

                # Compute the terms of the 'top' part of the concentration
                # constraint equation
                
                # Create an num_solutes + 1 size array for storing the 
                # coefficients
                top = np.zeros((num_solutes+1))

                # Set the solute coefficient to the mole-to-unit coefficient
                top[solute_idx] = convert_one(current_solute, numerator)
                
                # Set the solvent coefficient to the quantity of solute, in
                # terms of the numerator units per that are present in one mole 
                # of solvent.
                top[-1] = convert_one(current_solute, numerator) * \
                                        solute_mole_fractions[solute_idx]

                # Compute the coefficients of the left-hand side of the equation 
                # from the previously calculated arrays.
                a[equation_index] = c * bottom - top

                # NOTE: The right-hand side of the equation is 0, so it does not
                # need to be set here.

                equation_index += 1

        # The quantity constraint equations represent the amount of moles of
        # each solute and of the solvent needed to achieve the specified 
        # quantities of the solutes.
        # 
        # For a solution with a single specified solute, the quantity constraint
        # equation will look like:
        # 
        #   [f  g] = [h]
        # 
        # where f, g, and h, are defined as stated below:
        #   - f: The 'units per mole' of the pure solute. Here, 'unit' refers to
        #        the unit of the specified quantity. 
        #          E.g. If quantity is '2 mg', and the solute is NaCl, then 'f'
        #               will be 58,440 as there are 58,440 mg per mole of NaCl.       
        #  
        #   - g: The 'units of the solute per mole' of the solvent. If the
        #        solvent does not contain any of the solute, this number is 0.
        #        Otherwise, it is calculated based on the contents of the 
        #        solvent container.
        #          E.g. If quantity is '3 moles', the solute is NaCL, and the 
        #               solvent is salt water with a mole fraction of 0.01, then
        #               'g' will be 0.01 as there are 0.01 moles of salt per 
        #               mole of solvent.
        #  
        #   -h: The value half of the specified quantity.
        #         E.g. If quantity is '4 mL', 'h' will be 4.    
        # 
        # For multiple solutes, there will be multiple constraint equations. For
        # two solutes, the equations will look like the following:
        # 
        #   [f_1   0   g_1] = [h_1]
        #   [ 0   f_2  g_2] = [h_2] 
        #
        # The terms are the same as in the single solute setup, but now there
        # are extra 0 values in each equation for the additional solutes.

        # If the quantity constraint has been specified, define the equations 
        # that correspond to the specified quantities.
        if quantity is not None:
            # Ensure that the quantity argument has the correct type (this is 
            # only part of the type checking, type checking for each quantity
            # is performed later as part of the loop).
            if isinstance(quantity, str):
                quantity = [quantity] * len(solute)
            elif not isinstance(quantity, Iterable):
                raise TypeError("Quantity(s) must be a str.")
            
            # Ensure that the number of quantities specified matches the number 
            # of solutes.
            if len(quantity) != num_solutes:
                raise ValueError("Number of quantities must match number of solutes.")

            # Iterate through the specified quantities, parsing each into a 
            # constraint equation.
            for solute_idx, (q, current_solute) in enumerate(zip(quantity, solute)):
                # Ensure that each quantity is the correct type.
                if not isinstance(q, str):
                    raise TypeError("Quantity(s) must be a str.")
                
                # Parse the quantity as a value-unit pair.
                q, unit = Unit.parse_quantity(q)

                # Set the equation coefficient corresponding to the solute (the
                # i-th entry in the row) to the 'unit per mole' value for the 
                # solute ('f' in the above derivation). 
                a[equation_index, solute_idx] = convert_one(current_solute, unit)

                # Set the equation coefficient corresponding to the solvent (the
                # last entry in the row) to the 'unit solute per mole solvent'
                # value for the solvent.
                a[equation_index, -1] = convert_one(current_solute, unit) * \
                                            solute_mole_fractions[solute_idx]

                # Set the right-hand side of the equation to the value parsed 
                # from the specified quantity.
                b[equation_index] = q

                equation_index += 1


        # The total quantity constraint equation represents the amount of moles 
        # of each solute and of the solvent needed to achieve a specified total 
        # quantity of all substances in the solution combined. The equation 
        # takes the form:
        #
        #   [ q_1  q_2  ... q_n  q_solvent] = [tq]
        # 
        # where q_i is defined as the 'quantity per mole' of the corresponding
        # solute/solvent. 
        # 
        # If this is a pure substance, then it is the conversion factor between 
        # 1 mole of the substance and the units of the specified total quantity.
        #   E.g. If the first solute is salt, and the total quantity specified
        #        is 20 g, then 'q_1' = 58.44 because there are 58.44 grams per 
        #        one mole of salt.
        #
        # If this is a solution/mixture (i.e. if solvent is a Container), then
        # it is the 'effective' conversion factor between 1 mole of the solution
        # and the units of the specified total quantity.
        #   E.g. If the solvent is salt water with a mole fraction of 0.01, and 
        #        the total quantity specified is 25 g, then:
        #            q_solvent = (0.99) * 18.0153 + 0.01 * (58.44) = 18.42
        
        # If the total quantity constraint has been specified, define the
        # equation which corresponds to the specified total quantity.
        if total_quantity is not None:
            # Ensure that total quantity has the correct type.
            if not isinstance(total_quantity, str):
                raise TypeError("Total quantity must be a str.")

            total_quantity, tq_unit = Unit.parse_quantity(total_quantity)

            # Set the solute coefficients for this equation (all but the last
            # entry) to the 'quantity per mole' values.
            a[equation_index,:-1] = np.array(list(convert_one(sub, tq_unit) 
                                                  for sub in solute))
            
            # Set the solvent coefficient for this equation to the 'quantity per 
            # mole' amount
            if is_pure_solvent:
                a[equation_index, -1] = convert_one(solvent, tq_unit)
            else:
                # TODO: Refactor this to handle prefixes as outputs of 
                # Unit.parse_quantity (currently unhandled). Maybe even make a
                # function for Containers to automatically handle these kinds of
                # calculations. 
                a[equation_index, -1] = convert_one_container(solvent, tq_unit)

            # Set the right hand side of the equation to the value parsed from
            # the specified total quantity.
            b[equation_index] = total_quantity

        # Solve the system of equations to determine the number of moles of each
        # solute and the solvent needed to create the solution.
        xs = np.linalg.solve(a[:num_solutes + 1], b[:num_solutes + 1])

        # Ensure that the solution is a true solution to the system of equations
        # (as opposed to a least-squares best "solution") by checking if the 
        # left and right sides are equal within a small tolerance.
        for i in range(len(a)):
            if abs(sum(a[i] * xs) - b[i]) > 1e-6:
                raise ValueError("Solution is impossible to create. "
                                 "The provided constraints cannot all be "
                                 "satisfied.")

        # Ensure that the number of moles needed from each component is
        # non-negative. If any are negative, raise an error.
        if any(x <= 0 for x in xs):
            raise ValueError("Solution is impossible to create. "
                             "Negative amounts of substances are needed "
                             "to satisfy the constraints.")

        return xs

    @staticmethod
    def create_solution(solute: Substance | Iterable[Substance], 
                        solvent: Substance | Container,
                        name: str = None, **kwargs) -> Container:
        """
        Create a solution.

        Two out of concentration, quantity, and total_quantity must be specified.

        Multiple solutes can be, optionally, provided as a list. Each solute will have the desired concentration
        or quantity in the final solution.

        If one value is specified for concentration or quantity and multiple solutes are provided, the value will be
        used for all solutes.

        Arguments:
            solute: What to dissolve. Can be a single Substance or an iterable
                    set of Substances.
            solvent: What to dissolve with. Can be a Substance or a Container.
            name: Optional name for new container.
            concentration: Desired concentration(s). ('1 M', '0.1 umol/10 uL', etc.)
            quantity: Desired quantity of solute(s). ('3 mL', '10 g')
            total_quantity: Desired total quantity. ('3 mL', '10 g')


        Returns:
            New container with desired solution.
        """

        # Check that the solute argument has the correct type (either a single
        # Substance or an iterable set of Substances).
        #
        # This check is necessary to correctly generate the solution name in the
        # case where it is not provided, otherwise it would have been moved to
        # Container._compute_solution_contents().
        if isinstance(solute, Substance):
            solute = [solute]
        elif not isinstance(solute, Iterable) or \
             any(not isinstance(substance, Substance) for substance in solute):
            raise TypeError("Solute(s) must be a Substance.")

        # Check that the solvent argument has the correct type
        if not isinstance(solvent, (Substance, Container)):
            raise TypeError("Solvent must be a Substance or a Container.")

        # Check that the name argument as the correct type (if it is not None
        # or empty)
        if name is not None and not isinstance(name, str):
            raise TypeError("Name must be a str.")

        # If no name is provided, automatically generate a name based on the
        # solutes/solvent arguments
        if not name:
            name = Container._auto_generate_solution_name(solute, solvent)

        # Compute the moles of each of the substances of the solution
        xs = Container._compute_solution_contents(solute, solvent, **kwargs)

        # Set the initial contents of the solution based on the results of the 
        # mole calculations above
        initial_contents = list((substance, f"{x} mol") for x, substance in zip(xs, solute + [solvent]))
        
        # If the solvent argument was a Container, return the post-transfer
        # solvent container as well as the newly created solution container.
        if isinstance(solvent, Container):
            # Create a new container which represents the newly created solution
            # WITHOUT the solvent added.
            result = Container(name, initial_contents=initial_contents[:-1])
            
            # Create a list of contents for the "instructions" attribute of the
            # new container.
            contents = []
            for substance, value in result.contents.items():
                value, unit = Unit.convert_from_storage_to_standard_format(substance, value)
                precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                contents.append(f"{round(value, precision)} {unit} of {substance.name}")
            
            # Get the moles of the solvent container's contents needed for the
            # new solution
            _, solvent_amount = initial_contents[-1]

            # Trasnfer the amount of the solvent container necessary to create
            # the new solution
            solvent, result = Container.transfer(solvent, result, solvent_amount)

            # Compute the solvent volume needed for the transfer and convert the
            # result into a reading-friendly format.
            solvent_volume = solvent.get_volume('L')
            solvent_volume, unit = Unit.get_human_readable_unit(solvent_volume, 'L')
            solvent_volume = round(solvent_volume,
                                   config.precisions[unit] if unit in config.precisions else
                                   config.precisions['default'])
            
            # Set the container instructions attribute based on the amounts of 
            # solutes and solvent needed to create the new solution.
            result.instructions = ("Add " + ", ".join(contents) +
                                   f" to {solvent_volume} {unit} of " +
                                   f"{solvent.name}.")
            
            # Return the post-transfer result for the solvent container and 
            # the new solution container
            return solvent, result
        
        # Otherwise, return just the newly created solution container.
        else:
            # Create a new container which represents the newly created 
            # solution.
            result = Container(name, initial_contents=initial_contents)

            # Create a list of contents for the "instructions" attribute of the
            # new container.
            contents = []
            for substance, value in result.contents.items():
                value, unit = Unit.convert_from_storage_to_standard_format(substance, value)
                precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                contents.append(f"{round(value, precision)} {unit} of {substance.name}")
            
            # Set the container instructions attribute based on the amounts of 
            # solutes and solvent needed to create the new solution.
            result.instructions = "Add " + ", ".join(contents) + \
                                    " to a container."

            # Return the new solution container.
            return result

    @staticmethod
    def create_dilution(source: Container, solute: Substance, 
                            concentration: str, solvent: Substance | Container,
                            quantity: str, name=None) -> (Tuple[Container, Container] |
                                                          Tuple[Container, Container, Container]):
        """
        Create a diluted solution from an existing source solution and a 
        solvent.

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
        if name is not None and not isinstance(name, str):
            raise TypeError("Name must be a str.")

        quantity_value, quantity_unit = Unit.parse_quantity(quantity)
        
        if not math.isfinite(quantity_value):
            raise ValueError("Quantity must be finite.")
        
        if not quantity_value > 0:
            raise ValueError("Quantity must be positive.")
        
        if solute not in source.contents:
            raise ValueError(f"Source container does not contain {solute.name}.")

        # TODO: Possibly rework this name geneeation to include the name/
        #       contents of the source container. Currently, only the solute and
        #       solvent names are used. 
        if not name:
            name = Container._auto_generate_solution_name([solute], solvent)

        # For the following blocks of code, 'x' represents the source solution,
        # 's' represents the solute, and 'y' represents the solvent.

        mass = source.get_mass()
        moles = source.get_moles()
        volume = Unit.convert_from_storage(source.volume, 'mL')

        # Compute the 'effective density', 'effective molecular weight', and
        # 'effective molar concentration' of the source solution. Density is in
        # units of 'g/mL', molecular weight is in terms of 'g/mol', and molar
        # concentration is in terms of 'M' or 'mol/L'.
        d_x = mass / volume
        mw_x = mass / moles
        m_x = Unit.convert_from_storage(source.contents.get(solute, 0), 'mol') / (volume / 1000)

        # Compute the molecular weight, density, and molar concentration of the 
        # solvent. 
        # 
        # If the solvent is a Container, compute the 'effective' properties as 
        # is done for the source solution.
        if isinstance(solvent, Container):
            mass = solvent.get_mass()
            moles = solvent.get_moles('mol')
            volume = Unit.convert_from_storage(solvent.volume, 'mL')

            # Compute the 'effective density', 'effective molecular weight', and
            # 'effective molar concentration of solute' of the solvent. Density 
            # is in units of 'g/mL', molecular weight is in terms of 'g/mol', 
            # and molar concentration is in terms of 'M' or 'mol/L'.
            d_y = mass / volume
            mw_y = mass / moles
            m_y = Unit.convert_from_storage(solvent.contents.get(solute, 0), 'mol') / (volume / 1000)
        
        # Otherwise, use the properties of the solvent substance.
        else:
            d_y = solvent.density
            mw_y = solvent.mol_weight
            # Edge case: If the solvent and the solute are the same, then the
            # molar concentration of solute in the solvent is just the molar
            # density of the solvent. Otherwise, the concentration is 0.
            m_y = 0 if solvent != solute else solvent.density / solvent.mol_weight

        # Get the molecular weight and density of the solute (the shorter names 
        # will be useful for condensing later lines of code)
        mw_s = solute.mol_weight
        d_s = solute.density

        concentration, numerator, denominator = Unit.parse_concentration(concentration)

        # Define a blank system of equations that will be filled with values 
        # that correspond to the specified constraints. This system of equations
        # is in terms of the volumes (in mL) of the source and solvent that must
        # be added to create the desired diluted solution.
        a = np.array([[0., 0.], [0., 0.]])
        b = np.array([0., 0.])

        # The first equation in the system of equations represents the 
        # concentration constraint. The equation for solute concentration can be 
        # written as:
        #    
        #   concentration (C) = top / bottom
        #
        # where 'top' is the quantity of solute and 'bottom' is the total 
        # quantity. This is typically written in 'M', or 'mol/L', but PyPlate
        # supports all possible combinations of supported units for expressing 
        # concentration. 
        #  
        # To determine the values of the two terms of a[0], we must format this 
        # equation in terms of the volumes of the source and solvent needed for
        # the dilution. Unfortunately, these terms are buried in the top/bottom
        # terms above, and are different for all the possible types of units
        # that are allowed for concentrations. However, if we choose general
        # catch-all variable names 'p' and 'q' to represent the top and bottom
        # quantities respectively, we can write this equation as:
        #
        #   C = p_Total / q_Total 
        # 
        # These total quantities can be broken up into the contributions of the 
        # source and solvent solutions as follows:
        #  
        #   C = (p_x + p_y) / (q_x + q_y)
        #
        # The equation can then be rearranged to get:
        #
        #   C * (q_x + q_y) - (p_x + p_y) = 0
        #
        # The terms 'p_x', 'p_y', 'q_x', and 'q_y' are defined as follows:
        #
        #   - p_x represents the quantity (moles, mass, or volume) of SOLUTE 
        #     contributed to the dilution by the SOURCE solution.
        #
        #   - p_y represents the quantity (moles, mass, or volume) of SOLUTE
        #     contributed to the dilution by the SOLVENT solution.
        #
        #   - q_x represents the TOTAL quantity (moles, mass, or volume) 
        #     contributed to the dilution by the SOURCE solution.
        #
        #   - q_y represents the TOTAL quantity (moles, mass, or volume)
        #     contributed to the dilution by the SOLVENT solution.
        # 
        # If we define conversion ratios from the volume of the source and 
        # solvent solutions needed, V_x and V_y, to the quantities p_x/q_x and
        # p_y/q_y, we can write the above equation in terms of V_x and V_Y. 
        # 
        #   p_x = r_x * V_x
        #   p_y = r_y * V_y
        #
        #   q_x = s_x * V_x
        #   q_y = s_x * V_x
        # 
        #   C * (q_x + q_y) - (p_x + p_y) = 0
        #   C * (s_x * V_x + s_y * V_y) - (r_x * V_x + r_y * V_y) = 0
        #   (C * s_x - r_x) * V_x + (C * s_y - r_y) * V_y = 0 
        # 
        # If we define 'top' and 'bottom' as shown below:
        # 
        #   top = r_x * V_x + r_y * V_y 
        #   bottom = s_x * V_x + s_y * V_y
        #  
        # Then we can write the equation derived above as:
        #
        #   C * bottom - top = 0
        #
        # This is the form of the equation that will be used to solve for the 
        # dilution volumes. The various conversion factors are enumerated in the 
        # two code blocks below. 

        # Determine the appropriate conversion factors (r_x and r_y) for the 
        # 'top' quantities. These quantities express the quantity of SOLUTE
        # (mol, g, or L) added per mL of source/solvent solution. Units other 
        # than (mol, g, or L) in the concentration numerator will raise an 
        # error.
        if numerator == 'mol':
            # Compute 'moles of solute' per 'mL of solution'.
            top = np.array([m_x / 1000., m_y / 1000.])
        elif numerator == 'g':
            # Compute 'grams of solute' per 'mL of solution'.
            top = np.array([m_x * mw_s / 1000., m_y * mw_s / 1000.])
        elif numerator == 'L':
            # Compute 'liters of solute' per 'mL of solution'.
            top = np.array([m_x * mw_s / (d_s * 1e6), m_y * mw_s / (d_s * 1e6)])
        else:
            raise ValueError("Invalid numerator.")
        
        # Determine the appropriate conversion factors (s_x and s_y) for the 
        # 'bottom' quantities. These quantities express the TOTAL quantity
        # (mol, g, or L) added per mL of source/solvent solution. Units other 
        # than (mol, g, or L) in the concentration denominator will raise an 
        # error.
        if denominator == 'mol':
            # Compute 'moles of solution' per 'mL of solution'
            bottom = np.array([d_x / mw_x, d_y / mw_y])
        elif denominator == 'g':
            # Compute 'grams of solution' per 'mL of solution'
            bottom = np.array([d_x, d_y])
        elif denominator == 'L':
            # Compute 'liters of solution' per 'mL of solution'
            # (this one is just a simple conversion ratio from mL to L)
            bottom = np.array([1 / 1000., 1 / 1000.])
        else:
            raise ValueError("Invalid denominator.")

        # Set the entries of a[0] based on the derivation above
        a[0] = concentration * bottom - top

        # The second equation in the system of equations represents the total 
        # quantity constraint. The total quantity of the solution can be 
        # expressed as:
        # 
        #   q_Total = q_x + q_y
        #  
        # where q_x and q_y have the same definitions as in the derivation for
        # the first equation. Thus, to get the equation in terms of V_x and V_y,
        # we can write:
        #
        #   q_Total = s_x * V_x + s_y * V_y  
        # 
        # Thus, a[0] = [s_x, s_y] and b[0] = q_Total  
        #
        # These s_x and s_y ratios are defined indentically to those from the 
        # first equation. However, because the specified quantity may or may not 
        # be in the same units as the denominator of the specified dilution 
        # concentration, the values of s_x and s_y for this equation must be 
        # re-computed.

        # Parse quantity into a value-unit pair
        quantity_value, quantity_unit = Unit.parse_quantity(quantity)

        # Determine the appropriate conversion factors (s_x and s_y) to convert
        # from mL of solution to (mol/g/L) of solution, and set the values of 
        # the left-hand side of the equation accordingly. Units other than mol, 
        # g, or L in the quantity argument will raise an error.
        if quantity_value == 'mol':
            # Compute 'moles of solution' per 'mL of solution'.
            a[1] = np.array([d_x / mw_x, d_y / mw_y])
        elif quantity_unit == 'g':
            # Compute 'grams of solution' per 'mL of solution'.
            a[1] = np.array([d_x, d_y])
        elif quantity_unit == 'L':
            # Compute 'liters of solution' per 'mL of solution'
            # (this one is just a simple conversion ratio from mL to L).
            a[1] = np.array([1 / 1000., 1 / 1000.])
        else:
            raise ValueError("Invalid quantity unit.")

        # Set the right-hand side of the equation to the total quantity.
        b[1] = quantity_value

        # Solve the system of equations to compute the mL of source & solvent 
        # ('V_x' & 'V_y') needed for the dilution.
        V_x, V_y = np.linalg.solve(a, b)

        # If the volumes needed of either solution are negative, the solution is
        # impossible to create. This is likely because the specified dilution is
        # more concentrated in the solute than either the source or solvent 
        # solution.
        if V_x < 0 or V_y < 0:
            raise ValueError("Solution is impossible to create. The specified" +
                             " concentration is likely higher than either the" +
                             " source or solvent concentrations.")

        # Create the new solution using the calculated volumes 'V_x' and 'V_y'.
        # If the solvent is a substance, the necessary amount can be added to
        # the initial contents of the new dilution container. Otherwise, it must
        # be transferred from the solvent Container object.
        if isinstance(solvent, Substance):
            # If 'V_y' is greater than zero, add 'V_y' mL of solvent to the 
            # initial contents of the new container, otherwise leave the 
            # container empty.
            if V_y:
                new_solution = Container(name, initial_contents=[(solvent, f"{V_y} mL")])
            else:
                new_solution = Container(name)
            
            # If 'V_x' is greater than zero, transfer 'V_x' mL of the source 
            # solution to the new container.
            if V_x:
                source, new_solution = Container.transfer(source, new_solution, f"{V_x} mL")
        else:
            # Create an empty container for the dilution result
            new_solution = Container(name)

            # If 'V_x' is greater than zero, transfer 'V_x' mL of the source 
            # solution to the new container.
            if V_x:
                source, new_solution = Container.transfer(source, new_solution, f"{V_x} mL")

            # If 'V_y' is greater than zero, transfer 'V_y' mL of the solvent 
            # solution to the new container.
            if V_y:
                solvent, new_solution = Container.transfer(solvent, new_solution, f"{V_y} mL")

        # Set the new container's instructions attribute to accurately reflect
        # the details of the dilution.
        precision = config.precisions['mL'] if 'mL' in config.precisions else config.precisions['default']
        new_solution.instructions = f"Add {round(V_y, precision)} mL of {solvent.name} to" + \
                                    f" {round(V_x, precision)} mL of {source.name}."

        # If the solvent is a Substance, return the modified post-transfer 
        # source container and the new dilution container. Otherwise, return
        # the modified post-transfer source container, the modified post-
        # transfer solvent container, and the new dilution container.
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
            new_container.volume += substance.convert_from(value, config.moles_storage_unit, config.volume_storage_unit)

        new_container.instructions = self.instructions
        classes = {Substance.SOLID: 'solid', Substance.LIQUID: 'liquid'}
        if what in classes:
            new_container.instructions += f"Remove all {classes[what]}s."
        else:
            new_container.instructions += f"Remove all {what.name}s."
        return new_container

    def dilute_in_place(self, solute: Substance, concentration: str, 
                        solvent: (Substance | Container), 
                        name=None) -> Container:
        """
        Dilutes this container with `solvent` until the concentration of 
        `solute` matches `concentration`.

        Args:
            solute: Substance which is the subject of the dilution.
            concentration: Desired concentration of the solute.
            solvent: What to dilute with. Can be a Substance or a Container.
            name: Optional name for new container.

        Returns: A new (updated) container with the remainder of the original 
        container, and the diluted solution.

        If `solvent` is a Container, a new container with the remainder of the
        solvent will be returned as well.
        """
        if not isinstance(solute, Substance):
            raise TypeError("Solute must be a Substance.")
        if not isinstance(concentration, str):
            raise TypeError("Concentration must be a str.")
        if not isinstance(solvent, (Substance, Container)):
            raise TypeError("Solvent must be a Substance or a Container.")
        if name and not isinstance(name, str):
            raise TypeError("New name must be a str.")
        
        if solute not in self.contents:
            raise ValueError(f"Container does not contain {solute.name}.")
        
        # Save whether the solvent is a pure Substance to a local variable to 
        # avoid costlier calls to isinstance().
        is_pure_solvent = isinstance(solvent, Substance)

        # Parse the target concentration for the dilution and specified units 
        # from the concentration argument. The target units are combined for 
        # use in the later calls to get_concentration().
        target_conc, num_unit, denom_unit = Unit.parse_concentration(concentration)
        target_units = f"{num_unit}/{denom_unit}"

        # Compute the concentration of solute in the starting source solution in
        # terms of the target units.
        source_conc = self.get_concentration(solute, target_units)

        # Compute the concentration of solute in the solvent in terms of the
        # target units.
        if is_pure_solvent:
            if solvent != solute:
                # If the solvent is NOT the same as the solute, then the solute
                # concentration in the solvent is 0.
                solvent_conc = 0
            else:
                # Edge case: If the solvent IS the same as the solute, then the
                # solute concentration in the solvent in terms of the target 
                # units is the conversion factor between the denominator units 
                # and the numerator units.
                #   E.g. If concentration = 0.25 mol/L and the solute & solvent 
                #        are both water, then the solvent concentration is
                #        1 / 18.0153 mol/mL.
                solvent_conc = solvent.convert_from(1, denom_unit, num_unit)
        else:
            solvent_conc = solvent.get_concentration(solute, target_units)

        # These two checks are placed BEFORE the early return because they are
        # for conditions that should NEVER arise in the container. 
        # 
        # In the scenario where the target concentration and source 
        # concentration are identical, but they both match one of the failure 
        # cases below, it is better to alert the user to the existence of a 
        # problem by throwing an error than it is to silently succeed.

        if not math.isfinite(target_conc):
            raise ValueError("Target concentration cannot be non-finite!" +
                             f"Target: {concentration}")

        if target_conc < 0:
            raise ValueError("Target concentration cannot be negative." + 
                             f"Target: {concentration}")
        
        # If the current mole fraction of the solute is already within a small 
        # tolerance of the desired mole fraction, return the current container.
        # 
        # NOTE: This was changed from being a copy of the container as it seemed
        # unnecessary to copy the Container if no changes were made. May need to
        # be changed back if problems arise.        
        if abs(source_conc - target_conc) <= target_conc * 1e-6:
            return self

        # The remaining checks are placed AFTER the previous two lines of code 
        # so that otherwise invalid dilutions will succeed the container
        # already has the required concentration. 

        if target_conc == 0:
            raise ValueError("The target concentration for the solute cannot " +
                             "be zero if the source concentration is non-zero.")
        
        # Compute the ratio of solvent to source solution needed for the
        # dilution. This ratio is in terms of the denominator unit from the 
        # concentration argument, hereafter called "denom_units". If a zero-
        # division error is raised, this means that the target and solvent
        # concentrations are equal, which results in an impossible dilution.
        try:
            ratio = (source_conc - target_conc) / (target_conc - solvent_conc)
        except ZeroDivisionError as zde:
            raise ValueError("The target concentration for the solute cannot " +
                             "match its concentration in the solvent." + 
                             f"Target: {concentration}  " +
                             f"Solvent: {solvent_conc} {target_units}")

        # If the ratio is negative, then the target concentration lies outside
        # of the range between the source concentration and the solute 
        # concentration.
        if ratio < 0:
            raise ValueError("The target concentration for the solute must " + 
                             "lie between the source concentration and the " +
                             f"solvent concentration. Target: {concentration}" +
                             f"  Source: {source_conc} {target_units}  " + 
                             f"  Solvent: {source_conc} {target_units}")
        
        # NOTE: the case of ratio = 0 means that the source and target 
        # concentrations are identical, which would already result in early 
        # termination from the check above. 


        # Compute the volume of solvent needed for the dilution. This requires
        # two steps. 
        
        # First, the amount of solvent in "denom_units" is computed as the 
        # product of the amount of source solution in "denom units" and the 
        # previously computed ratio. 
        try:
            solvent_amt = self.get_quantity(denom_unit) * ratio

        # If this fails, the get_quantity() error does not specify that the
        # denominator unit of the concentration was the problem, so a new error
        # is raised to include these details.
        except ValueError as e:
            raise ValueError("Invalid unit in concentration denominator: " + 
                             f"{denom_unit}")
        
        # Second, the amount of solvent in "denom units" is multiplied by the 
        # "volume of solvent per denom unit".
        if is_pure_solvent:
            vol_per_qty = solvent.convert_from(1, denom_unit, 'L')
            solvent_volume = solvent_amt * vol_per_qty
        else:
            vol_per_qty = solvent.get_volume('L') / solvent.get_quantity(denom_unit)
            solvent_volume = solvent_amt * vol_per_qty

        
        # Ensure the computed volume can fit in this container.
        if self.volume + solvent_volume > self.max_volume:
            raise ValueError("Dilute solution will not fit in the container.")

        # Add the solvent to this container to produce the diluted solution.
        if is_pure_solvent:
            result = self._add(solvent, f"{solvent_volume} L")
        else:
            result = Container.transfer(solvent, self, f"{solvent_volume} L")

        diluted_solution = result if is_pure_solvent else result[1]

        if name:
            diluted_solution.name = name

        # Set the instructions attribute of the diluted container based on the
        # details of the dilution.
        solvent_volume, unit = Unit.get_human_readable_unit(solvent_volume, 'L')
        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        diluted_solution.instructions += f"\nDilute with {round(solvent_volume, precision)}" + \
                                    f"{unit} of {solvent.name}."
        
        return result

    def fill_to(self, substance: Substance, quantity: str) -> Container:
        """
        Fills container with `substance` up to `quantity`.

        Args:
            substance: Substance to use to fill.
            quantity: Desired final quantity in container.

        Returns: New Container with desired final `quantity`

        """
        # Check that the argument types are correct.
        if not isinstance(substance, Substance):
            raise TypeError("Argument 'substance' must be a Substance.")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")

        # Parse the quantity as a value-unit pair
        quantity, quantity_unit = Unit.parse_quantity(quantity)

        # Check that the quantity value is positive
        #
        # 'Not greater than' is preferred over 'less than or equal to' because
        # it will handle 'nan' values correctly ('nan' values should be caught 
        # during quantity parsing, but it is worth making sure this behaves
        # properly in the case that they are not caught).
        if not quantity > 0:
            raise ValueError("Quantity must be positive.")
        
        # Check that the unit is valid
        if quantity_unit not in ('L', 'g', 'mol'):
            raise ValueError("Invalid quantity unit.")

        # Compute the total amount of substances currently in the container.
        current_quantity = sum(subst.convert(f"{value} {config.moles_storage_unit}", 
                                            quantity_unit) 
                                for subst, value in self.contents.items())

        # Compute the amount of the substance that would need to be added to
        # reached the specified 'fill to' quantity.
        #
        # Rounding is done here to avoid throwing errors for values that are
        # 'effectively zero' e.g. -4.12...e-17
        required_quantity = round(quantity - current_quantity, 
                                  config.internal_precision)

        # Ensure that the quantity needed is either positive or zero.
        #
        # 'Not greater than or equal to' is preferred over 'less than' because
        # it will handle 'nan' values correctly ('nan' values should be caught 
        # during quantity parsing, but it is worth making sure this behaves
        # properly in the case that they are not caught).
        if not required_quantity >= 0:
            raise ValueError(f"Argument quantity '{quantity} {quantity_unit}'" + \
                             " must be greater than the current quantity within" + \
                             f" the container '{current_quantity} {quantity_unit}'.")

        # If the required volume needed is 0, return the same container without 
        # adding anything to it.
        if required_quantity == 0:
            return self

        # Add the required quantity to the container
        result = self._add(substance, f"{required_quantity} {quantity_unit}")

        # Update the container's instructions with this filling step.
        required_quantity, unit = Unit.get_human_readable_unit(required_quantity, quantity_unit)
        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        result.instructions += f"\nFill with {round(required_quantity, precision)} {unit} of {substance.name}."
        
        return result
