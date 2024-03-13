SOLUTION FORMULAS
=================

Formulas used in calculate_concentration_ratio and create_solution to determine
how much solute and solvent are needed to create a solution of a given
concentration.

x = solute in moles, y = solvent in moles

:math:`MW_x` = molecular weight of solute, :math:`d_x` = density of solute

:math:`MW_y` = molecular weight of solvent, :math:`d_y` = density of solvent

----------------------------------------------------

:math:`c` = concentration in :math:`\frac{g}{g}`

:math:`c = \frac{g}{g} = \frac{x\cdot MW_x}{x\cdot MW_x + y\cdot MW_y}`

:math:`c\cdot x\cdot MW_x + c\cdot y\cdot MW_y = x\cdot MW_x`

:math:`c\cdot y\cdot MW_y = x\cdot MW_x (1-c)`

:math:`\frac{x}{y} = \frac{c\cdot MW_y}{(1-c)MW_x}`

----------------------------------------------------

:math:`c` = concentration in :math:`\frac{g}{mol}`

:math:`c = \frac{g}{mol} = \frac{x\cdot MW_x}{x+y}`

:math:`c\cdot x + c\cdot y = x\cdot MW_x`

:math:`c\cdot y = x(MW_x-c)`

:math:`\frac{x}{y} = \frac{x}{MW_x -c}`

----------------------------------------------------

:math:`c` = concentration in :math:`\frac{g}{L}`

:math:`c = \frac{g}{L}\cdot \frac{1 L}{1000 mL} = \frac{g}{mL}`

:math:`c = \frac{x\cdot MW_x}{x\cdot MW_x/d_x + y\cdot MW_y/d_y}`

:math:`c\cdot x\cdot MW_x/d_y + c\cdot y\cdot MW_y/d_y = x\cdot MW_x`

:math:`c\cdot y\cdot MW_y/d_y = x\cdot MW_x(1-c/d_y)`

:math:`\frac{x}{y} = \frac{c\cdot MW_y}{MW_x\cdot d_y(1-c/d_x)}`

----------------------------------------------------

:math:`c` = concentration in :math:`\frac{mol}{L}`

:math:`c = \frac{L}{g}\cdot \frac{1000 mL}{1 L} = \frac{mL}{g}`

:math:`c = \frac{x\cdot MW_x/d_x}{x\cdot MW_x + y\cdot MW_y}`

:math:`c\cdot x\cdot MW_x + c\cdot y\cdot MW_y = x\cdot MW_x/d_x`

:math:`c\cdot y\cdot MW_y = x\cdot MW_x(1/d_x-c)`

:math:`\frac{x}{y} = \frac{c\cdot MW_y}{MW_x(1/d_x-c)}`

----------------------------------------------------

:math:`c` = concentration in :math:`\frac{L}{mol}`

:math:`c = \frac{L}{mol}\cdot \frac{1000 mL}{1 L} = \frac{mL}{mol}`

:math:`c = \frac{x\cdot MW_x/d_x}{x + y}`

:math:`c\cdot x + c\cdot y = x\cdot MW_x/d_x`

:math:`c\cdot y = x(MW_x/d_x - c)`

:math:`\frac{x}{y} = \frac{c}{MW_x/d_x-c}`

----------------------------------------------------

:math:`c` = concentration in :math:`\frac{L}{L}`

:math:`c = \frac{L}{L} = \frac{x\cdot MW_x/d_x}{x\cdot MW_x/d_x + y\cdot MW_y/d_y}`

:math:`c\cdot x\cdot MW_x/d_x + c\cdot y\cdot MW_y/d_y = x\cdot MW_x/d_x`

:math:`c\cdot y\cdot MW_y/d_y = (1-c)x\cdot MW_x/d_x`

:math:`\frac{x}{y} = \frac{c\cdot MW_y/d_y}{(1-c)MW_x/d_x}`

----------------------------------------------------

:math:`c` = concentration in :math:`\frac{mol}{g}`

:math:`c = \frac{mol}{g} = \frac{x}{x\cdot MW_x + y\cdot MW_y}`

:math:`x = c\cdot x\cdot MW_x + c\cdot y\cdot MW_y`

:math:`x(1-c\cdot MW_x) = c\cdot y\cdot MW_y`

:math:`\frac{x}{y} = \frac{c\cdot MW_y}{1-c\cdot MW_x}`

----------------------------------------------------

:math:`c` = concentration in :math:`\frac{mol}{mol}`

:math:`c = \frac{mol}{mol} = \frac{x}{x+y}`

:math:`x = c\cdot x + c\cdot y`

:math:`c\cdot y = x(1-c)`

:math:`\frac{x}{y} = \frac{c}{1-c}`

----------------------------------------------------

:math:`c` = concentration in :math:`\frac{mol}{L}`

:math:`c = \frac{mol}{L}\cdot \frac{1 L}{1000 mL} = \frac{mol}{mL} = \frac{x}{x\cdot MW_x/d_x + y\cdot MW_y/d_y}`

:math:`c\cdot x\cdot MW_x/d_x + c\cdot y\cdot MW_y/d_y = x`

:math:`c\cdot y\cdot MW_y/d_y = x(1 - c\cdot MW_x/d_x)`

:math:`\frac{x}{y} = \frac{x\cdot MW_y/d_y}{1 - c\cdot MW_x/d_x}`

----------------------------------------------------

To calculate required amount of solute, we need to convert the ratio to the same units as the solvent.

For quantities of grams, we convert :math:`\frac{x}{y}` to :math:`\frac{g}{g}`

:math:`\frac{x}{y}\cdot \frac{MW_x}{MW_y}`

For quantities of liters, we convert :math:`\frac{x}{y}` to :math:`\frac{mL}{mL}`. Since it is a ratio, it doesn't matter if we use mL or L.

:math:`\frac{x}{y}\cdot \frac{MW_x/d_x}{MW_y/d_y}`

For quantities of moles, we do nothing since the ratio is already in :math:`\frac{mol}{mol}`

----------------------------------------------------


:math:`ratio = quantity_{solute}/quantity_{solvent}`

:math:`quantity_{solute} = ratio\cdot quantity_{solvent}`

:math:`quantity = quantity_{solute} + quantity_{solvent} = ratio\cdot quantity_{solvent} + quantity_{solvent}`

:math:`= quantity_{solvent}(1 + ratio)`

:math:`quantity_{solvent} = \frac{quantity}{1+ratio}`

:math:`quantity_{solute} = quantity - quantity_{solvent}`

