# -*- coding: utf-8 -*-
"""
Created on Tue Feb 22 21:19:49 2022

@author: Zikang He
"""

# In [Modules import]
# First, setting the path and loading of some modules
import sys, os
sys.path.extend([os.path.abspath('../')])
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import rc
rc('font',**{'family':'serif','sans-serif':['Times'],'size':14})

#Initializing the random number generator (for reproducibility). -- Disable if needed.
np.random.seed(210217)

#Importing the model's modules

from qgs.params.params import QgParams
from qgs.integrators.integrator import RungeKuttaIntegrator, RungeKuttaTglsIntegrator
from qgs.functions.tendencies import create_tendencies
from qgs.plotting.util import std_plot

#and diagnostics

from qgs.diagnostics.streamfunctions import MiddleAtmosphericStreamfunctionDiagnostic
from qgs.diagnostics.variables import VariablesDiagnostic
from qgs.diagnostics.multi import MultiDiagnostic

# In[Systems definition]

# General parameters

# Time parameters
dt = 0.1
# Saving the model state n steps
write_steps = 5

number_of_trajectories = 1
number_of_perturbed_trajectories = 10

####Setting some model parameters

# Model parameters instantiation with some non-default specs
model_parameters = QgParams({'phi0_npi': np.deg2rad(50.)/np.pi, 'hd':0.3})
# Mode truncation at the wavenumber 2 in both x and y spatial coordinate
model_parameters.set_atmospheric_channel_fourier_modes(2, 2)

# Changing (increasing) the orography depth and the meridional temperature gradient
model_parameters.ground_params.set_orography(0.4, 1)
model_parameters.atemperature_params.set_thetas(0.2, 0)

# Printing the model's parameters
model_parameters.print_params()

# Creating the tendencies function
f, Df = create_tendencies(model_parameters)

# In[Time integration]

# Defining an integrator

integrator = RungeKuttaIntegrator()
integrator.set_func(f)

#Start on a random initial condition and integrate over a transient time to obtain an initial condition on the attractors

ic = np.random.rand(model_parameters.ndim)*0.1
integrator.integrate(0., 200000., dt, ic=ic, write_steps=0)
time, ic = integrator.get_trajectories()

# Now integrate to obtain a trajectory on the attractor

integrator.integrate(0., 100000., dt, ic=ic, write_steps=write_steps)
reference_time, reference_traj = integrator.get_trajectories()

varx = 0
vary = 1
varz = 2

fig = plt.figure(figsize=(10, 8))
axi = fig.add_subplot(111, projection='3d')

axi.scatter(reference_traj[varx], reference_traj[vary], reference_traj[varz], s=0.2);

axi.set_xlabel('$'+model_parameters.latex_var_string[varx]+'$')
axi.set_ylabel('$'+model_parameters.latex_var_string[vary]+'$')
axi.set_zlabel('$'+model_parameters.latex_var_string[varz]+'$');

varx = 2
vary = 1
plt.figure(figsize=(10, 8))

plt.plot(reference_traj[varx], reference_traj[vary], marker='o', ms=0.07, ls='')

plt.xlabel('$'+model_parameters.latex_var_string[varx]+'$')
plt.ylabel('$'+model_parameters.latex_var_string[vary]+'$');

var = 1
plt.figure(figsize=(10, 8))

plt.plot(model_parameters.dimensional_time*reference_time, reference_traj[var])

plt.xlabel('time (days)')
plt.ylabel('$'+model_parameters.latex_var_string[var]+'$');

# In[Initial condition sensitivity analysis example]

# Instantiating a tangent linear integrator with the model tendencies

tgls_integrator = RungeKuttaTglsIntegrator()
tgls_integrator.set_func(f, Df)

# Integrating with slightly perturbed initial conditions

tangent_ic = 0.0001*np.random.randn(number_of_perturbed_trajectories, model_parameters.ndim)
tgls_integrator.integrate(0., 130., dt=dt, write_steps=write_steps, ic=ic, tg_ic=tangent_ic)

#Obtaining the perturbed trajectories
time, traj, delta = tgls_integrator.get_trajectories()
pert_traj = traj + delta

# Trajectories plot
var = 10
plt.figure(figsize=(10, 8))

plt.plot(model_parameters.dimensional_time*time, traj[var])
plt.plot(model_parameters.dimensional_time*time, pert_traj[:,var].T, ls=':')

ax = plt.gca()

plt.xlabel('time (days)')
plt.ylabel('$'+model_parameters.latex_var_string[var]+'$');

#Mean and standard deviation
var = 1
plt.figure(figsize=(10, 8))

plt.plot(model_parameters.dimensional_time*time, traj[var])

ax = plt.gca()
std_plot(model_parameters.dimensional_time*time, np.mean(pert_traj[:,var], axis=0), np.sqrt(np.var(pert_traj[:, var], axis=0)), ax=ax, alpha=0.5)

plt.xlabel('time (days)')
plt.ylabel('$'+model_parameters.latex_var_string[var]+'$');

# In[Showing the resulting fields (animation)]

#Creating the diagnostics:
    #For the 500hPa geopotential height:
psi = MiddleAtmosphericStreamfunctionDiagnostic(model_parameters, geopotential=True)   
        
# For the nondimensional variables  𝜓2  and  𝜓3 :
variable_nondim = VariablesDiagnostic([2, 1], model_parameters, False)  

# setting also the background
background = VariablesDiagnostic([2, 1], model_parameters, False)
background.set_data(reference_time, reference_traj)

#Creating a multi diagnostic with both:
m = MultiDiagnostic(1,2)
m.add_diagnostic(variable_nondim,
                 diagnostic_kwargs={'show_time': False, 'background': background},
                 plot_kwargs={'ms': 0.2})
m.add_diagnostic(psi,
                 diagnostic_kwargs={'style': 'contour', 'contour_labels': False},
                 plot_kwargs={'colors': 'k'})
m.set_data(time, traj)

#and show an interactive animation:
rc('font',**{'family':'serif','sans-serif':['Times'],'size':12})
m.animate(figsize=(20,6))

#or a movie:
rc('font',**{'family': 'serif','sans-serif': ['Times'],'size': 12})
m.movie(figsize=(20,6), anim_kwargs={'interval': 100, 'frames': len(time)-1})
      