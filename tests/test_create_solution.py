import math
from itertools import product
from pyplate.pyplate import Unit, Container, config

epsilon = 1e-6


def test_create_solution(salt, water, triethylamine, dmso, sodium_sulfate, lipase):
    """

    Create a solution using each a quantity of each solvent and solute in each unit.
    Try "0.001 numerator/denominator" and "0.01 numerator/10 denominator"
    Ensure the correct amount of solvent, solute, and total solution is applied.
    Also try to create a "1.1 U/denominator" enzyme solution for each solvent.

    """
    solvents = [water, dmso]
    solutes = [salt, triethylamine, sodium_sulfate]
    units = ['g', 'mol', 'mL']
    for numerator, denominator, quantity_unit in product(units, repeat=3):
        for solute in solutes:
            for solvent in solvents:
                if numerator == 'mL' and solute.is_solid() and config.solid_density == float('inf'):
                    continue
                con = Container.create_solution(solute, solvent, concentration=f"0.001 {numerator}/{denominator}",
                                                total_quantity=f"10 {quantity_unit}")
                assert all(value > 0 for value in con.contents.values())
                total = sum(Unit.convert(substance, f"{value} {config.moles_prefix}", quantity_unit) for
                            substance, value in con.contents.items())
                assert abs(total - 10) < epsilon, f"Making 10 {quantity_unit} of a 0.001 {numerator}/{denominator}" \
                                                  f" solution of {solute} and {solvent} failed."
                conc = Unit.convert(solute, f"{con.contents[solute]} {config.moles_prefix}", numerator) / \
                    sum(Unit.convert(substance, f"{value} {config.moles_prefix}", denominator)
                        for substance, value in con.contents.items())
                assert abs(conc - 0.001) < epsilon

                con = Container.create_solution(solute, solvent, concentration=f"0.01 {numerator}/10 {denominator}",
                                                total_quantity=f"10 {quantity_unit}")
                total = sum(Unit.convert(substance, f"{value} {config.moles_prefix}", quantity_unit) for
                            substance, value in con.contents.items())
                assert abs(total - 10) < epsilon
                conc = Unit.convert(solute, f"{con.contents[solute]} {config.moles_prefix}", numerator) / \
                    sum(Unit.convert(substance, f"{value} {config.moles_prefix}", denominator)
                        for substance, value in con.contents.items())
                assert abs(conc - 0.01/10) < epsilon

    # Solute is an enzyme, concentration has U in the numerator
    solute = lipase
    for denominator, quantity_unit in product(units, repeat=2):
        for solvent in solvents:
            con = Container.create_solution(solute, solvent, concentration=f"1.1 U/{denominator}",
                                            total_quantity=f"10 {quantity_unit}")
            assert all(value > 0 for value in con.contents.values())
            total = sum(Unit.convert(substance, f"{value} {config.moles_prefix}", quantity_unit) for
                        substance, value in con.contents.items())
            assert abs(total - 10) < epsilon, f"Making 10 {quantity_unit} of a 1.1 U/{denominator}" \
                                              f" solution of {solute} and {solvent} failed."
            conc = con.contents[solute] / \
                sum(Unit.convert(substance, f"{value} {config.moles_prefix}", denominator)
                    for substance, value in con.contents.items())
            assert abs(conc - 1.1) < epsilon
