#!/usr/bin/python3
import os
import shutil
import mylib as t
import Levenshtein  # from python-levenshtein, for edit distance
import json


local_folder = os.path.abspath(__file__)
if os.path.isfile(local_folder):
    local_folder = os.path.dirname(local_folder)+os.sep

# input and output paths, configuration files.
fn_test_message = local_folder+'t0_joao_3_16.txt'
fn_test_message_alternate = local_folder+'t0_joao_3_16_alternate.txt'
fn_fldigi_configuration_folder = local_folder+'fldigi_conf'+os.sep
fn_macro_file = fn_fldigi_configuration_folder+'macros'+os.sep+'macros.mdf'
fn_fldigi_home_folder = local_folder+'fldigi_home'+os.sep
fn_output_folder = local_folder+'audio_temp'+os.sep
fn_simulation_file = fn_output_folder+'simulation.csv'
fn_audio = fn_output_folder+'audio.wav'
fn_modes_to_test = local_folder+'modes_to_test.csv'

assert os.path.exists(fn_test_message)
if not os.path.exists(fn_output_folder):
    os.makedirs(fn_output_folder)

modes_to_test = t.get_test_modes(fn_modes_to_test)

if not os.path.exists(fn_macro_file):
    print("Opening FLDIGI to populate custom configuration.")
    print("***Please skip all configuration and CLOSE FLDIGI.***")
    fldigi_process = t.open_fldigi(fn_fldigi_configuration_folder,
                                   fn_fldigi_home_folder)
    fldigi_process.wait()
    del fldigi_process
    assert os.path.exists(fn_macro_file)
    print("Launching fldigi again with updated macro file.")

f = open(fn_macro_file, 'w')
f.write(t.macro_file_template.format(fn_audio, fn_test_message))
f.close()

try:
    fldigi = t.connect()  # returns a xmlrpc connection
    t.initial_setup(fldigi)
    fldigi_process = None
except ConnectionRefusedError:
    fldigi_process = t.open_fldigi(fn_fldigi_configuration_folder,
                                   fn_fldigi_home_folder)
    t.wait(3)
    fldigi = t.connect()  # returns a xmlrpc connection
    t.initial_setup(fldigi)

# testing if all the intended modes are recognized by fldigi:
commands = fldigi.fldigi.list()
accepted_modems = set(fldigi.modem.get_names())
intended_modems = set(modes_to_test)
assert accepted_modems.issuperset(intended_modems)
del commands, accepted_modems, intended_modems  # avoiding namespace pollution

t.initial_setup(fldigi)

# load test message
test_message = open(fn_test_message, 'r').read()


def wav_decode(fn_wavfile, fn_audio, wait=0):
    fldigi.text.clear_rx()
    if fn_wavfile != fn_audio:
        shutil.copy(fn_wavfile, fn_audio)
    t.run_macro(fldigi, 'playback')
    t.run_macro(fldigi, 'highspeed_on')
    rx_data = t.get_rx(fldigi)
    rx_data += t.get_rx_until_file_closed(fldigi, fn_audio)
    t.wait(wait)
    t.run_macro(fldigi, 'stop_playback')
    rx_data += t.get_rx(fldigi)
    return rx_data


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
        if m[:4] == 'THOR' and 'Micro' not in m:
            # use alternate test message with extra padding
            os.rename(fn_test_message, fn_test_message+'_backup')
            os.rename(fn_test_message_alternate, fn_test_message)
        t.run_macro(fldigi, 'cps_test')
        t.wait_RX(fldigi)
        t.run_macro(fldigi, 'stop_generate')
        t.wait_closed(fn_audio)
        if m[:4] == 'THOR' and 'Micro' not in m:
            # replace the original file
            os.rename(fn_test_message, fn_test_message_alternate)
            shutil.copy(fn_test_message+'_backup', fn_test_message)
        print('Checking...')
        # decode the file, wait more every failed attempt
        # The wait at the end is necessary for some slower modes
        # that close the file before finishing transmitting.
        # documented examples are Olivia and MT63
        rx_data = wav_decode(fn_audio, fn_audio, (count-1)*2)
        trimmed_rx = t.trim(rx_data)
        # print(trimmed_rx)
        if trimmed_rx == trimmed_test:
            finished = True
        else:
            count = count+1
            t.initial_setup(fldigi)
            t.wait(2)
    fn_reference_audio = fn_output_folder+m+'.wav'
    os.rename(fn_audio, fn_reference_audio)

    print("Testing white noise...")
    datapoints = [[i,  # id
                   'AWGN_SN{0}{1:04.1f}'.format('p' if i >= 0 else 'n', abs(i)),  # prefix
                   None, len(trimmed_rx)]  # measurement result
                  for i in range(-20, 16, 1)]
    f = open(fn_simulation_file, 'w')
    f.write(t.simulation_file_header+os.linesep)
    for d in datapoints:
        if d[2] is not None:
            continue
        f.write('"{1}",1,{0},0,0,0,0,0,0,0,0,0,0,0,0'.format(d[0], d[1]) + os.linesep)
    f.close()
    t.run_linsim(fn_reference_audio, fn_output_folder, fn_simulation_file)
    for d in datapoints:
        if d[2] is not None:
            continue
        fn_current_test = fn_reference_audio[:-4]+'.'+d[1]+'.wav'
        assert os.path.exists(fn_current_test)
        rx_data = wav_decode(fn_current_test, fn_audio, 0)
        trimmed_rx = t.trim(rx_data)
        distance = Levenshtein.distance(trimmed_test, trimmed_rx)/len(trimmed_test)
        d[2] = distance
        print(m, d[0], distance)
        os.unlink(fn_current_test)  # deleting wav file, or we will need a lot of space.
    f = open(fn_reference_audio[:-4]+'.json', 'w')
    f.write(json.dumps(datapoints))
    f.close()
    all_datapoints.append([m, datapoints])
f = open(fn_output_folder+'all.json', 'w')
f.write(json.dumps(all_datapoints))
f.close()

# fldigi_process.terminate()
# fldigi_process.wait()
# t.wait(10)
