reset && killall fldigi
mv audio_temp/datapoints.json_new audio_temp/datapoints.json
rm audio_temp/*.wav
~/anaconda3/bin/ipython3 -i 2.1_add_datapoints.py
