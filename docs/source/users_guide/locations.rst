.. _locations:

Locations on a Plate and slices
===============================

PyPlate follows the ``pandas`` convention of having both integer- and
label-based indices for referencing wells in ``Plate``\ s.

- When row or column specifiers are provided as integers, they are assumed to be integer indices (1, 2, 3, …).
- When specifiers are provided as strings, they are assumed to be label indices (“A”, “B”, “C”, …).

- By default, rows in plates are given alphabetical labels “A”, “B”, “C”, and columns in plates are given numerical labels “1”, “2”, “3”.
- However, rows and columns are always given integer indices 1, 2, 3, ….

Here are some ways to refer to a specific well:

-  **String Method**: ``“A:1”``
-  **Tuple Method**: ``(‘A’, 1)``

Here are some alternate ways to refer to well B3:

.. _hlist

- ``“B:3”``
- ``('B', 3)``
- ``(2,3)``

You can refer to multiple wells as a list::

    plate[[('A', 1), ('B', 2), ('C', 3), 'D:4']] or plate[['A1, 'B2', 'C3', 'D4']]

Slicing syntax is supported:

-  You can provide python slices of wells with 1-based or label-based
   indexes::

    plate[:3], plate[:, :3], plate['C':], plate[1, '3':], plate['A':'D', :]

- To make a rectangular slice of ``B2`` to ``D3``, you can use::

    plate['B':'D', 2:3]

  This will be two rows of three columns, specifically referring to ``B2``, ``B3``, ``C2``, ``C3``, ``D2``, and ``D3``.
