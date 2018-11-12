#!/usr/bin/python3
import numpy as np
import json
import mylib as t

from myconf import *  # dn_results_folder, fn_simulation_templates, fn_test_message,

#'''
datapoints = [i for i in
              json.loads(open(fn_datapoints, 'r').read())
              if 'simulation string' in i]
#'''

profile_names = {}
for i in open(fn_simulation_templates).readlines()[1:]:
    parameters = t.parse_simulation_parameters(i)
    profile_names[parameters['profile']] = parameters['title'].strip('"')

modes_to_test = t.get_test_modes(fn_modes_to_test)
#modes_to_test = ['QPSK250','MT63-2KL','THOR11']

simulation_profiles = {}
for p in profile_names:
    for m in modes_to_test:
        simulation_profiles[(m, p)] = np.zeros((0,2))

#'''
for d in datapoints:
    parameters = t.parse_simulation_parameters(d['simulation string'])
    p = (d['mode'], parameters['profile'])
    e = [[parameters['awgn s/n'], d['error rate']]]
    simulation_profiles[p] = np.array(list(simulation_profiles[p]) + e)
#'''

trimmed_test_data = t.trim(open(fn_test_message, 'rb').read())


fldigi = t.start_fldigi(dn_fldigi_configuration_folder,
                        dn_fldigi_home_folder,
                        fn_macro_file,
                        fn_audio,
                        fn_message)


new_datapoints = []
target_error_rate=1/100
for p in simulation_profiles:
    #if p[0] not in ['BPSK31']:
    #if 'thor' not in p[0].lower():
    #    #print(p)
    #    continue
    l = simulation_profiles[p]  # list of [s/n, error rate]
    aux = np.array(l).transpose()
    new_snrs = t.suggest_samples(aux[0], aux[1], target_error_rate, 1)

    base_suffix = profile_names[p[1]].replace(' ', '_')
    new_snrs.sort()
    for s in new_snrs:
        # s=s-10 #DEBUG
        suffix = base_suffix+'_SN{0}{1:04.1f}'.format(
            'p' if s >= 0 else 'n',
            abs(s))
        simstring = t.unparse_simulation_parameters({
            'title': suffix,
            'awgn enable': 1,
            'awgn s/n': s,
            'profile': p[1]})
        print(p[0], simstring)
        dp = {'awgn s/n': s,
              'error rate': None,
              'message length': len(trimmed_test_data),
              'mode': p[0],
              'simulation string': simstring,
              'suffix': suffix}
        dp2 = t.evaluate_datapoint(fldigi,
                                   fn_test_message,
                                   fn_simulation_file,
                                   fn_message,
                                   fn_audio,
                                   dp)
        print(dp2['error rate'])
        new_datapoints.append(dp2)

new_datapoints.extend(datapoints)
open(fn_datapoints+'_new', 'w').write(json.dumps(new_datapoints, indent=' '))
