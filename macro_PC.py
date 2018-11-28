# -*- coding: utf-8 -*-
"""
uGrid "Macro" Code

@author: Phy
"""

from __future__ import division
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from technical_tools_PC import Tech_total
from economic_tools_PC import Econ_total
import time

start_time = time.time()

#PSO Parameters
PSO_Parameters = pd.read_excel('uGrid_Input.xlsx', sheet_name = 'PSO')
maxGen = PSO_Parameters['maxGen'][0]
numInd = PSO_Parameters['numInd'][0]
X_tariff_multiplier = PSO_Parameters['X_tariff_multiplier'][0]
stopLimit = PSO_Parameters['stopLimit'][0]
convergenceRequirement = PSO_Parameters['convergenceRequirement'][0]
lowTestLim = PSO_Parameters['lowTestLim'][0]
highTestLim = PSO_Parameters['highTestLim'][0]
roundDownSize = PSO_Parameters['roundDownSize'][0]
C1 = PSO_Parameters['C1'][0]
C2 = PSO_Parameters['C2'][0]
CF = PSO_Parameters['CF'][0]
W = PSO_Parameters['W'][0]
VF = PSO_Parameters['VF'][0]
momentum = PSO_Parameters['momentum'][0]

#Parameter limits: Battery, PV
#These will be changed so the solutions are more flexible for sites (not input)
#Could make these scaled off of load input
lower_bounds = [1,1]
upper_bounds = [10,5]


#Initialize matrixes and parameters
Parameters_test = np.zeros(2)
Parameters_dev = np.zeros(2)

Parameters = np.zeros((2,numInd,maxGen)) #this is the result for each parameter, for each month, for each individual
Propane_ec = np.zeros((numInd,maxGen))
Batt_kWh_tot_ec = np.zeros((numInd,maxGen))

#Create random initial guesses for Parameters
for i in range(2):
    for k in range(numInd):
        rn = np.random.uniform(lower_bounds[i],upper_bounds[i])
        if rn < roundDownSize: #Constraint for minimum sizes
            rn = 0
        Parameters[i,k,0] = np.copy(rn)
    
#Initialize Economic Parameters    
tariff = np.zeros((numInd,maxGen))
Batt_life_yrs = np.zeros((numInd,maxGen))

#Initialize Global Bests
#global best: best known postions ever, personal best: best known position for each particle(out of all generations), gbest_change: best in generation (out of all individuals)
#Global Best
gB_propane = 999
gB_tariff = 999
gB_tariff_plus = gB_tariff*(1+X_tariff_multiplier)
gB_parameters = np.zeros(2)
LoadKW_MAK = pd.read_excel('LoadKW_MAK.xlsx',index_col=None, header=None)
hmax = len(LoadKW_MAK)
gB_Cost = np.zeros(hmax)
data_plot_variables = np.zeros((hmax,13))
gB_plot_variables = pd.DataFrame(data = data_plot_variables ,columns=['Batt_SOC', 'Charge', 'LoadkW', 'genLoad', 'Batt_Power_to_Load', 'Batt_Power_to_Load_neg', 'PV_Power', 'PV_Batt_Change_Power', 'dumpload', 'Batt_frac', 'Gen_Batt_Charge_Power', 'Genset_fuel', 'Fuel_kW'])
data_optimization_variables = np.zeros((maxGen-1, 4))
gB_optimization_output_var = np.zeros((4,maxGen-1))
gB_optimization_output =pd.DataFrame(data = data_optimization_variables, columns =['BattkW','PVkW','Propane','Tariff'])            

#gB_change (best individual in generation)
gB_change_propane = np.ones(maxGen)*999
gB_change_tariff = np.ones(maxGen)*999
gB_change_tariff_plus = gB_change_tariff*(1+X_tariff_multiplier)
gB_change_parameters = np.zeros((2,maxGen))

#Personal Best (best position for each particle)
pB_propane = np.ones(numInd)*999
pB_tariff = np.ones(numInd)*999
pB_parameters = np.ones((2,numInd))*999
pB_tariff_plus = np.ones(numInd)*999

#Initialize Velocities
#batt, PV, CSP, ORC, TES
VelMax = np.zeros(2)
VelMin = np.zeros(2)
VelMax = VF*(np.array(upper_bounds)-np.array(lower_bounds))
VelMin = -1*VelMax
V_gens = np.zeros((2,numInd,maxGen))


# Start Optimization Iterations
iteration = 0
t_diff = 999
match = 0
while iteration < maxGen-1 and t_diff > stopLimit and match < convergenceRequirement:
    match = 0
    for m in range(numInd):            
        #calculate technical parameters
        Propane_ec[m,iteration], DNI, Batt_kWh_tot_ec[m,iteration], Batt_SOC, Charge, State, LoadkW, genLoad, Inv_Batt_Dis_P, PV_Power, PV_Batt_Change_Power, dumpload, Batt_frac, Gen_Batt_Charge_Power, Genset_fuel, Fuel_kW, peakload, loadkWh = Tech_total(Parameters[0,m,iteration],Parameters[1,m,iteration])
        #don't need to save DNI, final, Batt_SOC, and Charge these are used to validate program
               
        LoanPrincipal, year, Cost, Revenue, CashonHand, Balance, M, O, tariff[m,iteration], Batt_life_yrs[m,iteration] = Econ_total(Propane_ec[m,iteration],Parameters[1,m,iteration]*peakload,Parameters[0,m,iteration]*peakload,Batt_kWh_tot_ec[m,iteration],peakload,loadkWh)
        #order of parameters: batt, PV, CSP, ORC, TES_ratio
        
   
        #Checking Outputs
        print "This individual's yearly propane and tariff is: " +str(Propane_ec[m,iteration]) + ", " +str(tariff[m,iteration])

        #Find generation best
        if tariff[m,iteration] < gB_change_tariff_plus[iteration] or (tariff[m,iteration] < gB_change_tariff[iteration] and Propane_ec[m,0] < gB_change_propane[iteration]):
            gB_change_tariff[iteration] = np.copy(tariff[m,iteration])
            gB_change_tariff_plus[iteration] = gB_change_tariff[iteration]*(1+X_tariff_multiplier)
            gB_change_propane[iteration] = np.copy(Propane_ec[m,iteration])
            gB_change_parameters[:,iteration] = np.copy(Parameters[:,m,iteration])
        #Find global best (removed gB_tariff_plus buffer for true global best: tariff[m,iteration] < gB_tariff_plus or)
        if tariff[m,iteration] < gB_tariff and Propane_ec[m,0] < gB_propane:
            gB_tariff = np.copy(tariff[m,iteration])
            gB_tariff_plus = gB_tariff*(1+X_tariff_multiplier)
            gB_propane = np.copy(Propane_ec[m,iteration])
            gB_parameters = np.copy(Parameters[:,m,iteration])
            #Saving plotting variables
            data_plot_variables = np.transpose([Batt_SOC, Charge, LoadkW, genLoad, -Inv_Batt_Dis_P, Inv_Batt_Dis_P, PV_Power, PV_Batt_Change_Power, dumpload, Batt_frac, Gen_Batt_Charge_Power, Genset_fuel, Fuel_kW])
            gB_plot_variables = pd.DataFrame(data = data_plot_variables,columns=['Batt_SOC', 'Charge', 'LoadkW', 'genLoad', 'Batt_Power_to_Load', 'Batt_Power_to_Load_neg', 'PV_Power', 'PV_Batt_Change_Power', 'dumpload', 'Batt_frac', 'Gen_Batt_Charge_Power', 'Genset_fuel', 'Fuel_kW'])
            gB_Cost = np.copy(Cost)
        #Find personal best (done at the end of each iteration)
        for pB_iter in range(iteration):
            if tariff[m,iteration] < pB_tariff_plus[m] or (tariff[m,iteration] < pB_tariff[m] and Propane_ec[m,iteration] < pB_propane[m]):
                pB_tariff[m] = np.copy(tariff[m,iteration])
                pB_tariff_plus[m] = pB_tariff[m]*(1+X_tariff_multiplier)
                pB_propane[m] = np.copy(Propane_ec[m,iteration])
                pB_parameters[:,m] = np.copy(Parameters[:,m,iteration])

        #Calculate Next Gen
        V_gens[:,m,iteration+1] = W*V_gens[:,m,iteration] + C1*np.random.uniform(0,1)*(pB_parameters[:,m] - Parameters[:,m,iteration]) + C2*np.random.uniform(0,1)*(gB_parameters- Parameters[:,m,iteration])
        for s in range(2):
            if V_gens[s,m,iteration+1] > VelMax[s]:
                V_gens[s,m,iteration+1] = np.copy(VelMax[s])
            if V_gens[s,m,iteration+1] < VelMin[s]:
                V_gens[s,m,iteration+1] = np.copy(VelMin[s])
        # new microgrid parameters for the next generation
        # value from previous position plus some movement based on velocity & PSO parameters
        Parameters[:,m,iteration+1] = Parameters[:,m,iteration] + CF*V_gens[:,m,iteration+1]
        #// ceilings based on limits for specific microgrid parameters
        for q in range(2):
            if Parameters[q,m,iteration+1] > upper_bounds[q]:
                Parameters[q,m,iteration+1] = np.copy(upper_bounds[q])
            if Parameters[q,m,iteration+1] < lower_bounds[q]:
                Parameters[q,m,iteration+1] = np.copy(lower_bounds[q])
            if Parameters[q,m,iteration+1] < roundDownSize:
                Parameters[q,m,iteration+1] = 0
           
    #Stopping Criteria (once all individuals are calculated)
    if iteration < 30:
        testLim = np.copy(lowTestLim)
    else:
        testLim = np.copy(highTestLim)
    match = 0
    for ind in range(numInd):
        Parameters_test = (Parameters[:,ind,iteration] - gB_parameters)/(gB_parameters + 0.0001)
        Parameters_dev = np.zeros(2)
        for r in range(2):
             if abs(Parameters_test[r]) <= testLim:
                Parameters_dev[r] = 1
        PSO_match = sum(Parameters_dev)
        if PSO_match == 2:
            match = match + 1 #equivalent of previous code
    if match > convergenceRequirement:
        print "Stopping due to matching parameter values"
    
    #Checking for minimal change between bests
    if iteration >= 2:
        diff1 = abs(gB_change_tariff[iteration-2]-gB_change_tariff[iteration-1])
        diff2 = abs(gB_change_tariff[iteration-1] - gB_change_tariff[iteration])
        t_diff = diff1+diff2
        if t_diff < stopLimit:
            print "Stopping due to minimal change between global bests"
    
    
    #Print generation results
    print "Global Best Tariff "+ str(gB_tariff)
    print "Best Tariff in Generation " + str(gB_change_tariff[iteration])
    iteration += 1

end_time = time.time()
total_time = end_time - start_time
print "Time to complete generation is " + str(total_time)

#Best Solution Variables Saved
Total_Cost = sum(gB_Cost)
#add extra variables to solution output
#gB_plot_variables.add()
#also add total time

#gB_optimization_output_var = np.zeros((4,maxGen-1))
gB_optimization_output_var = {'BattkW':gB_change_parameters[0,:],'PVkW':gB_change_parameters[1,:], 'Propane':gB_change_propane,'Tariff':gB_change_tariff}

#gB_optimization_output_var = np.transpose(np.concatenate((gB_change_parameters[0,:],gB_change_parameters[1,:], gB_change_propane,gB_change_tariff), axis=1))
gB_optimization_output =pd.DataFrame(gB_optimization_output_var)#, columns =['BattkW','PVkW','Propane','Tariff'])            

#Print Results to Excel (Optimization and Solution Variables)
filename_xlsx = "uGrid_Output_"+PSO_Parameters['output_name'][0]+".xlsx"
writer = pd.ExcelWriter(filename_xlsx, engine='xlsxwriter')

# Convert the dataframe to an XlsxWriter Excel object.
gB_plot_variables.to_excel(writer, sheet_name='Solution Output')
gB_optimization_output.to_excel(writer, sheet_name='Optimization Output')

# Close the Pandas Excel writer and output the Excel file.
writer.save()

#Plot power to the load and the load curve
gB_plot_variables.plot(y = ['LoadkW', 'genLoad', 'Batt_Power_to_Load', 'PV_Power','dumpload'], kind='line')
filename_Plot_LoadDispatch = "Power_to_Load_"+PSO_Parameters['output_name'][0]+".pdf"
plt.savefig(filename_Plot_LoadDispatch)
#Plot power to battery and battery SOC
gB_plot_variables.plot(y = ['Batt_SOC', 'Charge', 'PV_Batt_Change_Power','Batt_Power_to_Load_neg', 'Batt_frac', 'Gen_Batt_Charge_Power'], kind='line')
filename_Plot_BatteryDispatch = "Battery_to_Load_"+PSO_Parameters['output_name'][0]+".pdf"
plt.savefig(filename_Plot_BatteryDispatch)


    
    



