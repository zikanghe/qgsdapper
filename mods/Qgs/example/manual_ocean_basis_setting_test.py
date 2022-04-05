# -*- coding: utf-8 -*-
"""
Created on Thu Feb 24 08:20:25 2022

@author: Zikang He
"""

import sys, os

sys.path.extend([os.path.abspath('../')])

from qgs.params.params import QgParams
model_parameters = QgParams({'n': 1.5})
model_parameters.set_atmospheric_channel_fourier_modes(2, 2, mode="symbolic")
import numpy as np

from qgs.basis.base import SymbolicBasis
ocean_basis = SymbolicBasis()

from sympy import symbols, sin, exp
x, y = symbols('x y')  # x and y coordinates on the model's spatial domain
n, al = symbols('n al', real=True, nonnegative=True)  # aspect ratio and alpha coefficients
for i in range(1, 3):
    for j in range(1, 3):
        ocean_basis.functions.append(2 * exp(- al * x) * sin(j * n * x / 2) * sin(i * y))
        
ocean_basis.substitutions.append(('al', 1.))

model_parameters.set_oceanic_modes(ocean_basis)



from sympy import pi
from qgs.inner_products.definition import StandardSymbolicInnerProductDefinition
class UserInnerProductDefinition(StandardSymbolicInnerProductDefinition):

    def symbolic_inner_product(self, S, G, symbolic_expr=False, integrand=False):
        """Function defining the inner product to be computed symbolically:
        :math:`(S, G) = \\frac{n}{2\\pi^2}\\int_0^\\pi\\int_0^{2\\pi/n}  e^{2 \\alpha x} \\,  S(x,y)\\, G(x,y)\\, \\mathrm{d} x \\, \\mathrm{d} y`.

        Parameters
        ----------
        S: Sympy expression
            Left-hand side function of the product.
        G: Sympy expression
            Right-hand side function of the product.
        symbolic_expr: bool, optional
            If `True`, return the integral as a symbolic expression object. Else, return the integral performed symbolically.
        integrand: bool, optional
            If `True`, return the integrand of the integral and its integration limits as a list of symbolic expression object. Else, return the integral performed symbolically.

        Returns
        -------
        Sympy expression
            The result of the symbolic integration
        """
        expr = (n / (2 * pi ** 2)) * exp(2 * al * x) * S * G
        if integrand:
            return expr, (x, 0, 2 * pi / n), (y, 0, pi)
        else:
            return self.integrate_over_domain(self.optimizer(expr), symbolic_expr=symbolic_expr)
        
        
        
ip = UserInnerProductDefinition()

from qgs.inner_products.symbolic import AtmosphericSymbolicInnerProducts, OceanicSymbolicInnerProducts

aip = AtmosphericSymbolicInnerProducts(model_parameters)
oip = OceanicSymbolicInnerProducts(model_parameters, inner_product_definition=ip)

from qgs.tensors.qgtensor import QgsTensor

aotensor = QgsTensor(model_parameters, aip, oip)

from numba import njit
from qgs.functions.sparse_mul import sparse_mul3
coo = aotensor.tensor.coords.T
val = aotensor.tensor.data

@njit
def f(t, x):
    xx = np.concatenate((np.full((1,), 1.), x))
    xr = sparse_mul3(coo, val, xx, xx)

    return xr[1:]
