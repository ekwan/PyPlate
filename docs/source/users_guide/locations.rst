.. _locations:

Locations on a Plate and slices
===============================

PyPlate follows the ``pandas`` convention of having both integer- and
label-based indices for referencing wells in ``Plate``\ s. When row or
column specifiers are provided as integers, they are assumed to be
integer indices (1, 2, 3, …). When specifiers are provided as strings,
they are assumed to be label indices (“A”, “B”, “C”, …).

By default, rows in plates are given alphabetical labels “A”, “B”, “C”,
… and columns in plates are given numerical labels “1”, “2”, “3”.
However, rows and columns are always given integer indices 1, 2, 3, ….
For example, ``“B:3”``, ``('B', 3)``, and ``(2,3)`` all refer to well B3.

Here are some ways to refer to a specific well:

-  **String Method**: ``“A:1”``
-  **Tuple Method**: ``(‘A’, 1)``

You can refer to multiple wells as a list::

    plate[[('A', 1), ('B', 2), ('C', 3), 'D:4']]

Slicing syntax is supported:

-  In addition, you can provide python slices of wells with 1-based or label-based
   indexes::

    plate[:3], plate[:, :3], plate['C':], plate[1, '3':]

