#!/usr/bin/env python
# coding: utf-8

# ## Coupled ocean-atmosphere model version

# This model version is a 2-layer channel QG atmosphere truncated at wavenumber 2 coupled, both by friction
# and heat exchange, to a shallow water ocean with 8 modes.
#
# More detail can be found in the articles:
#
# * Vannitsem, S., Demaeyer, J., De Cruz, L., & Ghil, M. (2015). Low-frequency variability and heat
#   transport in a low-order nonlinear coupled ocean¡§Catmosphere model. Physica D: Nonlinear Phenomena, 309, 71-85.
# * De Cruz, L., Demaeyer, J., and Vannitsem, S.: The Modular Arbitrary-Order Ocean-Atmosphere Model:
#   MAOOAM v1.0, Geosci. Model Dev., 9, 2793¡§C2808, 2016.
#


# ## Modules import
import numpy as np
#import sys
#import time
from multiprocessing import freeze_support, get_start_method
import sys,os
#sys.path.extend([os.path.abspath('../qgs')])
# Importing the model's modules
from dapper.mods.Qgs.qgs.params.params import QgParams
from dapper.mods.Qgs.qgs.integrators.integrator import RungeKuttaIntegrator
from dapper.mods.Qgs.qgs.functions.tendencies import create_tendencies

# Initializing the random number generator (for reproducibility). -- Disable if needed.


class QGS_model:
   if get_start_method() == "spawn":
        freeze_support()


    # ## Systems definition

    # General parameters
   def __init__(self,t = 0.1,w = 100,tr = 3.e6,inte = 5.e5):
   #def _init_(self,t,w ,tr ,inte):
    # Time parameters
    self.dt=t
    # Saving the model state n steps
    self.write_steps = w
    # transient time to attractor
    self.transient_time = tr
    # integration time on the attractor
    self.integration_time = inte
   def algorithm(self,atx=2,aty=2,otx=2,oty=4):
    # file where to write the output
    filename = "evol_fields.dat"

    # Setting some model parameters
    # Model parameters instantiation with default specs
    model_parameters = QgParams()
    # Mode truncation at the wavenumber 2 in both x and y spatial coordinate
    model_parameters.set_atmospheric_channel_fourier_modes(atx,aty)
    # Mode truncation at the wavenumber 2 in the x and at the
    # wavenumber 4 in the y spatial coordinates for the ocean
    model_parameters.set_oceanic_basin_fourier_modes(otx,oty)

    # Setting MAOOAM parameters according to the publication linked above
    model_parameters.set_params({'kd': 0.0290, 'kdp': 0.0290, 'n': 1.5, 'r': 1.e-7,
                                 'h': 136.5, 'd': 1.1e-7})
    model_parameters.atemperature_params.set_params({'eps': 0.7, 'T0': 289.3, 'hlambda': 15.06, })
    model_parameters.gotemperature_params.set_params({'gamma': 5.6e8, 'T0': 301.46})

    model_parameters.atemperature_params.set_insolation(103.3333, 0)
    model_parameters.gotemperature_params.set_insolation(310., 0)


    # Creating the tendencies functions
    f, Df = create_tendencies(model_parameters)

    # ## Time integration
    # Defining an integrator
    integrator = RungeKuttaIntegrator()
    integrator.set_func(f)
    np.random.seed(21217)
    # Start on a random initial condition
    ic = np.random.rand(model_parameters.ndim)*0.01
    # Integrate over a transient time to obtain an initial condition on the attractors
    print('start')  
    ws = 10000
    y = ic
    total_time = 0.
    #t_up = ws * self.dt / self.integration_time * 100
    while total_time < self.transient_time:
        integrator.integrate(0., ws * self.dt, self.dt, ic=y, write_steps=0)
        t, y = integrator.get_trajectories()
        total_time += t
    # Now integrate to obtain a trajectory on the attractor
    total_time = 0.
    traj = np.insert(y, 0, total_time)
    traj = traj[np.newaxis, ...]
    #t_up = self.write_steps * self.dt / self.integration_time * 100

    print('finish spin up')
    while total_time < self.integration_time:
        integrator.integrate(0., self.write_steps * self.dt, self.dt, ic=y, write_steps=0)
        t, y = integrator.get_trajectories()
        total_time += t
        ty = np.insert(y, 0, total_time)
        traj = np.concatenate((traj, ty[np.newaxis, ...]))
    print('finish integration')  

    np.savetxt(filename, traj)
    return traj



 

   
