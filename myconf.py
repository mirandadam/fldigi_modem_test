import os

dn_local_folder = os.path.abspath(__file__)
if os.path.isfile(dn_local_folder):
    dn_local_folder = os.path.dirname(dn_local_folder)+os.sep


# input and output paths, configuration files.
fn_test_message = dn_local_folder+'t0_joao_3_16.txt'
dn_fldigi_configuration_folder = dn_local_folder+'fldigi_conf'+os.sep
fn_macro_file = dn_fldigi_configuration_folder+'macros'+os.sep+'macros.mdf'
dn_fldigi_home_folder = dn_local_folder+'fldigi_home'+os.sep
dn_output_folder = dn_local_folder+'audio_temp'+os.sep
fn_simulation_file = dn_output_folder+'simulation.csv'
fn_audio = dn_output_folder+'audio.wav'
fn_message = dn_output_folder+'message.txt'
fn_modes_to_test = dn_local_folder+'modes_to_test.csv'
fn_datapoints = dn_output_folder+'datapoints.json'
fn_mode_info = dn_output_folder+'mode_info.json'
dn_results_folder = dn_local_folder+'results'+os.sep
fn_simulation_templates = dn_local_folder+'simulation_templates.csv'
