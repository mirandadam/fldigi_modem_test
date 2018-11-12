reset && killall fldigi
mv audio_temp/datapoints.json_new audio_temp/datapoints.json
rm audio_temp/*.wav
/home/a/anaconda3/bin/ipython3 -i /home/a/Desktop/git/fldigi_modem_test/2.1_add_datapoints.py
