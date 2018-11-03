#!/usr/bin/python3
import os
import shutil
import mylib as t
import Levenshtein  # from python-levenshtein, for edit distance
import json
import sys

from myconf import *

assert os.path.exists(fn_test_message)
if not os.path.exists(dn_output_folder):
    os.makedirs(dn_output_folder)

modes_to_test = t.get_test_modes(fn_modes_to_test)

fldigi = t.start_fldigi(dn_fldigi_configuration_folder,
                        dn_fldigi_home_folder,
                        fn_macro_file,
                        fn_audio,
                        fn_message)

# testing if all the intended modes are recognized by fldigi:
try:
    commands = fldigi.fldigi.list()
except AttributeError:
    sys.exit(1)
accepted_modems = set(fldigi.modem.get_names())
intended_modems = set(modes_to_test)
assert accepted_modems.issuperset(intended_modems)
del commands, accepted_modems, intended_modems  # avoiding namespace pollution

t.initial_setup(fldigi)

# load test message
test_message = open(fn_test_message, 'r').read()


# thor 100 decoded text shows ok on fldigi screen, but does not read out on get_rx
# thor 16 is similar, but get_rx gets data only from the middle of the message onwards
# a workaround was implemented so they were dropped from the blacklist
blacklist = set()  # set(['THOR100','THOR16'])

all_datapoints = []

for m in modes_to_test:
    if m in blacklist:
        continue
    trimmed_test = t.trim(test_message.encode())
    finished = False
    count = 1
    while not finished:
        print('Running mode', modes_to_test.index(m), '('+m+')', 'attempt', count)
        fldigi.text.clear_tx()
        fldigi.text.clear_rx()
        fldigi.modem.set_by_name(m)
        t.run_macro(fldigi, 'generate')
        t.wait()
        shutil.copy(fn_test_message, fn_message)
        if m in ['THOR100', 'THOR16', 'THOR50x1', 'THOR50x2']:
            # Add extra padding
            f = open(fn_message, 'w')
            f.write('='*50)
            f.write(test_message.rstrip('\r\n\t '))
            f.write('+'*50)
            f.close()
        t.run_macro(fldigi, 'cps_test')
        t.wait_RX(fldigi)
        t.run_macro(fldigi, 'stop_generate')
        t.wait_closed(fn_audio)
        print('Checking...')
        # decode the file, wait more every failed attempt
        # The wait at the end is necessary for some slower modes
        # that close the file before finishing transmitting.
        # documented examples are Olivia and MT63
        rx_data = t.wav_decode(fldigi, fn_audio, fn_audio, (count-1)*2)
        trimmed_rx = t.trim(rx_data)
        # print(trimmed_rx)
        if trimmed_rx == trimmed_test:
            finished = True
        else:
            count = count+1
            t.initial_setup(fldigi)
            t.wait(2)
    fn_reference_audio = dn_output_folder+m+'.wav'
    os.rename(fn_audio, fn_reference_audio)

    print("Testing white noise...")
    datapoints = [{'mode': m,
                   'awgn s/n': i,
                   'suffix': 'AWGN_SN{0}{1:04.1f}'.format('p' if i >= 0 else 'n', abs(i)),
                   'message length': len(trimmed_rx),
                   'simulation string': None,
                   'error rate': None} for i in range(-30, 16, 5)]
    f = open(fn_simulation_file, 'w')
    f.write(t.simulation_file_header+os.linesep)
    for d in datapoints:
        if d['error rate'] is not None:
            continue
        d['simulation string'] = '"{0}",1,{1},0,0,0,0,0,0,0,0,0,0,0,0'.format(d['suffix'], d['awgn s/n'])
        f.write(d['simulation string']+os.linesep)

    f.close()
    t.run_linsim(fn_reference_audio, dn_output_folder, fn_simulation_file)
    for d in datapoints:
        if d['error rate'] is not None:
            continue
        fn_current_test = fn_reference_audio[:-4]+'.'+d['suffix']+'.wav'
        assert os.path.exists(fn_current_test)
        rx_data = t.wav_decode(fldigi, fn_current_test, fn_audio, 0)
        trimmed_rx = t.trim(rx_data)
        distance = Levenshtein.distance(trimmed_test, trimmed_rx)/len(trimmed_test)
        d['error rate'] = distance
        print(m, d['awgn s/n'], distance)
        os.unlink(fn_current_test)  # deleting wav file, or we will need a lot of space.
    f = open(fn_reference_audio[:-4]+'.json', 'w')
    f.write(json.dumps(datapoints, sort_keys=True))
    f.close()
    all_datapoints.extend(datapoints)
f = open(fn_datapoints, 'w')
f.write(json.dumps(all_datapoints, sort_keys=True))
f.close()

fldigi.fldigi.terminate(0)
print('Terminating running fldigi session found on local port 7362.')
t.wait(1)
