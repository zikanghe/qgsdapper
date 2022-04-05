# -*- coding: utf-8 -*-
"""
Created on Thu Feb 24 16:40:30 2022

@author: Zikang He
"""

# -*- coding: utf-8 -*-
"""
Created on Thu Feb 24 15:50:36 2022

@author: Zikang He
"""

# In[Modules import]
import sys, os, warnings

sys.path.extend([os.path.abspath('../')])
import numpy as np
#import matplotlib.pyplot as plt
from numba import njit
from matplotlib import rc
rc('font',**{'family':'serif','sans-serif':['Times'],'size':12})

np.random.seed(210217)

from qgs.params.params import QgParams
from qgs.basis.base import SymbolicBasis
from qgs.inner_products.definition import StandardSymbolicInnerProductDefinition
from qgs.inner_products.symbolic import AtmosphericSymbolicInnerProducts, OceanicSymbolicInnerProducts
from qgs.tensors.qgtensor import QgsTensor
from qgs.functions.sparse_mul import sparse_mul3
from qgs.integrators.integrator import RungeKuttaIntegrator
#from multiprocessing import freeze_support, get_start_method


#from qgs.diagnostics.streamfunctions import MiddleAtmosphericStreamfunctionDiagnostic, OceanicLayerStreamfunctionDiagnostic
#from qgs.diagnostics.temperatures import MiddleAtmosphericTemperatureDiagnostic, OceanicLayerTemperatureDiagnostic
#from qgs.diagnostics.variables import VariablesDiagnostic, GeopotentialHeightDifferenceDiagnostic
#from qgs.diagnostics.multi import MultiDiagnostic

from sympy import symbols, sin, exp, pi

# In[Systems definition]


    # Time parameters
dt = 0.1
    # Saving the model state n steps
write_steps = 100

number_of_trajectories = 1

   # Model parameters instantiation with some non-default specs
model_parameters = QgParams({'n': 1.5})

   # Mode truncation at the wavenumber 2 in both x and y spatial
   # coordinates for the atmosphere
model_parameters.set_atmospheric_channel_fourier_modes(2, 2, mode="symbolic") 
ocean_basis = SymbolicBasis()
x, y = symbols('x y')  # x and y coordinates on the model's spatial domain
n, al = symbols('n al', real=True, nonnegative=True)  # aspect ratio and alpha coefficients
for i in range(1, 3):
   for j in range(1, 3):
         ocean_basis.functions.append(2 * exp(- al * x) * sin(j * n * x / 2) * sin(i * y))
         
ocean_basis.substitutions.append((al, 1.))
ocean_basis.substitutions.append((n, model_parameters.scale_params.n))
    
model_parameters.set_oceanic_modes(ocean_basis)
    

    # Setting MAOOAM parameters according to the publication linked above
model_parameters.set_params({'kd': 0.029, 'kdp': 0.029, 'r': 1.0e-7,
                             'h': 136.5, 'd': 1.1e-7})
model_parameters.atemperature_params.set_params({'eps': 0.76, 'T0': 289.3,
                                                 'hlambda': 15.06})
model_parameters.gotemperature_params.set_params({'gamma': 5.6e8, 'T0': 301.46})
    
model_parameters.atemperature_params.set_insolation(103.3333, 0)
model_parameters.gotemperature_params.set_insolation(310, 0)
    
model_parameters.print_params()
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
            return expr, (x, 0, 2 * pi / 
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
# In[3]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    ip = UserInnerProductDefinition( )
    print(ip)
    aip = AtmosphericSymbolicInnerProducts(model_parameters)
    oip = OceanicSymbolicInnerProducts(model_parameters, inner_product_definition=ip)
    #oip = OceanicSymbolicInnerProducts(model_parameters)  
aotensor = QgsTensor(model_parameters, aip, oip)
      
coo = aotensor.tensor.coords.T
val = aotensor.tensor.data

@njit
def f(t, x):
    xx = np.concatenate((np.full((1,), 1.), x))
    xr = sparse_mul3(coo, val, xx, xx)

    return xr[1:]
      
integrator = RungeKuttaIntegrator()
integrator.set_func(f)
      
      ## Might take several minutes, depending on your cpu computational power.
ic = np.random.rand(model_parameters.ndim)*0.0001
integrator.integrate(0., 10000000., dt, ic=ic, write_steps=0)
time, ic = integrator.get_trajectories()
      
integrator.integrate(0., 1000000., dt, ic=ic, write_steps=write_steps)
reference_time, reference_traj = integrator.get_trajectories()



