.. _locations:

Locations on a Plate and slices
===============================

PyPlate follows the ``pandas`` convention of having both integer- and
label-based indices for referencing wells in ``Plate``\ s.

- When row or column specifiers are provided as integers, they are assumed to be integer indices (1, 2, 3, …).
- Integer indices are 1-based, meaning that the first row or column is referred to as 1, not 0.
- When specifiers are provided as strings, they are assumed to be label indices (“A”, “B”, “C”, …).

- By default, rows in plates are given alphabetical labels “A”, “B”, “C”, and columns in plates are given numerical labels “1”, “2”, “3”.
- However, rows and columns are always given integer indices 1, 2, 3, ….

Here are some ways to refer to a specific well:

-  **String Method**: ``“A:1”``
-  **Tuple Method**: ``(‘A’, 1)``

Here are some alternate ways to refer to well B3:

.. hlist::
    :columns: 3

    - ``“B:3”``
    - ``('B', 3)``
    - ``(2,3)``

You can refer to multiple wells as a list::

    plate[[('A', 1), ('B', 2), ('C', 3), 'D:4']] or plate[['A1, 'B2', 'C3', 'D4']]

.. image:: /images/wells_A1_B2_C3_D4.png

Slice Notation
--------------

To get a range of rows, you can use the following syntax:

-  ``plate['A':'C']`` will return rows 1, 2, and 3 ('A', 'B', and 'C').
-  ``plate[1:3]`` will return rows 1, 2, and 3.

   .. image:: /images/rows_A_C.png
-  ``plate['D':]`` will return rows 4, 5, 6 ... to the end of the plate.

   .. image:: /images/rows_D_end.png

To get a range of columns, you can use the following syntax:

-  ``plate[:, '1':'3']`` will return columns 1, 2, and 3 ('1', '2', and '3').
-  ``plate[:, 1:3]`` will return columns 1, 2, 3.

   .. image:: /images/cols_1_3.png
-  ``plate[:, '4':]`` will return columns 4, 5, 6 ... to the end of the plate.

   .. image:: /images/cols_4_end.png


You can get a rectangular slice of the plate by using both row and column slices:

-  ``plate['A':'C', '1':'3']`` will return the region bound by 'A:1' to 'C:3' inclusive.

   .. image:: /images/wells_A1_C3.png

- To make a rectangular slice of ``B2`` to ``D3``, you can use::

    plate['B':'D', 2:3]

  This will be three rows of two columns, specifically referring to ``B2``, ``B3``, ``C2``, ``C3``, ``D2``, and ``D3``.

  .. image:: /images/wells_B2_D3.png
