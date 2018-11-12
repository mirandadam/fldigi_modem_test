import json
import numpy as np
import matplotlib.pyplot as plt

import mylib as t

from myconf import *  # dn_results_folder, fn_simulation_templates, fn_test_message,


datapoints = [i for i in
              json.loads(open(fn_datapoints, 'r').read())
              if 'simulation string' in i]

mode_info = json.loads(open(fn_mode_info, 'r').read())

profile_names = {}
for i in open(fn_simulation_templates).readlines()[1:]:
    parameters = t.parse_simulation_parameters(i)
    profile_names[parameters['profile']] = parameters['title'].strip('"')

simulation_profiles = {}
for d in datapoints:
    parameters = t.parse_simulation_parameters(d['simulation string'])
    p = (d['mode'], parameters['profile'])
    e = [[parameters['awgn s/n'], d['error rate']]]
    simulation_profiles[p] = simulation_profiles.get(p, []) + e

for p in simulation_profiles:
    x, y = np.array(sorted(simulation_profiles[p])).transpose()
    y = np.minimum(1., y)
    cut_point = (t.suggest_samples(x, y, 1/100, 0.)+[40])[0]
    n = profile_names[p[1]]
    #if n != 'Mid_Latitude_Disturbed':
    if n != 'Mid_Latitude_Disturbed_NVIS':
    #if n != 'Frequency_Shifter':
    #if n != 'Direct_Path':
        continue
    #if 'psk' not in p[0].lower():
    #    continue
    speed = [i['speed (char/s)'] for i in mode_info if i['mode'] == p[0]][0]
    speed = np.log10(speed)
    print((p[0], n, speed, cut_point))
    plt.scatter(cut_point, speed)
    plt.annotate(p[0],
                 xy=(cut_point, speed))

#plt.plot(x, y)
plt.show()
