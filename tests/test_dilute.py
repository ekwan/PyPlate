from itertools import product
import pytest
from pyplate.pyplate import Container, Unit, config


def test_dilute(salt, sodium_sulfate, triethylamine, water, dmso):
    solvents = [water, dmso]
    solutes = [salt, triethylamine, sodium_sulfate]
    units = ['g', 'mol', 'mL']
    for numerator, denominator, quantity_unit in product(units, repeat=3):
        for solute in solutes:
            for solvent in solvents:
                con = Container.create_solution(solute, f"0.001 {numerator}/{denominator}",
                                                solvent, f"10 {quantity_unit}")
                con2 = con.dilute(solute, f'0.0005 {numerator}/{denominator}', solvent)
                new_concentration = Unit.convert(solute, f"{con2.contents[solute]} {config.moles_prefix}", numerator) / \
                                    sum(Unit.convert(substance, f"{value} {config.moles_prefix}", denominator)
                                        for substance, value in con2.contents.items())
                assert new_concentration == pytest.approx(0.0005)
