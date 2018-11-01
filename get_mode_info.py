import os
import json
import shutil
import mylib as t

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

modes_to_test = t.get_test_modes(fn_modes_to_test)

try:
    fldigi = t.connect()  # returns a xmlrpc connection
    t.initial_setup(fldigi)
    fldigi_process = None
except ConnectionRefusedError:
    f = open(fn_macro_file, 'w')
    f.write(t.macro_file_template.format(fn_audio, fn_test_message))
    f.close()
    fldigi_process = t.open_fldigi(fn_fldigi_configuration_folder,
                                   fn_fldigi_home_folder)
    t.wait(3)
    fldigi = t.connect()  # returns a xmlrpc connection
    t.initial_setup(fldigi)

# get speed in cps of modem
test_message = open(fn_test_message, 'r').read()
speed = []
for m in modes_to_test:
    fldigi.modem.set_by_name(m)
    t.run_macro(fldigi, 'generate')
    t.wait()
    t.run_macro(fldigi, 'cps_test')
    t.wait_RX(fldigi)
    t.run_macro(fldigi, 'stop_generate')
    t.wait_closed(fn_audio)
    duration = t.get_wav_duration(fn_audio)
    os.rename(fn_test_message, fn_test_message+'_backup')
    f = open(fn_test_message, 'w')
    f.write('=')
    f.close()
    t.run_macro(fldigi, 'generate')
    t.wait()
    t.run_macro(fldigi, 'cps_test')
    t.wait_RX(fldigi)
    t.run_macro(fldigi, 'stop_generate')
    t.wait_closed(fn_audio)
    overhead = t.get_wav_duration(fn_audio)
    shutil.copy(fn_test_message+'_backup', fn_test_message)
    cps = (len(test_message)-1)/(duration-overhead)
    overhead = overhead-(1/cps)
    speed.append([m, cps, overhead])
    print(m, cps, overhead)

open(fn_output_folder+'mode_cps_overhead.json','w').write(json.dumps(speed))
