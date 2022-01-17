import time

import test
import pandas as pd

daa = pd.read_csv('20220104-212027-UTC_0-CAT3-IVER3-3089.log', header=0, delimiter=';')
lat = daa['Latitude']
lng = daa['Longitude']
tme = daa['Time']

for i in range(1, 200):
    print(i, lat[i], lng[i])
    print(test.heading(x=[lat[i], lng[i], ''.join(tme[i].split(':'))], y=10))
    time.sleep(1)



