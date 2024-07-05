Dilute
""""""

Currently ``Container.dilute(solute, concentration, solvent, name)`` consumes all of the source container.

We use create_solution_from to use some of the source container to create a new container with a different concentration.

I propose we combine these into a new ``dilute()`` function.

This is an example of dilute::

    salt_water = Container.create_solution(solute=salt, solvent=water, concentration='1 mol/L', total_quantity='100 mL')
    salt_water = salt_water.dilute(solute=salt, solvent=water, concentration='0.5 M')

 >>> salt_water
    +-------------------------+------------+-----------+------------+-----+
    | Solution of NaCl in H2O |   Volume   |   Mass    |   Moles    |  U  |
    +-------------------------+------------+-----------+------------+-----+
    |     Maximum Volume      |     ∞      |     -     |     -      |  -  |
    |          NaCl           |  5.844 mL  |  5.844 g  | 100.0 mmol |  -  |
    |           H2O           | 194.156 mL | 194.156 g | 10.777 mol |  -  |
    |          Total          |  200.0 mL  |  200.0 g  | 10.877 mol | 0 U |
    +-------------------------+------------+-----------+------------+-----+

>>> salt_water.get_concentration(solute=salt, units='M')
0.5 M


This is an example of create_solution_from::

    salt_water1M = Container.create_solution(name='salt water (1 M)', solute=salt, solvent=water, concentration='1 M', quantity='100 mL')

    salt_water1M, salt_water500mM = Container.create_solution_from(name='salt water (0.5 M)', source=salt_water1M, solute=salt,
                                                                   solvent=water, concentration='0.5 M', quantity='10 mL')


>>> salt_water1M
    +------------------+-----------+----------+-----------+-----+
    | salt water (1 M) |  Volume   |   Mass   |   Moles   |  U  |
    +------------------+-----------+----------+-----------+-----+
    |  Maximum Volume  |     ∞     |    -     |     -     |  -  |
    |       NaCl       | 5.552 mL  | 5.552 g  | 95.0 mmol |  -  |
    |       H2O        | 89.448 mL | 89.448 g | 4.965 mol |  -  |
    |      Total       |  95.0 mL  |  95.0 g  | 5.06 mol  | 0 U |
    +------------------+-----------+----------+-----------+-----+

>>> salt_water500mM
    +--------------------+----------+----------+--------------+-----+
    | salt water (0.5 M) |  Volume  |   Mass   |    Moles     |  U  |
    +--------------------+----------+----------+--------------+-----+
    |   Maximum Volume   |    ∞     |    -     |      -       |  -  |
    |        H2O         | 9.708 mL | 9.708 g  | 538.865 mmol |  -  |
    |        NaCl        | 292.0 uL | 292.2 mg |   5.0 mmol   |  -  |
    |       Total        | 10.0 mL  |  10.0 g  | 543.865 mmol | 0 U |
    +--------------------+----------+----------+--------------+-----+

5 mL of the 100mL of 1M solution was used to create a 10 mL 0.5M solution, leaving 95 mL of the 1M solution.


I propose the following:

- ``dilute()`` should be a method of the container class.
- ``dilute()`` should take the following arguments:

  - solute
  - solvent
  - concentration
  - name
  - quantity (optional)
- If quantity is not provided, the container will be diluted to the maximum volume.
- If quantity is provided, the container will be diluted to the specified quantity.
- If the quantity is greater than the maximum volume, an exception will be raised.
- The function will return an (new) updated version of the original container and the new container.

The full dilute example will now be::

    salt_water = Container.create_solution(solute=salt, solvent=water, concentration='1 mol/L', total_quantity='100 mL')
    _, salt_water = salt_water.dilute(solute=salt, solvent=water, concentration='0.5 M')

The partial dilute example will now be::

    salt_water1M = Container.create_solution(name='salt water (1 M)', solute=salt, solvent=water, concentration='1 M', total_quantity='100 mL')
    salt_water1M, salt_water500mM = salt_water1M.dilute(solute=salt, solvent=water, concentration='0.5 M', quantity='10 mL')
