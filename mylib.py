import xmlrpc.client
import csv
import time
import os
import sys
import re
import subprocess

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


def run_linsim(input_file, output_folder, simulation_file):
    print("Running linsim. Please close linsim so that simulation can continue.")
    p = subprocess.run(['linsim',
                        '--input_file=' + input_file,
                        '--output_folder=' + output_folder,
                        '--run_batch=' + simulation_file])


def get_datapoint(fldigi_connection,
                  mode,
                  test_data,
                  center_freq,
                  linsimconf,
                  fn_wavfile,
                  fn_temp_folder):
    client = fldigi_connection
    assert mode in client.modem.get_names()
