import re

class Substance:
    SOLID = 1
    LIQUID = 2
    ENZYME = 3

    next_id = 0

    def __init__(self, name, type):
        self.id = Substance.next_id
        Substance.next_id += 1
        self.name = name
        self.type = type

    @staticmethod
    def solid(name, mol_weight):
        substance = Substance(name, Substance.SOLID)
        substance.mol_weight = mol_weight
        return substance

    @staticmethod
    def liquid(name, mol_weight, density):
        substance = Substance(name, Substance.LIQUID)
        substance.mol_weight = mol_weight               # g / mol
        substance.density = density                     # g / mL
        substance.mol_per_mL = density / mol_weight
        return substance

    @staticmethod
    def enzyme(name):
        return Substance(name, Substance.ENZYME)


    def convert_to_unit_value(self, amount):  # mol, mL or AU
        if not isinstance(amount, srt):
            raise TypeError
        match = re.fullmatch(r"([\d.]+(?>[eE]\d+)?)\s*([a-zA-Z]+)", amount)
        if not match:
            raise ValueError
        value, unit = float(match.group(0)), match.group(1)
        if self.type == Substance:
            pass

class Mixture:
    next_id = 0

    def __init__(self,name):
        self.name = name
        self.id = Substance.next_id
        Substance.next_id += 1

    def __iadd__(self, other):
        assert isinstance(other, tuple) and len(other) == 2,\
            "You must specify a Substance or Mixture and an amount to add"
        assert isinstance(other[0], (Substance, Mixture)), "You must specify a Substance or Mixture"
        assert isinstance(other[1], str), "You must specify an amount (i.e., \"10 mL\")"

        match = re.match(r"([\d.]+)\s*([a-zA-Z]+)", str)
        assert match, "You must specify an amount (i.e., \"10 mL\")"

        if isinstance(other[0], Substance):
