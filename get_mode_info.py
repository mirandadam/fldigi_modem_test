import json
import shutil
import mylib as t
from myconf import *

modes_to_test = t.get_test_modes(fn_modes_to_test)

fldigi = t.start_fldigi(dn_fldigi_configuration_folder,
                        dn_fldigi_home_folder,
                        fn_macro_file,
                        fn_audio,
                        fn_message)

fn_test_message = dn_local_folder+'t2_cancao_do_exilio.txt'
# get speed in cps of modem
test_message = open(fn_test_message, 'r').read()
data = []
for m in modes_to_test:
    fldigi.modem.set_by_name(m)
    t.generate_wav(fldigi, fn_test_message, fn_audio, fn_message, fn_audio)
    duration = t.get_wav_duration(fn_audio)
    bandwidth = t.get_wav_bandwidth(fn_audio, 1500)
    f = open(fn_message, 'w')
    f.write('=')
    f.close()
    t.generate_wav(fldigi, fn_message, fn_audio, fn_message, fn_audio)
    overhead = t.get_wav_duration(fn_audio)
    cps = (len(test_message)-1)/(duration-overhead)
    overhead = overhead-(1/cps)
    datum = {'mode': m, 'speed (char/s)': cps, 'overhead (s)': overhead, 'bandwidth 95% (Hz)': bandwidth}
    print(datum)
    data.append(datum)
    print()

open(dn_output_folder+'mode_cps_overhead.json', 'w').write(json.dumps(data, sort_keys=True))
