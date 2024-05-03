Unit Conversion Utilities
=========================

The `Unit` class provides several convenience functions for developers of PyPlate.


convert_from
""""""""""""

To convert a float quantity from one unit to another, use the `convert_from` function:

>>> print(Unit.convert_from(substance=water, quantity=1, from_unit='mol', to_unit='mL'))
18.0153

>>> print(Unit.convert_from(substance=water, quantity=18.0153, from_unit='g', to_unit='mol'))
1.0

This function should be the most used function for converting between units. |br|
`config.moles_storage_unit` or `config.volume_storage_unit` can be passed as `from_unit` to convert from the internal storage unit.

convert
"""""""

`convert` is a wrapper for `convert_from` that automatically parses a quantity string into a float and unit.

>>> print(Unit.convert(substance=water, quantity='1 mol', to_unit='mL'))
18.0153

convert_from_storage
""""""""""""""""""""

Moles and volumes are stored internally in units as defined in pyplate.yaml.

- Moles are stored in `moles_storage_unit` (default: umol)
- Volumes are stored in `volume_storage_unit` (default: uL)
- Activity units are stored in 'U'

Use the `convert_from_storage` function to convert these values to a desired prefix:

>>> print(Unit.convert_from_storage(value=1, unit='mL'))
0.001

>>> print(Unit.convert_from_storage(value=1, unit='mol'))
1e-06

convert_to_storage
""""""""""""""""""

Use the `convert_to_storage` function to convert a quantity to the internal storage unit:

>>> print(Unit.convert_to_storage(value=1, unit='mL'))
1000.0

>>> print(Unit.convert_to_storage(value=1, unit='mol'))
1000000.0

convert_from_storage_to_standard_format
"""""""""""""""""""""""""""""""""""""""

If you have a substance or a container and a storage quantity, you can convert it to a standard format (liquids and containers as liters, solids as grams, enzymes as activity units) using the `convert_from_storage_to_standard_format` function:

- This automatically scales the quantity to a human readable format. It will return 18.015 mL instead of 0.018015 L.
- The return values are rounded in accordance with `precisions` in pyplate.yaml.
- These examples assume the default configuration of `moles_storage_unit` and `volume_storage_unit` as umol and uL respectively.

>>> print(Unit.convert_from_storage_to_standard_format(what=water, quantity=1e6))
(18.015, 'mL')

>>> print(Unit.convert_from_storage_to_standard_format(what=NaCl, quantity=1e6))
(58.443, 'g')

>>> print(Unit.convert_from_storage_to_standard_format(what=Amylase, quantity=1))
(1, 'U')

>>> print(Unit.convert_from_storage_to_standard_format(what=salt_water, quantity=1))
(1, 'uL')

get_human_readable_unit
"""""""""""""""""""""""

Given a value and a unit, scales the value to a human readable format.

- It does not round the value.

>>> print(Unit.get_human_readable_unit(value=1e-6, unit='L'))
(1.0, 'uL')

>>> print(Unit.get_human_readable_unit(value=1e-3, unit='mol'))
(1.0, 'mmol')

>>> print(Unit.get_human_readable_unit(value=.123456789, unit='g'))
(123.456789, 'mg')
