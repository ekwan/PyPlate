from pyplate.pyplate import Unit, Container, config

epsilon = 1e-6


def test_create_solution(salt, water, triethylamine, dmso, sodium_sulfate):
    solvents = [water, dmso]
    solutes = [salt, triethylamine, sodium_sulfate]
    units = ['g', 'mol', 'mL']
    for numerator in units:
        for denominator in units:
            for quantity_unit in units:
                for solute in solutes:
                    for solvent in solvents:
                        con = Container.create_solution(solute, f"0.001 {numerator}/{denominator}",
                                                        solvent, f"10 {quantity_unit}")
                        total = sum(Unit.convert(substance, f"{value} {config.moles_prefix}", quantity_unit) for
                                    substance, value in con.contents.items())
                        assert abs(total - 10) < epsilon
                        conc = Unit.convert(solute, f"{con.contents[solute]} {config.moles_prefix}", numerator) / \
                            sum(Unit.convert(substance, f"{value} {config.moles_prefix}", denominator)
                                for substance, value in con.contents.items())
                        assert abs(conc - 0.001) < epsilon

                        con = Container.create_solution(solute, f"0.01 {numerator}/10 {denominator}",
                                                        solvent, f"10 {quantity_unit}")
                        total = sum(Unit.convert(substance, f"{value} {config.moles_prefix}", quantity_unit) for
                                    substance, value in con.contents.items())
                        assert abs(total - 10) < epsilon
                        conc = Unit.convert(solute, f"{con.contents[solute]} {config.moles_prefix}", numerator) / \
                            sum(Unit.convert(substance, f"{value} {config.moles_prefix}", denominator)
                                for substance, value in con.contents.items())
                        assert abs(conc - 0.01/10) < epsilon
