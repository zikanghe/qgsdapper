# -*- coding: utf-8 -*-
"""
Created on Wed Feb 23 08:30:59 2022

@author: Zikang He
"""

# In[Modules import]
import sys, os
sys.path.extend([os.path.abspath('../')])
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

np.random.seed(210217)

from qgs.params.params import QgParams
from qgs.basis.fourier import contiguous_channel_basis
from qgs.integrators.integrator import RungeKuttaIntegrator
from qgs.functions.tendencies import create_tendencies

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
# Mode truncation at the wavenumber 2 in the x and at the 
# wavenumber 4 in the y spatial coordinates for the ocean
ocean_basis = contiguous_channel_basis(2, 2, 1.5)
model_parameters.set_oceanic_modes(ocean_basis)

# Setting MAOOAM parameters according to the publication linked above
model_parameters.set_params({'phi0_npi': 0.3056, 'kd': 0.026778245344758034, 'kdp': 0.026778245344758034, 'r': 1.e-8,
                             'h': 1000.0, 'd': 1.6e-8, 'f0': 1.195e-4, 'sigma': 0.14916, 'n':1.7})
model_parameters.atemperature_params.set_params({'eps': 0.76, 'T0': 270.,
                                                 'hlambda': 16.064})
model_parameters.gotemperature_params.set_params({'gamma': 4e9, 'T0': 285.})

model_parameters.atemperature_params.set_insolation(350/3., 0)
model_parameters.gotemperature_params.set_insolation(350, 0)

# Printing the model's parameters
model_parameters.print_params()

#Creating the tendencies function
## Might take several minutes, depending on the number of cpus you have.
f, Df = create_tendencies(model_parameters)

# In[Time integration]
integrator = RungeKuttaIntegrator()
integrator.set_func(f)

ic = np.array([ 2.34980646e-02, -5.91652353e-03,  3.20923307e-03, -1.08916714e-03,
       -1.13188144e-03, -5.14454554e-03,  1.50294902e-02, -2.20518843e-04,
        4.55325496e-03, -1.18748859e-03,  2.27043688e-02,  4.29437410e-04,
        3.74041445e-03, -1.78681895e-03, -1.71853500e-03,  3.68921542e-04,
       -6.42748591e-04, -2.81188015e-03, -2.14109639e-03, -1.41736652e-03,
        3.24489725e-09,  3.97502699e-05, -7.47489713e-05,  9.89194512e-06,
        5.52902699e-06,  6.43875197e-05, -6.95990073e-05,  1.21618381e-04,
        7.08494425e-05, -1.11255308e-04,  4.13406579e-02, -7.90716982e-03,
        1.33752621e-02,  1.66742520e-02,  6.29900201e-03,  1.76761107e-02,
       -5.40207169e-02,  1.29814807e-02, -4.35142923e-02, -7.62511906e-03])

integrator.integrate(0., 1000000., dt, ic=ic, write_steps=write_steps)
time, traj = integrator.get_trajectories()

# In[Plotting the result in 3D and 2D]
varx = 20
vary = 30
varz = 0

fig = plt.figure(figsize=(10, 8))
axi = fig.gca(projection='3d')

axi.scatter(traj[varx], traj[vary], traj[varz], s=0.2);

axi.set_xlabel('$'+model_parameters.latex_var_string[varx]+'$')
axi.set_ylabel('$'+model_parameters.latex_var_string[vary]+'$')
axi.set_zlabel('$'+model_parameters.latex_var_string[varz]+'$')

varx = 30
vary = 10
plt.figure(figsize=(10, 8))

plt.plot(traj[varx], traj[vary], marker='o', ms=0.1, ls='')

plt.xlabel('$'+model_parameters.latex_var_string[varx]+'$')
plt.ylabel('$'+model_parameters.latex_var_string[vary]+'$')

var = 30
plt.figure(figsize=(10, 8))

plt.plot(model_parameters.dimensional_time*time, traj[var])

plt.xlabel('time (days)')
plt.ylabel('$'+model_parameters.latex_var_string[var]+'$')

var = 10
plt.figure(figsize=(10, 8))

plt.plot(model_parameters.dimensional_time*time, traj[var])

plt.xlabel('time (days)')
plt.ylabel('$'+model_parameters.latex_var_string[var]+'$')

var = 20
plt.figure(figsize=(10, 8))

plt.plot(model_parameters.dimensional_time*time, traj[var])

plt.xlabel('time (days)')
plt.ylabel('$'+model_parameters.latex_var_string[var]+'$')




