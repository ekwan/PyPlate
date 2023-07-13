import re
import copy
from typing import Tuple, Dict


def convert_prefix(prefix):
    match prefix:
        case 'µ':
            return 1e-6
        case 'm':
            return 1e-3
        case 'c':
            return 1e-2
        case 'd':
            return 1e-1
        case '':
            return 1
        case 'k':
            return 1e3
        case 'M':
            return 1e6

def _split_value_unit(s: str):
    if not isinstance(s, str):
        raise TypeError
    match = re.fullmatch(r"(\d+(?:\.\d+)?(?:e-?\d+)?)\s*([a-zA-Z]+)", s)
    if not match:
        raise ValueError
    value, unit = match.groups()
    value = float(value)
    return value, unit


class Substance:
    SOLID = 1
    LIQUID = 2
    ENZYME = 3

    next_id = 0

    def __init__(self, name, mol_type):
        self.id = Substance.next_id
        Substance.next_id += 1
        self.name = name
        self.type = mol_type
        self.mol_weight = self.density = self.concentration = None

    def __repr__(self):
        if self.type == Substance.SOLID:
            return f"SOLID ({self.name}: {self.mol_weight})"
        if self.type == Substance.LIQUID:
            return f"LIQUID ({self.name}: {self.mol_weight}, {self.density})"
        else:
            return f"ENZYME ({self.name})"
    @staticmethod
    def solid(name, mol_weight):
        substance = Substance(name, Substance.SOLID)
        substance.mol_weight = mol_weight
        return substance

    @staticmethod
    def liquid(name, mol_weight, density):
        substance = Substance(name, Substance.LIQUID)
        substance.mol_weight = mol_weight  # g / mol
        substance.density = density  # g / mL
        substance.concentration = 1000.0 * density / mol_weight  # mol / L
        return substance

    @staticmethod
    def enzyme(name):
        return Substance(name, Substance.ENZYME)

    def convert_to_unit_value(self, amount: str, volume: float = 0.0):  # mol, mL or AU
        """
        Converts amount to standard units.

        :param amount: Amount of substance to convert
        :param volume: Volume of containing Mixture in mL
        :return: float

                 +--------+--------+--------+--------+--------+--------+
                 |              Valid Input                   | Output |
                 |    g   |    L   |   mol  |    M   |    AU  |        |
        +--------+--------+--------+--------+--------+--------+--------+
        |SOLID   |   Yes  |   No   |   Yes  |   Yes  |   No   |   mol  |
        +--------+--------+--------+--------+--------+--------+--------+
        |LIQUID  |   Yes  |   Yes  |   Yes  |   No   |   No   |   mL   |
        +--------+--------+--------+--------+--------+--------+--------+
        |ENZYME  |   No   |   No   |   No   |   No   |   Yes  |   AU   |
        +--------+--------+--------+--------+--------+--------+--------+
        """

        value, unit = _split_value_unit(amount)
        if self.type == Substance.SOLID:  # Convert to moles
            if unit[-1] == 'g':  # mass
                grams = value * convert_prefix(unit[:-1])
                return grams / self.mol_weight
            elif unit.endswith('mol'):  # moles
                return value * convert_prefix(unit[:-3])
            elif unit[-1] == 'M':  # molar
                molar = value * convert_prefix(unit[:-1])
                if volume <= 0.0:
                    raise ValueError('Must have a liquid to add a molar concentration.')
                return 1000 * molar * volume  # moles
            raise ValueError
        elif self.type == Substance.LIQUID:  # Convert to mL
            if unit[-1] == 'g':  # mass
                grams = value * convert_prefix(unit[:-1])
                return grams / self.density
            elif unit[-1] == 'L':  # volume
                liters = value * convert_prefix(unit[:-1])
                return liters * 1000
            elif unit.endswith('mol'):  # moles
                moles = value * convert_prefix(unit[:-3])
                return (moles / self.concentration) / 1000.0
            raise ValueError
        elif self.type == Substance.ENZYME:
            if unit == 'AU':
                return value
            raise ValueError


class Mixture:
    next_id = 0

    def __init__(self, other):
        if isinstance(other, Mixture):
            self.name = other.name
            self.contents = other.contents.copy()
            self.volume = other.volume
        else:
            self.name = other
            self.contents: Dict[int, Tuple[Substance, float, float, float]] = dict()
            self.volume = 0.0
        self.id = Substance.next_id
        Substance.next_id += 1

    def __add__(self, other):
        assert isinstance(other, tuple) and len(other) == 2, \
            'You must specify a Substance or Mixture and an amount to add'
        other, raw_value = other
        assert isinstance(other, (Substance, Mixture)), 'You must specify a Substance or Mixture'
        assert isinstance(raw_value, str), 'You must specify an amount (i.e., "10 mL")'
        new_mixture = Mixture(self)
        if isinstance(other, Substance):
            substance: Substance = other
            adding: Tuple[Substance, float, float, float] = None
            amount = substance.convert_to_unit_value(raw_value, self.volume)
            if substance.type == Substance.LIQUID:
                volume = amount  # in mL
                moles = volume * substance.concentration / 1000.0
                # mol, volume, AU
                adding = (substance, moles, volume, 0)
                new_mixture.volume += volume
            elif substance.type == Substance.SOLID:
                adding = (substance, amount, 0, 0)
            elif substance.type == Substance.ENZYME:
                adding = (substance, 0, 0, amount)
            if substance.id in new_mixture.contents:
                old = new_mixture.contents[substance.id]
                new_mixture.contents[substance.id] = (substance, old[1] + adding[1], old[2] + adding[2], old[3] + adding[3])
            else:
                new_mixture.contents[substance.id] = adding
        else:  # Mixture
            value, unit = _split_value_unit(raw_value)
            mixture: Mixture = other
            if mixture.volume:
                # TODO: ask Eugene about this.
                if unit[-1] != 'L' or len(unit) > 2:
                    raise ValueError('You can only add liquid mixtures by volume to another mixture')
                value = float(value) * convert_prefix(unit[:-1])
                # if value > mixture.volume:
                #     raise ValueError('Volume exceeds available amount')
                # TODO: I'll use the volume of mixture merely for concentration purposes
                ratio = 1000 * value / mixture.volume   # value is in L
                new_mixture = Mixture(self)
                for substance, mass, volume, au in mixture.contents.values():
                    old: Tuple[Substance, float, float, float] = self.contents.get(substance.id, (substance, 0, 0, 0))
                    new_mixture.contents[substance.id] = (substance, old[1] + mass * ratio,
                                                          old[2] + volume * ratio, old[3] + au * ratio)
                    new_mixture.volume += volume * ratio
            else:
                raise ValueError('You can only add a liquid Mixture to another Mixture')
        return new_mixture


    # def __iadd__(self, other):
    # def __setitem__(self, key, value):
    #     assert key == self
