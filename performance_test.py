#!/usr/bin/python3
import os
import shutil
import mylib as t


local_folder = os.path.abspath(__file__)
if os.path.isfile(local_folder):
    local_folder = os.path.dirname(local_folder)+os.sep

# input and output paths, configuration files.
fn_test_message = local_folder+'t0_joao_3_16.txt'
fn_fldigi_configuration_folder = local_folder+'fldigi_conf'+os.sep
fn_macro_file = fn_fldigi_configuration_folder+'macros'+os.sep+'macros.mdf'
fn_fldigi_home_folder = local_folder+'fldigi_home'+os.sep
fn_output_folder = local_folder+'audio_temp'+os.sep
fn_simulation_file = fn_output_folder+'simulation.csv'
fn_audio = fn_output_folder+'audio.wav'
fn_mode_info = local_folder+'mode_info.csv'

assert os.path.exists(fn_test_message)
if not os.path.exists(fn_output_folder):
    os.makedirs(fn_output_folder)

modes_to_test = t.get_test_modes(fn_mode_info)

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

fldigi_process = t.open_fldigi(fn_fldigi_configuration_folder,
                               fn_fldigi_home_folder)

t.wait(4)

fldigi = t.connect()  # returns a xmlrpc connection

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
    shutil.copy(fn_wavfile, fn_audio)
    t.run_macro(fldigi, 'playback')
    t.run_macro(fldigi, 'highspeed_on')
    rx_data = t.get_rx(fldigi)
    print('Checking...')
    rx_data += t.get_rx_until_file_closed(fldigi, fn_audio)
    t.wait(wait)
    t.run_macro(fldigi, 'stop_playback')
    rx_data += t.get_rx(fldigi)
    return rx_data


for m in modes_to_test[18:]:
    trimmed_test = t.trim(test_message.encode())
    finished = False
    count = 1
    while not finished:
        print('Running mode', modes_to_test.index(m), '('+m+')', 'attempt', count)
        fldigi.text.clear_tx()
        fldigi.text.clear_rx()
        fldigi.modem.set_by_name(m)
        # fldigi.text.add_tx(test_message+'^r')
        t.run_macro(fldigi, 'generate')
        t.wait()
        # fldigi.main.tx()
        t.run_macro(fldigi, 'cps_test')
        t.wait_RX(fldigi)
        t.run_macro(fldigi, 'stop_generate')
        t.wait_closed(fn_audio)
        fldigi.text.clear_rx()
        # adding 5 seconds of white noise before and after the signal
        '''
        os.rename(fn_audio, fn_audio+'_bkp.wav')
        subprocess.run(['sox',
                        'tests/noise.wav',
                        audio_fn+'_bkp.wav',
                        'tests/noise.wav',
                        audio_fn])
        '''
        t.run_macro(fldigi, 'playback')
        t.run_macro(fldigi, 'highspeed_on')
        rx_data = t.get_rx(fldigi)
        print('Checking...')
        rx_data += t.get_rx_until_file_closed(fldigi, fn_audio)
        # The following wait is necessary for some slower modes
        # that close the file before finishing transmitting.
        # documented examples are Olivia and MT63
        t.wait((count-1)*2)  # wait more every failed attempt
        t.run_macro(fldigi, 'stop_playback')
        rx_data += t.get_rx(fldigi)
        trimmed_rx = t.trim(rx_data)
        if trimmed_rx == trimmed_test:
            finished = True
        else:
            count = count+1
            t.initial_setup(fldigi)
            t.wait(2)
    if os.path.exists(fn_audio+'_bkp.wav'):
        os.rename(fn_audio+'_bkp.wav', fn_audio)
    fn_reference_audio = fn_output_folder+m+'.wav'
    os.rename(fn_audio, fn_reference_audio)
    print("Testing white noise...")

    datapoints = [(i, None) for i in range(-20, 11, 1)]
    finished = False

    while not finished:
        f = open(fn_simulation_file, 'w')
        f.write(t.simulation_file_header+os.linesep)
        for d in datapoints:
            if d[1] != None:
                continue
            temp = 'AWGN_SN{0}{1:04.1f}'.format('p' if d[0] >= 0 else 'n', abs(d[0]))
            f.write('"'+temp+'",1,{0},0,0,0,0,0,0,0,0,0,0,0,0'.format(d[0]) + os.linesep)
        f.close()
        t.run_linsim(fn_reference_audio, fn_output_folder, fn_simulation_file)
        for d in datapoints:
            if d[1] != None:
                continue
            temp = 'AWGN_SN{0}{1:04.1f}'.format('p' if d[0] >= 0 else 'n', abs(d[0]))
            fn_current_test = fn_reference_audio[:-4]+'.'+temp+'.wav'
            assert os.path.exists(fn_current_test)
            print("file", fn_current_test, "exists!")
            rx_data = wav_decode(fn_current_test, fn_audio, 0)
            trimmed_rx = t.trim(rx_data)
            print(trimmed_rx)


# fldigi_process.terminate()
# fldigi_process.wait()
# t.wait(10)
