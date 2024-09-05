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


    def get_mass(self, unit: str = None) -> float:
        """
        Get the total mass of all contents of the container.

        Args:
            unit: Unit to return the mass in. Defaults to mass_display_unit 
            from config.

        Returns: Total mass of all contents in the container.
        """
        if unit is None:
            unit = config.mass_display_unit

        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")
        
        return sum(
            Unit.convert_from(sub, value, config.moles_storage_unit, unit)
                for sub, value in self.contents.items()
        )


    def get_moles(self, unit: str = None) -> float:
        """
        Get the total moles of all contents of the container.

        Args:
            unit: Unit to return the moles in. Defaults to 'mol'.

        Returns: Total moles of all contents in the container.
        """
        if unit is None:
            unit = "mol"

        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")
        
        return Unit.convert_from_storage(sum(self.contents.values()), unit)

    def get_volume(self, unit: str = None) -> float:
        """
        Get the volume of the container.

        Args:
            unit: Unit to return volume in. Defaults to volume_display_unit 
            from config.

        Returns: Volume of the container.

        """
        if unit is None:
            unit = config.volume_display_unit

        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")

        return Unit.convert_from_storage(self.volume, unit)

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
            return Unit.convert_from(substance, 1, 'mol', u)

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
                    return solvent.get_mass('g') / solvent.get_moles()
                elif u == 'mol':
                    return 1
                elif u == 'L':
                    return solvent.get_volume('L') / solvent.get_moles()

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
        # _dilute_to_quantity(), please refer to the explanatory comment in that
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

        # Ensure that the number of moles needed from each component is
        # non-negative. If any are negative, raise an error.
        if any(x <= 0 for x in xs):
            raise ValueError("Solution is impossible to create.")

        # Ensure that the solution is a true solution to the system of equations
        # (as opposed to a least-squares best "solution") by checking if the 
        # left and right sides are equal within a small tolerance.
        for i in range(len(a)):
            if abs(sum(a[i] * xs) - b[i]) > 1e-6:
                raise ValueError("Solution is impossible to create.")
            
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
    def _dilute_to_quantity(source: Container, solute: Substance, 
                            concentration: str, solvent: Substance | Container,
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
        # Check argument types
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

        # Parse the quantity as a value-unit pair
        quantity_value, quantity_unit = Unit.parse_quantity(quantity)
        
        # Ensure that the quantity value is finite
        if not math.isfinite(quantity_value):
            raise ValueError("Quantity must be finite.")
        
        # Ensure that the quantity value is positive.
        if not quantity_value > 0:
            raise ValueError("Quantity must be positive.")
        
        # Ensure the solute is part of the source container's contents.
        if solute not in source.contents:
            raise ValueError(f"Source container does not contain {solute.name}.")

        # Ensure that the solute and solvent are not the same Substance.
        if solvent == solute:
            raise ValueError("Solute and solvent must be different.")

        # TODO: Possibly rework this name geneeation to include the name/
        #       contents of the source container. Currently, only the solute and
        #       solvent names are used. 
        if not name:
            name = Container._auto_generate_solution_name([solute], solvent)

        # For the following blocks of code, 'x' represents the source solution,
        # 's' represents the solute, and 'y' represents the solvent.

        # Compute the total mass, moles, and volume of all the substances in the 
        # source solution
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
            # Compute the total mass, moles, and volume of all the substances in 
            # the solvent
            mass = solvent.get_mass()
            moles = solvent.get_moles('mol')
            volume = Unit.convert_from_storage(solvent.volume, 'mL')

            # Compute the 'effective density', 'effective molecular weight', and
            # 'effective molar concentration' of the solvent. Density is in
            # units of 'g/mL', molecular weight is in terms of 'g/mol', and 
            # molar concentration is in terms of 'M' or 'mol/L'.
            d_y = mass / volume
            mw_y = mass / moles
            m_y = Unit.convert_from_storage(solvent.contents.get(solute, 0), 'mol') / (volume / 1000)
        
        # Otherwise, use the properties of the solvent substance.
        else:
            d_y = solvent.density
            mw_y = solvent.mol_weight
            m_y = 0  # There is no solute present in the case of a pure solvent

        # Get the molecular weight and density of the solute (the shorter names 
        # will be useful for condensing later lines of code)
        mw_s = solute.mol_weight
        d_s = solute.density

        # Parse the specified concentration into a concentration, numerator, and
        # denominator triplet
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
        # from mL of solution to (mol/g/L) of solution. Units other than mol, g,
        # or L in the quantity argument will raise an error.
        if quantity_value == 'mol':
            # Compute 'moles of solution' per 'mL of solution'
            a[1] = np.array([d_x / mw_x, d_y / mw_y])
        elif quantity_unit == 'g':
            # Compute 'grams of solution' per 'mL of solution'
            a[1] = np.array([d_x, d_y])
        elif quantity_unit == 'L':
            # Compute 'liters of solution' per 'mL of solution'
            # (this one is just a simple conversion ratio from mL to L)
            a[1] = np.array([1 / 1000., 1 / 1000.])
        else:
            raise ValueError("Invalid quantity unit.")

        # Set b[1] to the total quantity
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
