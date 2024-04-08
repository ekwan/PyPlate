Introduction
============

The *PyPlate* Python API defines a set of objects and operations for
implementing a high-throughput screen of chemical or biological
conditions. *PyPlate* assists with the enumeration of solid or liquid
handling steps, ensures that those steps are physically reasonable, and
provides plate visualization capabilities.

Scope
"""""

*PyPlate* specifically focuses on the implementation of high-throughput
experimentation (HTE). The upstream process of designing the screens
themselves will be handled elsewhere. Similarly, the downstream process
of analyzing the outcomes of screens will also be handled elsewhere.

External Classes
""""""""""""""""

Four simple HTE classes will be exposed to the user: ``Substance``,
``Container``, ``Plate``, and ``Recipe``. *All classes are immutable.*
(An immutable object is one whose fields cannot be changed once it has
been constructed.)

Note: all quantity, volume, and max_volume parameters are given as
strings. For example, ‘10 mL’, ‘5 g’, ‘1 mol’, or ‘11 U’.

The following are set based on preferences read ``pyplate.yaml``:

-  Units in which moles and volumes are stored internally.
   ``moles_storage_unit`` and ``volume_storage_unit``
-  Default units to be returned to the user. ``moles_display_unit`` and
   ``volume_display_unit``
-  Density of solids in g/mL. ``default_solid_density``
-  Density of enzymes in U/mL. ``default_enzyme_density``
-  Units for ‘%w/v’ concentrations (‘g/mL’).
   ``default_weight_volume_units``
-  Default colormap and diverging colormap. ``default_colormap`` and
   ``default_diverging_colormap``
-  Default number of digits of precision for different units.
   ``precisions``
