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

# plotting the 1% point for all the profiles:
profile_order = [
    'Direct_Path',
    'CCIR_520_2_Good_Conditions',
    'CCIR_520_2_Poor_Conditions',
    'CCIR_520_2_Doppler_Fading',
    'CCIR_520_2_Flutter_Fading',
    'Low_Latitude_Moderate',
    'Low_Latitude_Disturbed',
    'Mid_Latitude_Quiet',
    'Mid_Latitude_Moderate',
    'Mid_Latitude_Disturbed',
    'Mid_Latitude_Disturbed_NVIS',
    'High_Latitude_Moderate',
    'High_Latitude_Disturbed',
    'Frequency_Shifter'
]
assert len(set(profile_order).symmetric_difference(set(profile_names.values()))) == 0
f = open(fn_results_md, 'w')
f.write('### Mode information\n\n')
f.write('| Mode | Speed (char/s) | Bandwidth 95% power (Hz) | Overhead (s) |\n')
f.write('| ---- | -------------- | ------------------ | ------------ |\n')
aux = []
for m in mode_info:
    aux.append([m['mode'], m['speed (char/s)'], m['bandwidth 95% (Hz)'], m['overhead (s)']])
aux.sort(key=lambda x: (x[0][:3].replace('8','R'), round(x[1], 2), round(x[3], 2), x[2]))
for m in aux:
    f.write('| '+m[0]+' | '+str(round(m[1], 2))+' | '+str(round(m[2], 1))+' | '+str(round(m[3], 2))+' |\n')
del aux, m
f.write('\n')

f.write('### Scatter plots\n\n')
for n in profile_order:  # profile_names.values():
    fig = plt.figure()
    fig.set_size_inches(12, 8)
    ax = plt.axes()
    plt.title('Linsim profile: '+n.replace('_', ' '))
    ax.set_xscale('linear')
    ax.set_xlabel(
        'Signal to noise ratio in dB where error rate is 1%\n'
        'Modes not displayed were unable to decode with 1% or better error rate.\n'
        'Test message has 712 characters in pt-BR language (t2_cancao_do_exilio.txt).',
    )
    fig.subplots_adjust(bottom=0.15)
    ax.set_yscale('log')
    ax.set_ylabel('Transmission speed (cps)')
    point_set = []
    for p in simulation_profiles:
        if n != profile_names[p[1]]:
            continue
        x, y = np.array(sorted(simulation_profiles[p])).transpose()
        y = np.minimum(1., y)
        cut_point = (t.suggest_samples(x, y, 1/100, 0.)+[60])[0]

        speed = [i['speed (char/s)'] for i in mode_info if i['mode'] == p[0]][0]
        #speed = np.log10(speed)
        if cut_point >= 60:
            #print('Mode unable to decode with required accuracy:')
            #print('', (p[0], n, speed, cut_point))
            continue
        # if 'THOR11' == p[0]:
        #    print('', (p[0], n, speed, cut_point))
        point_set.append((speed, cut_point, p[0]))
        ax.scatter(cut_point, speed)
        ax.annotate(p[0], xy=(cut_point, speed), fontsize=8)
    point_set.sort(reverse=True)
    pareto_set = np.zeros(len(point_set), dtype='bool')
    pareto_set[0] = True
    sensitivity = point_set[0][1]  # best sensitivity seen so far
    for i in range(len(point_set)-1):
        # we already know that the speed is decrescent, so any point
        # down the line has to improve on sensitivity to be included
        # in the pareto frontier
        if point_set[i+1][1] < sensitivity:
            # if the sensitivity of the next point is better than all previous ones
            sensitivity = point_set[i+1][1]
            pareto_set[i+1] = True
        if (point_set[i+1][0] == point_set[i][0] and
                point_set[i+1][1] == point_set[i][1]):
                # we also add equal points to the pareto set
            pareto_set[i+1] = pareto_set[i]

    fig.savefig(dn_results_folder+n+'.png')

    f.write('#### Linsim profile: '+n.replace('_', ' ')+'\n\n')
    f.write('---\n\n')
    f.write('!['+n+'](results/'+n+'.png)\n\n')
    f.write('Modes in the pareto frontier:\n\n')
    f.write('| Mode | Speed (cps) | S/N 1% |\n')
    f.write('| ---- | ----------- | ------ |\n')
    for aux in [point_set[i] for i in np.where(pareto_set)[0]]:
        f.write('| '+aux[2] +
                ' | '+str(round(aux[0], 2)) +
                ' | '+str(round(aux[1], 2)) +
                ' |\n')
    f.write('\n')

f.close()
plt.show()
