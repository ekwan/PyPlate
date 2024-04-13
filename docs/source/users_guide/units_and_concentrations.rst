.. _units_and_concentrations:

Units and Concentrations
========================

Units
"""""

- There are three types of units in pyplate:

  - Mass

    - grams (g, mg, ug)

  - Volume

    - liters (L, mL, uL)

  - Numbers

    - moles (mol, mmol, umol)
    - Enzyme Activity units (U)


PyPlate supports these common prefixes:

.. hlist::
    :columns: 3

    - 'p' (pico)
    - 'n' (nano)
    - 'u' (micro)
    - 'm' (milli)
    - 'k' (kilo)
    - 'M' (mega)


- Quantities are specified as strings with a number and a unit abbreviation. (‘1 mmol’, ‘10.2 g’, ‘10 uL’, …)

Concentrations
""""""""""""""

Concentrations can be defined in terms of molarity, molality, or ratios of units:

Examples ('w' stands for weight, 'v' stands for volume, '%' stands for per hundred):

.. hlist::
    :columns: 3

    - '0.1 M'
    - '0.1 m'
    - '0.1 g/mL'
    - '0.01 umol/10 uL'
    - '5 %v/v'
    - '5 %w/v'
    - '5 %w/w'

.. note:: For '%w/v', the units are defined as ``default_weight_volume_units`` in the configuration file.
    (The default is 'g/mL')


Unit Usage within PyPlate
"""""""""""""""""""""""""
.. PyPlate uses the `pint <https://pint.readthedocs.io/en/stable/>`_ library to handle units and conversions.

- The fundamental unit for liquids and solids is moles.

  - Mass is calculated using the molecular weight of the substance.
  - Volume is calculated using the density and molecular weight of the substance.

- The fundamental unit for enzymes is enzyme activity units ('U').

  - Enzymes must be defined in terms of activity units per mass.

- Masses and volumes are considered to be strictly additive.
