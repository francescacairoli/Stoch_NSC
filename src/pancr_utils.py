import numpy as np
from scipy.optimize import leastsq
from scipy.integrate import odeint
import copy
import pickle
import matplotlib.pyplot as plt
#from casadi import *

def HJ_params(BW=75):

	p = {}
	p["BW"] = BW
	p["ka_int"] = 0.025
	p["EGP_0"] = 0.0158*BW
	p["F_01"] = 0.0104*BW
	p["V_G"] = 0.1797*BW
	p["k12"] = 0.0793
	p["R_thr"]=9
	p["R_cl"]=0.003
	p["Ag"] = 0.8121
	p["tMaxg"] = 48.8385
	p["Ug_ceil"] = 0.0275*BW
	p["K"] = 0.7958
	p["kia1"] = 0.0113
	p["kia2"] = 0.0197
	p["k_e"] = 0.1735
	p["Vmax_LD"] = 2.9639
	p["km_LD"] = 47.5305
	p["ka_1"] = 0.007
	p["ka_2"] = 0.0331
	p["ka_3"] = 0.0308
	p["SIT"] = 0.0046
	p["SID"] = 0.0006
	p["SIE"] = 0.0384
	p["V_I"] = 0.1443*BW
	p["M_PGU_f"] = 1/35
	p["M_HGP_f"] = 1/155
	p["M_PIU_f"] = 2.4
	p["PGUA_rate"] = 1/30
	p["PGUA_a"] = 0.006
	p["PGUA_b"] = 1.2264
	p["PGUA_c"] = -10.1952
	p["PVO2max_rate"] = 5/3

	return p

def steady_PGUA_from_PVO2max(PVO2max, params):

	PGUA_ss = params["PGUA_a"]*PVO2max**2 + params["PGUA_b"]*PVO2max + params["PGUA_c"]

	return PGUA_ss


def diff_eq(y):
	'''
	% y: state variables -- vector of length 14
	% params: parameters
	% dists: disturbances at t (vector of length 3)
	'''
	#y =  np.array([1.05124500e+02, 3.53833297e+01,8.78988903e+02, 8.78988903e+02,
 #7.42622616e+01, 6.56803525e+01, 2.79168049e-02, 3.64132238e-03,
 #2.33044632e-01, 0.00000000e+00, 0.00000000e+00, 7.80000000e+00,
 #0.00000000e+00, 8.00000000e+00])
	#y[:6] = y_red


	params = HJ_params()

	basal_iir = 16.0146096438259

	u = basal_iir

	dydt = np.zeros(len(y))

	## extract disturbances
	# ingested CHO
	D = 0
	# active muscular mass at current time
	MM = 0
	# max oxygen at current time
	targetPVo2max = 8

	## extract variables

	# glucose kinetics
	# masses of glucose in the accessible and non-accessible compartments respectively, in mmol.
	Q1 = y[0]
	Q2 = y[1]

	# Measured glucose concentration
	G = Q1/params["V_G"]

	# corrected non-insulin mediated glucose uptake [Hovorka04]
	if G >= 4.5:
		F_01c = params["F_01"]
	else:
		F_01c = params["F_01"]*G/4.5

	if G >= 9:
		F_R = 0.003*(G-9)*params["V_G"]
	else:
		F_R = 0


	# insulin kinetics
	# insulin mass through the slow absorption pathway,
	Q1a = y[2]
	Q2i = y[3]
	#faster channel for insulin absorption
	Q1b = y[4]
	#plasma insulin mass
	Q3 = y[5]
	#plasma insulin concentration
	I = Q3/params["V_I"]

	# insulin dynamics
	# x1 (min-1), x2 (min-1) and x3 (unitless) represent 
	# the effect of insulin on glucose distribution, 
	# glucose disposal and suppression of endogenous glucose 
	# production, respectively
	x1 = y[6]
	x2 = y[7]
	x3 = y[8]

	k_b1 = params["ka_1"]*params["SIT"]
	k_b2 = params["ka_2"]*params["SID"]
	k_b3 = params["ka_3"]*params["SIE"]

	# Subsystem of glucose absorption from gut
	# Glucose masses in the accessible and nonaccessible compartments
	G1 = y[9]
	G2 = y[10]

	tmax = np.maximum(params["tMaxg"],G2/params["Ug_ceil"])
	U_g = G2/tmax

	# interstitial glucose
	C = y[11]

	# exercise 
	PGUA = y[12]
	PVO2max = y[13]
	M_PGU = 1 + PGUA*MM*params["M_PGU_f"]
	M_PIU = 1 + MM*params["M_PIU_f"]
	M_HGP = 1 + PGUA*MM*params["M_HGP_f"]
	#PGUA_ss = p.PGUA_a*PVO2max^2 + p.PGUA_b*PVO2max + p.PGUA_c;
	PGUA_ss = steady_PGUA_from_PVO2max(PVO2max, params)

	## compute change rates
	# use flow variables to avoid duplicated computation

	# Glucose kinetics
	Q1_to_Q2_flow = x1*Q1 - params["k12"]*Q2
	Q1dt = -F_01c -Q1_to_Q2_flow - F_R + U_g +  params["EGP_0"]*(1 - x3)
	Q2dt = Q1_to_Q2_flow -x2*Q2
	dydt[0] = Q1dt
	dydt[1] = Q2dt

	## insulin kinetics
	Q1a_to_Q2i_flow = params["kia1"]*Q1a
	Q2i_to_Q3_flow = params["kia1"]*Q2i
	Q1b_to_Q3_flow = params["kia2"]*Q1b
	###---
	insulin_ratio = params["K"]*u 

	Q1adt = insulin_ratio - Q1a_to_Q2i_flow - params["Vmax_LD"]*Q1a/(params["km_LD"]+Q1a)
	Q2idt = Q1a_to_Q2i_flow - Q2i_to_Q3_flow
	####----
	Q1bdt = u - insulin_ratio - Q1b_to_Q3_flow - params["Vmax_LD"]*Q1b/(params["km_LD"]+Q1b)
	Q3dt = Q2i_to_Q3_flow + Q1b_to_Q3_flow - params["k_e"]*Q3

	dydt[2] = Q1adt
	dydt[3] = Q2idt
	dydt[4] = Q1bdt
	dydt[5] = Q3dt

	## insulin dynamics
	x1dt = -params["ka_1"]*x1 + M_PGU*M_PIU*k_b1*I
	x2dt = -params["ka_2"]*x2 + M_PGU*M_PIU*k_b2*I
	x3dt = -params["ka_3"]*x3 + M_HGP*k_b3*I
	dydt[6] = x1dt
	dydt[7] = x2dt
	dydt[8] = x3dt


	## Glucose absorption from gut
	G1_to_G2_flow = G1/tmax
	G1dt =  - G1_to_G2_flow + params["Ag"]*D
	G2dt =  G1_to_G2_flow - G2/tmax
	dydt[9] = G1dt
	dydt[10] = G2dt


	## interstitial glucose
	Cdt = params["ka_int"]*(G-C)
	dydt[11] = Cdt


	## exercise
	PGUAdt = -params["PGUA_rate"]*PGUA +params["PGUA_rate"]*PGUA_ss
	dydt[12] = PGUAdt

	PVO2maxdt = -params["PVO2max_rate"]*PVO2max +params["PVO2max_rate"]*targetPVo2max
	dydt[13] = PVO2maxdt

	return dydt#[:6]



