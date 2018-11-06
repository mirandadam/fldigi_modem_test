#!/usr/bin/python3
import numpy as np
import json
import mylib as t

from myconf import *  # dn_results_folder, fn_simulation_templates, fn_test_message,

datapoints = [i for i in
              json.loads(open(fn_datapoints, 'r').read())
              if 'simulation string' in i]

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

trimmed_test_data = t.trim(open(fn_test_message, 'rb').read())


fldigi = t.start_fldigi(dn_fldigi_configuration_folder,
                        dn_fldigi_home_folder,
                        fn_macro_file,
                        fn_audio,
                        fn_message)

fn_test_message_alternate = fn_test_message+'_alternate'
open(fn_test_message_alternate, 'w').write(
    '='*40+open(fn_test_message).read()+'+'*40
)

new_datapoints = []
for p in simulation_profiles:
    l = simulation_profiles[p]  # list of [s/n, error rate]
    aux = np.array(l).transpose()
    #new_snrs = t.suggest_samples(aux[0], aux[1], 1/1000, 1)
    new_snrs = t.suggest_samples(aux[0], aux[1], 1/1000, 1)

    base_suffix = profile_names[p[1]].replace(' ', '_')
    new_snrs.sort()
    for s in new_snrs:  # [:1]:
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
        if dp['mode'] in ['THOR100', 'THOR50x1', 'THOR50x2']:
            dp2 = t.evaluate_datapoint(fldigi,
                                       fn_test_message_alternate,
                                       fn_simulation_file,
                                       fn_message,
                                       fn_audio,
                                       dp)
        else:
            dp2 = t.evaluate_datapoint(fldigi,
                                       fn_test_message,
                                       fn_simulation_file,
                                       fn_message,
                                       fn_audio,
                                       dp)
        print(dp2['error rate'])
        new_datapoints.append(dp2)

datapoints.extend(new_datapoints)

open(fn_datapoints+'_new', 'w').write(json.dumps(datapoints))
