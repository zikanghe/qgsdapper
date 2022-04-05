import numpy as np

import dapper.mods as modelling
import sys
import time
import sys,os
from multiprocessing import freeze_support, get_start_method
#sys.path.extend([os.path.abspath('../Qgs/qgs')])
# Importing the model's modules

# Start on a random initial condition

from dapper.mods.Qgs.qgs.params.params import QgParams
from dapper.mods.Qgs.qgs.functions.tendencies import create_tendencies
from dapper.mods.Qgs.qgs.integrators.integrator import RungeKuttaIntegrator
from dapper.mods.Qgs.qgs.integrators.integrate import integrate_runge_kutta


if __name__ == "__main__":

    if get_start_method() == "spawn":
        freeze_support()
        
    a_nx = 2 
    a_ny = 2 
    o_nx = 2 
    o_ny = 4 
    Na = a_ny*(2*a_nx+1) 
    No = o_ny*o_nx


    Nx = 2*Na+2*No
    T1 =time.perf_counter()
        ################
        # General parameters
        
        # Saving the model state n steps
    write_steps = 100
        # transient time to attractor
    transient_time = 3.e6
        #transient_time = 300
        # integration time on the attractor
    integration_time = 5.e5
    #integration_time = 500
    # Setting some model parameters
    # Model parameters instantiation with default specs
    model_parameters = QgParams()
    # Mode truncation at the wavenumber 2 in both x and y spatial coordinate
    model_parameters.set_atmospheric_channel_fourier_modes(a_nx, a_ny)
    # Mode truncation at the wavenumber 2 in the x and at the
    # wavenumber 4 in the y spatial coordinates for the ocean
    model_parameters.set_oceanic_basin_fourier_modes(o_nx, o_ny)

# Setting MAOOAM parameters according to the publication linked above
    model_parameters.set_params({'kd': 0.0290, 'kdp': 0.0290, 'n': 1.5, 'r': 1.e-7,
                                 'h': 136.5, 'd': 1.1e-7})
    model_parameters.atemperature_params.set_params({'eps': 0.7, 'T0': 289.3, 'hlambda': 15.06, })
    model_parameters.gotemperature_params.set_params({'gamma': 5.6e8, 'T0': 301.46})

    model_parameters.atemperature_params.set_insolation(103.3333, 0)
    model_parameters.gotemperature_params.set_insolation(310., 0)

    model_parameters.print_params()

    f, Df = create_tendencies(model_parameters)   
    # ## Time integration
    # Defining an integrator
   # integrator = RungeKuttaIntegrator()
    #integrator.set_func(f)

# =============================================================================
# from dapper.mods.integrationHe import with_rk4
# step = with_rk4(f, autonom=False)
# 
# =============================================================================
    integrator = RungeKuttaIntegrator()
    integrator.set_func(f)
    
    
    def step(x0, t0, dt):
       y = x0
       integrator.integrate(t0, t0+dt, 0.1, ic=y, write_steps=0)
       t0, y0 = integrator.get_trajectories()
       #y = np.round(y,7)
       #t,y = integrate_runge_kutta(f, t0, t0+dt, 0.1, ic=y, forward=True,write_steps=0, b=None, c=None, a=None)
       return y0
###
#parameter setting

    #1:Dyn
    Dyn = {
        'M': Nx,
        'model': step,
        'linear': Df,
        'noise': 0.0,
    }



    #2:Time(need to modify)    
    to_time = transient_time + integration_time
    dt = 100*0.1
    t = modelling.Chronology(dt=dt, dto=100*dt, T=to_time,  BurnIn=transient_time)
    #t = modelling.Chronology(dt=dt, dto=100, T=to_time,  BurnIn=transient_time)
    
    np.random.seed(21217) 
    ic = np.random.rand(50,model_parameters.ndim)*0.01
    x0=ic
    X0 = modelling.GaussRV(C=0.0, M=Dyn['M'])

    jj = np.arange(Nx)  # obs_inds
    Obs = modelling.partial_Id_Obs(Nx, jj)
    Obs['noise'] = 0.0000002  # modelling.GaussRV(C=CovMat(2*eye(Nx)))

# =============================================================================
# Obs = {
#     'M': Nx,
#     'model': step,
#      'linear': Df,
#     'noise': 0.0002,
# }
# 
# =============================================================================
    HMM = modelling.HiddenMarkovModel(Dyn, Obs, t, X0)

    xx, yy = HMM.simulate()
    T2 =time.perf_counter()
    print(str(T2-T1)+' seconds')
    #np.savetxt('xxQ2.dat', xx)
    #np.savetxt('yyQ.dat', yy)
####################
# Suggested tuning
####################
# from dapper.mods.Lorenz63.sakov2012 import HMM           # rmse.a:
# N = 50  # Size of the ensemble
#config = EnKF_N(N=N)  # DA config

# =============================================================================
#    import dapper as dpr
#    import dapper.da_methods as da
# 
# 
# 
# 
#    xp = da.EnKF_N(N=20)
# 
# 
#    xp.assimilate(HMM, xx, yy)
# 
# 
# 
# print(xp.avrgs.tabulate(['rmse.a', 'rmv.a']))
# =============================================================================


