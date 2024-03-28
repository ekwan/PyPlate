Unit
====

The `Unit` class provides several convenience functions for developers of PyPlate.

`Unit.convert_from(def convert_from(substance: Substance, quantity: float, from_unit: str, to_unit: str) -> float`

Converts a quantity of a substance from one unit to another.

Example:

- `(water, 1, 'mol', 'mL')` -> `18.015`

-----------------------------------

`Unit.convert_from_storage(value: float, unit: str) -> float`

Moles and volumes are stored internally in units as defined in pyplate.yaml.

Use this function to convert these values to a desired prefix.

Examples:

- `(1, 'uL')` -> `1`      (assuming uL is the storage unit for volume)
- `(1, 'mol')` -> `1e-6`  (assuming umol is the storage unit for moles)

-----------------------------------

`Unit.convert_from_storage_to_standard_format(what: Substance | Container, quantity: float) -> Tuple[float, str]``

Converts a quantity of a substance or container to a standard format (liquids and containers as liters, solids as grams, enzymes as activity units).

Examples: (Assumes that the storage unit for volume is uL, and for moles is umol)

- `(water, 1e6)` -> `(18.015, 'mL')`
- `(NaCl, 1e6)` -> `(58.443, 'g')`
- `(Amylase, 1)` -> `(1, 'U')`
- `(salt_water, 1)` -> `(1, 'uL')`

-----------------------------------

`Unit.get_human_readable_unit(value: float, unit: str) -> Tuple[float, str]`

Scales a value to be human readable.

Examples:

- `(.001, 'mol')` -> `(1.0, 'mmol')``
- `(1e-6, 'L')` -> `(1.0, 'uL')``