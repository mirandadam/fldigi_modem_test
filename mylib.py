import xmlrpc.client
import csv
import time
import os
import sys
import re
import subprocess
import wave
import numpy as np
import shutil
# import matplotlib.pyplot as plt

simulation_file_header = "TITLE,AWGN,S/N,P1,SPREAD_1,OFFSET_1,P2,DELAY_2,SPREAD_2,OFFSET_2,P3,DELAY_3,SPREAD_3,OFFSET_3"


def initial_setup(client):
    client.main.set_rsid(False)
    client.main.set_txid(False)
    client.modem.set_carrier(1500)
    # client.main.set_squelch(False)
    client.main.set_squelch(True)
    client.main.set_squelch_level(0.5)
    run_macro(client, 'stop_generate')
    run_macro(client, 'stop_playback')


def wait(t=1):
    time.sleep(t)


def wait_RX(client):
    while client.main.get_trx_state() != 'RX':
        sys.stdout.write('.')
        sys.stdout.flush()
        wait()
    print('')


def get_test_modes(fname):
    f = open(fname, 'r')
    r = csv.reader(f, delimiter=',', quotechar='"')
    modes = sorted(list(i[2] for i in r if i[8] == '1'))
    f.close()
    return modes


def get_rx(client):
    r = client.rx.get_data().data
    return r


def wait_closed(fname):
    r = subprocess.run(['lsof', fname], stdout=subprocess.PIPE).returncode
    while r == 0:
        sys.stdout.write('x')
        sys.stdout.flush()
        wait()
        r = subprocess.run(['lsof', fname], stdout=subprocess.PIPE).returncode
    print('')


def get_rx_until_file_closed(client, fname):
    rx = get_rx(client)
    r = subprocess.run(['lsof', fname], stdout=subprocess.PIPE).returncode
    while r == 0:
        sys.stdout.write('x')
        sys.stdout.flush()
        wait()
        rx += get_rx(client)
        r = subprocess.run(['lsof', fname], stdout=subprocess.PIPE).returncode
    print('')
    return rx


re_begin = re.compile(b'[=]{3}[=]*')
re_end = re.compile(b'[+]{3}[+]*')


def trim(data):
    return re_end.split(re_begin.split(data)[-1])[0]


def wait_end_received(client, timeout=180):
    rx_data = get_rx(client)
    t0 = time.time()
    tlast = time.time()
    while not re_end.search(rx_data) and time.time() < (t0+timeout):
        wait()
        rx_data += get_rx(client)
        if time.time()-tlast > 5:
            tlast = time.time()
            print(rx_data)
    return rx_data


macro_file_template = '''//fldigi macro definition file extended

/$ 0 Generate
<WAV_TXGENERATE:{0}>

/$ 1 Stop generate
<WAV_STOP_TXGENERATE>

/$ 2 Playback
<WAV_PLAYBACK:{0}>

/$ 3 Stop playback
<WAV_STOP_PLAYBACK>

/$ 4 High speed on
<HS:on>

/$ 5 High speed off
<HS:off>

/$ 6 CPS test
<WAV_FILE:{1}>
'''

macros = {'generate': 0,
          'stop_generate': 1,
          'playback': 2,
          'stop_playback': 3,
          'highspeed_on': 4,
          'highspeed_off': 5,
          'cps_test': 6}


def run_macro(client, macroname):
    client.main.run_macro(macros[macroname])


'''
def connect():
    return xmlrpc.client.ServerProxy("http://127.0.0.1:7362/")

def open_fldigi(configuration_folder, home_folder):
    if not os.path.exists(configuration_folder):
        os.makedirs(configuration_folder)
    if not os.path.exists(home_folder):
        os.makedirs(home_folder)
    p = subprocess.Popen(
        ['fldigi',
         '--config-dir', configuration_folder,
         '--home-dir', home_folder],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    return p
'''


def start_fldigi(configuration_folder, home_folder,
                 macro_file, audio_file, message_file):
    '''
    This function does what is necessary to return a working
    xmlrpc connection to an instance of fldigi configured
    with the required macros.
    '''
    initial_conf = False
    if not os.path.exists(configuration_folder):
        os.makedirs(configuration_folder)
        initial_conf = True
    if not os.path.exists(home_folder):
        os.makedirs(home_folder)
        initial_conf = True
    if not os.path.exists(os.path.dirname(macro_file)):
        os.makedirs(os.path.dirname(macro_file))
        initial_conf = True
    if not os.path.exists(os.path.dirname(audio_file)):
        os.makedirs(os.path.dirname(audio_file))
        initial_conf = True
    if not os.path.exists(os.path.dirname(message_file)):
        os.makedirs(os.path.dirname(message_file))
        initial_conf = True

    try:
        # if whe can connect to a running fldigi, ask the user to close it.
        fldigi = xmlrpc.client.ServerProxy("http://127.0.0.1:7362/")  # returns a xmlrpc connection
        if fldigi.modem.get_names():
            print('***Running fldigi found. Please terminate FLDIGI before running this script.***')
            return None
    except ConnectionRefusedError:
        print('No running fldigi session found on local port 7362. Opening a new one.')

    f = open(macro_file, 'w')
    f.write(macro_file_template.format(audio_file, message_file))
    f.close()
    p = subprocess.Popen(
        ['fldigi',
         '--config-dir', configuration_folder,
         '--home-dir', home_folder],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    wait(3)

    if initial_conf:
        print("Skip all fldigi configuration and ***CLOSE FLDIGI***.")
        p.wait()
        f = open(macro_file, 'w')
        f.write(macro_file_template.format(audio_file, message_file))
        f.close()
        p = subprocess.Popen(
            ['fldigi',
             '--config-dir', configuration_folder,
             '--home-dir', home_folder],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        wait(3)

    fldigi = xmlrpc.client.ServerProxy("http://127.0.0.1:7362/")  # returns a xmlrpc connection
    initial_setup(fldigi)
    return fldigi


def run_linsim(input_file, output_folder, simulation_file):
    p = subprocess.run(['linsim',
                        '--input_file=' + input_file,
                        '--output_folder=' + output_folder,
                        '--run_batch=' + simulation_file])


def evaluate_datapoint(client,
                       test_data_file,
                       simulation_file,
                       message_file,
                       audio_file,
                       datapoint):
    '''
    Evaluate the error rate using the conditions in a datapoint.
    audio_file and message_file have to be the same as fn_audio and fn_message;
      these two files have to be in sync with the macros configured in fldigi.

    example_datapoint = {
        "mode": "PSK500C2",
        "awgn s/n": -30,
        "suffix": "AWGN_SNn30.0",
        "message length": 143,
        "simulation string": "\"AWGN_SNn30.0\",1,-30,0,0,0,0,0,0,0,0,0,0,0,0",
        "error rate": None
    }
    '''

    assert len(set(datapoint.keys()).symmetric_difference({
        'mode',
        'awgn s/n',
        'suffix',
        'message length',
        'simulation string',
        'error rate'
    })) == 0
    assert datapoint['mode'] in client.modem.get_names()
    simulation_parameters = datapoint['simulation string'].split(',')
    assert len(simulation_parameters) == 15
    for p, i in enumerate(simulation_parameters):
        if p == '':
            simulation_parameters[i] = '0.0'
        elif i > 0:
            simulation_parameters[i] = str(float(simulation_parameters[i]))
    # copy datapoint to output
    output = json.loads(json.dumps(datapoint))
    output['simulation string'] = ','.join(simulation_parameters)

    test_data = open(test_data_file, 'r').read()
    f = open(simulation_file, 'w')
    f.write(simulation_file_header+os.linesep)
    f.write(output['simulation string'])
    f.close()
    client.modem.set_by_name(output['mode'])
    generate_wav(client, test_data_file, audio_file, message_file, audio_file)
    decoded_data = wav_decode(client, audio_file, audio_file)
    ml = len(trim(test_data))
    ed = Levenshtein.distance(trim(test_data), trim(decoded_data))
    output['message length'] = ml
    output['error rate'] = ed/ml
    return output


def generate_wav(client, input_file, output_audio, fn_message, fn_audio):
    client.text.clear_tx()
    if input_file != fn_message:
        shutil.copy(input_file, fn_message)
    run_macro(client, 'generate')
    wait()
    run_macro(client, 'cps_test')
    wait_RX(client)
    run_macro(client, 'stop_generate')
    wait_closed(fn_audio)
    if fn_audio != output_audio:
        shutil.copy(fn_audio, output_audio)


def get_wav_duration(fn_wavefile):
    w = wave.open(fn_wavefile, 'rb')
    framerate = w.getframerate()
    nframes = w.getnframes()
    w.close()
    return float(nframes)/framerate


def get_wav_bandwidth(fn_wavefile, center_frequency):
    '''
    occupied bandwidth is calculated as the frequency interval which contains
    95% of the signal power.
    '''
    w = wave.open(fn_wavefile, 'r')
    framerate = w.getframerate()
    assert w.getsampwidth() == 2  # 16 bits
    nframes = w.getnframes()
    signal = np.frombuffer(w.readframes(nframes), dtype='<i2')
    # power = (signal**2)/nframes  # energy over time
    fourier = np.fft.fft(signal)
    freq = np.fft.fftfreq(nframes, d=(1/framerate))
    # picking only positive frequencies:
    m = np.abs(fourier[np.where(freq >= 0)])**2  # signal power density
    f = freq[np.where(freq >= 0)]
    # folding the spectrum around at the center frequency
    f[np.where(f > center_frequency)] = 2*center_frequency - f[np.where(f > center_frequency)]
    # sorting
    m = m[np.argsort(f)]
    f = np.sort(f)
    # calculating cumulative power
    cumulative_power = np.cumsum(m)
    cumulative_power = cumulative_power/cumulative_power[-1]
    low_freq = f[np.where(cumulative_power > 0.05)][0]
    bw = 2*(center_frequency-low_freq)
    # print('bw', bw)
    # plt.plot(f, m)
    # plt.show()
    w.close()
    return bw


def wav_decode(client, fn_wavfile, fn_audio, wait_s=0):
    client.text.clear_rx()
    if fn_wavfile != fn_audio:
        shutil.copy(fn_wavfile, fn_audio)
    run_macro(client, 'playback')
    run_macro(client, 'highspeed_on')
    rx_data = get_rx(client)
    rx_data += get_rx_until_file_closed(client, fn_audio)
    wait(wait_s)
    run_macro(client, 'stop_playback')
    rx_data += get_rx(client)
    return rx_data
