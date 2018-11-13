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
        'Modes not displayed where unable to decode with 1% or better error rate.\n'
        'Test message has 712 characters in pt-BR language (t2_cancao_do_exilio.txt).',
    )
    fig.subplots_adjust(bottom=0.15)
    ax.set_yscale('log')
    ax.set_ylabel('Transmission speed (cps)')
    for p in simulation_profiles:
        if n != profile_names[p[1]]:
            continue
        x, y = np.array(sorted(simulation_profiles[p])).transpose()
        y = np.minimum(1., y)
        cut_point = (t.suggest_samples(x, y, 1/100, 0.)+[60])[0]

        speed = [i['speed (char/s)'] for i in mode_info if i['mode'] == p[0]][0]
        #speed = np.log10(speed)
        if cut_point >= 60:
            print('Mode unable to decode with required accuracy:')
            print('', (p[0], n, speed, cut_point))
            continue

        ax.scatter(cut_point, speed)
        ax.annotate(p[0], xy=(cut_point, speed), fontsize=8)
    fig.savefig(dn_results_folder+n+'.png')
plt.show()
