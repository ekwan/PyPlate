### Formulas used to calculate concentrations in `Unit.calculate_concentration_ratio`
#### Ratio of moles to moles is calculated based on the numerator and denominator of desired concentration.
x = solute in moles, y = solvent in moles

$MW_x$ = molecular weight of solute, $d_x$ = density of solute

$MW_y$ = molecular weight of solvent, $d_y$ = density of solvent

---
c = $\frac{g}{g}$ = $\frac{x\cdot MW_x}{x\cdot MW_x + y\cdot MW_y}$

$c\cdot x\cdot MW_x + c\cdot y\cdot MW_y = x\cdot MW_x$

$c\cdot y\cdot MW_y = x\cdot MW_x (1-c)$

$\frac{x}{y} = \frac{c\cdot MW_y}{(1-c)MW_x}$
---
c = $\frac{g}{mol}$ = $\frac{x\cdot MW_x}{x+y}$

$c\cdot x + c\cdot y = x\cdot MW_x$

$c\cdot y = x(MW_x-c)$

$\frac{x}{y} = \frac{x}{MW_x -c}$
---
c = $\frac{g}{L}\cdot \frac{1 L}{1000 mL} = \frac{g}{mL}$

c = $\frac{x\cdot MW_x}{x\cdot MW_x/d_x + y\cdot MW_y/d_y}$

$c\cdot x\cdot MW_x/d_y + c\cdot y\cdot MW_y/d_y = x\cdot MW_x$

$c\cdot y\cdot MW_y/d_y = x\cdot MW_x(1-c/d_y)$

$\frac{x}{y} = \frac{c\cdot MW_y}{MW_x\cdot d_y(1-c/d_x)}$
---

c = $\frac{L}{g}\cdot \frac{1000 mL}{1 L} = \frac{mL}{g}$

c = $\frac{x\cdot MW_x/d_x}{x\cdot MW_x + y\cdot MW_y}$

$c\cdot x\cdot MW_x + c\cdot y\cdot MW_y = x\cdot MW_x/d_x$

$c\cdot y\cdot MW_y = x\cdot MW_x(1/d_x-c)$

$\frac{x}{y} = \frac{c\cdot MW_y}{MW_x(1/d_x-c)}$

---

c = $\frac{L}{mol}\cdot \frac{1000 mL}{1 L} = \frac{mL}{mol}$

c = $\frac{x\cdot MW_x/d_x}{x + y}$

$c\cdot x + c\cdot y = x\cdot MW_x/d_x$

$c\cdot y = x(MW_x/d_x - c)$

$\frac{x}{y} = \frac{c}{MW_x/d_x-c}$

---

c = $\frac{L}{L} = \frac{x\cdot MW_x/d_x}{x\cdot MW_x/d_x + y\cdot MW_y/d_y}$

$c\cdot x\cdot MW_x/d_x + c\cdot y\cdot MW_y/d_y = x\cdot MW_x/d_x$

$c\cdot y\cdot MW_y/d_y = (1-c)x\cdot MW_x/d_x$

$\frac{x}{y} = \frac{c\cdot MW_y/d_y}{(1-c)MW_x/d_x}$

---

c = $\frac{mol}{g} = \frac{x}{x\cdot MW_x + y\cdot MW_y}$

$x = c\cdot x\cdot MW_x + c\cdot y\cdot MW_y$

$x(1-c\cdot MW_x) = c\cdot y\cdot MW_y$

$\frac{x}{y} = \frac{c\cdot MW_y}{1-c\cdot MW_x}$

---

c = $\frac{mol}{mol} = \frac{x}{x+y}$

$x = c\cdot x + c\cdot y$

$c\cdot y = x(1-c)$

$\frac{x}{y} = \frac{c}{1-c}$

---

c = $\frac{mol}{L}\cdot \frac{1 L}{1000 mL} = \frac{mol}{mL} = \frac{x}{x\cdot MW_x/d_x + y\cdot MW_y/d_y}$

$c\cdot x\cdot MW_x/d_x + c\cdot y\cdot MW_y/d_y = x$

$c\cdot y\cdot MW_y/d_y = x(1 - c\cdot MW_x/d_x)$

$\frac{x}{y} = \frac{x\cdot MW_y/d_y}{1 - c\cdot MW_x/d_x}$

---
---
### Formulas used in `Container.create_solution` to calculate quantity of solvent and solute if given total quantity and concentration.
#### For quantities of grams, we convert $\frac{x}{y}$ to $\frac{g}{g}$

$\frac{x}{y}\cdot \frac{MW_x}{MW_y}$

#### For quantities of liters, we convert $\frac{x}{y}$ to $\frac{mL}{mL}$. Since it is a ratio, it doesn't matter if we use mL or L.

$\frac{x}{y}\cdot \frac{MW_x/d_x}{MW_y/d_y}$

#### For quantities of moles, we do nothing since the ratio is already in $\frac{mol}{mol}$

---
#### quantity is total_quantity
$ratio = quantity_{solute}/quantity_{solvent}$

$quantity_{solute} = ratio\cdot quantity_{solvent}$

$quantity = quantity_{solute} + quantity_{solvent} = ratio\cdot quantity_{solvent} + quantity_{solvent}$

$= quantity_{solvent}(1 + ratio)$

$quantity_{solvent} = \frac{quantity}{1+ratio}$

$quantity_{solute} = quantity - quantity_{solvent}$

