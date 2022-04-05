# -*- coding: utf-8 -*-
"""
Created on Wed Feb 23 09:13:53 2022

@author: Zikang He
"""

# In[Modules import]

import sys, os
sys.path.extend([os.path.abspath('../')])
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from matplotlib import rc
rc('font',**{'family':'serif','sans-serif':['Times'],'size':12})

np.random.seed(210217)

from qgs.params.params import QgParams
from qgs.integrators.integrator import RungeKuttaIntegrator
from qgs.functions.tendencies import create_tendencies

from qgs.diagnostics.streamfunctions import MiddleAtmosphericStreamfunctionDiagnostic, OceanicLayerStreamfunctionDiagnostic
from qgs.diagnostics.temperatures import MiddleAtmosphericTemperatureDiagnostic, OceanicLayerTemperatureDiagnostic
from qgs.diagnostics.variables import VariablesDiagnostic, GeopotentialHeightDifferenceDiagnostic
from qgs.diagnostics.multi import MultiDiagnostic


# In[Systems definition]
# Time parameters
dt = 0.1
# Saving the model state n steps
write_steps = 100

number_of_trajectories = 1

# Model parameters instantiation with some non-default specs
model_parameters = QgParams()

# Mode truncation at the wavenumber 2 in both x and y spatial
# coordinates for the atmosphere
model_parameters.set_atmospheric_channel_fourier_modes(2, 2)
# Mode truncation at the wavenumber 2 in the x and at the 
# wavenumber 4 in the y spatial coordinates for the ocean
model_parameters.set_oceanic_basin_fourier_modes(2, 4)

# Setting MAOOAM parameters according to the publication linked above
model_parameters.set_params({'kd': 0.0290, 'kdp': 0.0290, 'n': 1.5, 'r': 1.e-7,
                             'h': 136.5, 'd': 1.1e-7})
model_parameters.atemperature_params.set_params({'eps': 0.7, 'T0': 289.3,
                                                 'hlambda': 15.06})
model_parameters.gotemperature_params.set_params({'gamma': 5.6e8, 'T0': 301.46})

model_parameters.atemperature_params.set_insolation(103.3333, 0)
model_parameters.gotemperature_params.set_insolation(310, 0)

#Printing the model's parameters
model_parameters.print_params()
# Creating the tendencies function
f, Df = create_tendencies(model_parameters)


# In[Time integration]
integrator = RungeKuttaIntegrator()
integrator.set_func(f)
## Might take several minutes, depending on your cpu computational power.
ic = np.random.rand(model_parameters.ndim)*0.01
integrator.integrate(0., 3000000., dt, ic=ic, write_steps=0)
time, ic = integrator.get_trajectories()

integrator.integrate(0., 500000., dt, ic=ic, write_steps=write_steps)
reference_time, reference_traj = integrator.get_trajectories()

# In[plot]
varx = 21
vary = 29
varz = 0

fig = plt.figure(figsize=(10, 8))
axi = fig.add_subplot(111, projection='3d')

axi.scatter(reference_traj[varx], reference_traj[vary], reference_traj[varz], s=0.2);

axi.set_xlabel('$'+model_parameters.latex_var_string[varx]+'$', labelpad=12.)
axi.set_ylabel('$'+model_parameters.latex_var_string[vary]+'$', labelpad=12.)
axi.set_zlabel('$'+model_parameters.latex_var_string[varz]+'$', labelpad=12.);

varx = 21
vary = 29
plt.figure(figsize=(10, 8))

plt.plot(reference_traj[varx], reference_traj[vary], marker='o', ms=0.1, ls='')

plt.xlabel('$'+model_parameters.latex_var_string[varx]+'$')
plt.ylabel('$'+model_parameters.latex_var_string[vary]+'$')

var = 10
plt.figure(figsize=(10, 8))

plt.plot(model_parameters.dimensional_time*reference_time, reference_traj[var])

plt.xlabel('time (days)')
plt.ylabel('$'+model_parameters.latex_var_string[var]+'$')

# In[Showing the resulting fields (animation)]
#For the 500hPa geopotential height:
psi_a = MiddleAtmosphericStreamfunctionDiagnostic(model_parameters, geopotential=True)
#For the ocean streamfunction:
psi_o = OceanicLayerStreamfunctionDiagnostic(model_parameters)


theta_a = MiddleAtmosphericTemperatureDiagnostic(model_parameters)
#For the ocean temperature:
theta_o = OceanicLayerTemperatureDiagnostic(model_parameters)
#For the nondimensional variables  𝜓a,1 ,  𝜓o,2  and  𝜃o,2 
variable_nondim = VariablesDiagnostic([21, 29, 0], model_parameters, False)
# For the geopotential height difference between North and South:
geopot_dim = GeopotentialHeightDifferenceDiagnostic([[[np.pi/model_parameters.scale_params.n, np.pi/4], [np.pi/model_parameters.scale_params.n, 3*np.pi/4]]],
                                                    model_parameters, True)
# setting also the background
background = VariablesDiagnostic([21, 29, 0], model_parameters, False)
background.set_data(reference_time, reference_traj)
stride = 10
time = reference_time[10000:10000+5200*stride:stride]
traj = reference_traj[:, 10000:10000+5200*stride:stride]

m = MultiDiagnostic(2,3)
m.add_diagnostic(geopot_dim, diagnostic_kwargs={'style':'moving-timeserie'})
m.add_diagnostic(theta_a, diagnostic_kwargs={'show_time':False})
m.add_diagnostic(theta_o, diagnostic_kwargs={'show_time':False})
m.add_diagnostic(variable_nondim, diagnostic_kwargs={'show_time':False, 'background': background, 'style':'3Dscatter'}, plot_kwargs={'ms': 0.2})
m.add_diagnostic(psi_a, diagnostic_kwargs={'show_time':False})
m.add_diagnostic(psi_o, diagnostic_kwargs={'show_time':False})

m.set_data(time, traj)

rc('font',**{'family':'serif','sans-serif':['Times'],'size':12})
m.animate(figsize=(23,12))

