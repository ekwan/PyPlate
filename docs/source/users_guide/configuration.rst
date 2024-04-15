.. _configuration:

Configuration
=============

pyplate.yaml location
"""""""""""""""""""""

Various configuration options are available to control the behavior of the package. They are stored in a yaml file named `pyplate.yaml`. The default configuration file is located in the package directory.
|br| A custom configuration file can be created. The package will look for the configuration file in the following order:

- A directory specified by the environment variable `PYPLATE_CONFIG`
- The current working directory
- The user's home directory

Precision
"""""""""

The number of digits to display in the output can be controlled using the `precisions` option. Different precisions can be set for different units.

.. code-block:: yaml

    # How many digits of precision to return to the user
    precisions:
      default: 3
      uL: 1
      umol: 1
      mg: 2

The default precision is 3 digits. The precision for units `uL`, `umol`, and `mg` are set to 1, 1, and 2 digits respectively.

Because floating point numbers are not exact, some rounding of numbers during intermediate calculations should occur. The number of digits to retain during intermediate calculations can be controlled using the `internal_precision` option.

.. code-block:: yaml

    # How many digits of precision to maintain in internal calculations
    internal_precision: 10

Default Units
"""""""""""""

Amounts of substances and volumes can be stored with different units. The default units for these can be set using the `moles_storage_units` and `volume_storage_units` options.

.. code-block:: yaml

    # How to store volumes and moles internally
    # uL means we will store volumes as microliters
    volume_storage_unit: uL

    # umol means we will store moles as micromoles
    moles_storage_unit: umol

Default Units
"""""""""""""

In many of PyPlate's functions, the user can specify which units to return data in.
- `volume_display_unit` specifies the default unit for displaying volumes.
- `moles_display_unit` specifies the default unit for displaying moles.
- `concentration_display_unit` specifies the default unit for displaying concentrations.

.. code-block:: yaml

    # uL means we will return volumes as microliters
    volume_display_unit: uL

    # umol means we will return moles as micromoles
    moles_display_unit: umol

    # Default concentration unit for get_concentration()
    concentration_display_unit: M

Concentration Units
"""""""""""""""""""

When specifying concentration in '%w/v', a default for the units for weight and volume is set using the `default_weight_Volume_units` option.

.. code-block:: yaml

    # units for %w/v
    default_weight_volume_units: g/mL

Colormaps
"""""""""

For functions that return a styled DataFrame, the colormap can be set using the `colormap` option.

.. code-block:: yaml

    # default colormap to be used in visualizations
    default_colormap: Purples
    default_diverging_colormap: PuOr

The diverging colormap is used for functions that return a DataFrame with both positive and negative values.
