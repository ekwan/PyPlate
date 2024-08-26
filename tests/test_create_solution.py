import math
from itertools import product
from pyplate import Unit, Container, config

epsilon = 1e-3


def test_create_solution(salt, water, triethylamine, dmso, sodium_sulfate):
    """

    Create a solution using each a quantity of each solvent and solute in each unit.
    Try "0.001 numerator/denominator" and "0.01 numerator/10 denominator"
    Ensure the correct amount of solvent, solute, and total solution is applied.

    """
    solvents = [water, dmso]
    solutes = [salt, triethylamine, sodium_sulfate]
    units = ['g', 'mol', 'mL']
    for numerator, denominator, quantity_unit in product(units, repeat=3):
        for solute in solutes:
            for solvent in solvents:
                if numerator == 'mL' and solute.is_solid() and config.default_solid_density == float('inf'):
                    continue
                con = Container.create_solution(solute, solvent, concentration=f"0.001 {numerator}/{denominator}",
                                                total_quantity=f"10 {quantity_unit}")
                assert all(value > 0 for value in con.contents.values())
                total = sum(Unit.convert(substance, f"{value} {config.moles_storage_unit}", quantity_unit) for
                            substance, value in con.contents.items())
                assert abs(total - 10) < epsilon, f"Making 10 {quantity_unit} of a 0.001 {numerator}/{denominator}" \
                                                  f" solution of {solute} and {solvent} failed."
                conc = con.get_concentration(solute, f"{numerator}/{denominator}")
                assert abs(conc - 0.001) < epsilon, f"{solute} and {solvent} failed to create a 0.001 {numerator}/{denominator}"

                con = Container.create_solution(solute, solvent, concentration=f"0.01 {numerator}/10 {denominator}",
                                                total_quantity=f"10 {quantity_unit}")
                total = 0
                for substance, value in con.contents.items():
                    total += Unit.convert_from(substance, value, config.moles_storage_unit, quantity_unit)
                assert abs(total - 10) < epsilon
                conc = con.get_concentration(solute, f"{numerator}/{denominator}")
                assert abs(conc - 0.01/10) < epsilon


