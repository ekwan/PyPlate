.. _units_and_concentrations:

Units and Concentrations
========================

Units
"""""

* Units are specified as strings with a number and a unit abbreviation. (‘1 mmol’, ‘10.2 g’, ‘10 uL’, …)
* The basic units of pyplate are moles, grams, liters, and activity units. (‘mol’, ‘g’, ‘L’, ‘U’)
* Any time units are required, metric prefixes may be specified. (‘mg’, ‘umol’, ‘dL’, …)

Concentrations
""""""""""""""

Concentration can be define in molarity, molality, or in ratio of units:

Examples:

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