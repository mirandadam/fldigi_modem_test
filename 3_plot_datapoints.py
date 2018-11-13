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
for n in profile_names.values():
    fig = plt.figure()
    fig.set_size_inches(10, 6)
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
        #if 'THOR11' == p[0]:
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
    print('')
    print(n)
    print('')
    print("Modes in the pareto frontier:")
    print('| Mode | Speed (cps) | S/N 1% |')
    print('| ---- | ----------- | ------ |')
    for aux in [point_set[i] for i in np.where(pareto_set)[0]]:
        print('|', aux[2], '|', round(aux[0], 1), '|', round(aux[1], 1), '|')
    fig.savefig(dn_results_folder+n+'.png')
plt.show()
