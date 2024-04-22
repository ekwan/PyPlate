.. _configuration:

Configuration
=============

pyplate.yaml location
"""""""""""""""""""""

``pyplate.yaml`` controls package behavior.  PyPlate will search for ``pyplate.yaml`` in the following locations in this order:

- The directory specified by the environment variable ``PYPLATE_CONFIG``
- The current working directory
- The user's home directory
- The package directory

The configuration file that is found first will take precedence.

Precision
"""""""""

The number of digits to display in the output can be controlled using the `precisions` option. Different precisions can be set for different units.

.. code-block:: yaml

    # How many digits of precision to return to the user
    precisions:
      default: 3
      uL: 0
      umol: 1
      mg: 1

The default precision is 3 digits. The precision for units `uL` is set to 0 because it is impossible to measure less than 1 `uL`. `umol`, and `mg` are set to 1 digit.


Internal Precision
""""""""""""""""""

Because floating point numbers are not exact, some rounding of numbers during intermediate calculations should occur. The number of digits to retain during intermediate calculations can be controlled using the `internal_precision` option.

.. code-block:: yaml

    # How many digits of precision to maintain in internal calculations
    internal_precision: 10

Storage Units
"""""""""""""

Amounts of substances and volumes can be stored with different units. The default units for these can be set using the `moles_storage_units` and `volume_storage_units` options.

.. code-block:: yaml

    # How to store volumes and moles internally
    # uL means we will store volumes as microliters
    volume_storage_unit: uL

    # umol means we will store moles as micromoles
    moles_storage_unit: umol

.. what are the implications of choosing different storage units?
.. when might someone want to do that?

Display Units
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

When specifying concentration in '%w/v', a default for the units for weight and volume is set using the `default_weight_volume_units` option.

.. code-block:: yaml

    # units for %w/v
    default_weight_volume_units: g/mL

Default Densities
"""""""""""""""""

Solids and enzymes have the same default densities for all objects.

- The default density for solids is set using the `default_solid_density` option.
- The default density for enzymes is set using the `default_enzyme_density` option.

.. code-block:: yaml

    # density for solids/enzymes in g/mL or U/mL. Can be set to float('inf') to give solids and enzymes zero volume.
    default_solid_density: 1
    default_enzyme_density: 1

Colormaps
"""""""""

For functions that return a styled DataFrame, the colormap can be set using the `colormap` option.

.. code-block:: yaml

    # default colormap to be used in visualizations
    default_colormap: Purples
    default_diverging_colormap: PuOr

The diverging colormap is used for functions that return a DataFrame with both positive and negative values.
