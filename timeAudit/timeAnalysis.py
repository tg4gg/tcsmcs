#! /usr/bin/python
"""
Print time differences
"""
import sys

sys.path.append('../')
from swglib.export import DataManager, get_exporter
from datetime import datetime, timedelta, date
import pdb
import matplotlib.pyplot as plt

start_date = datetime(2020, 4, 2, 22)
end_date = datetime(2020, 4, 3, 8)
systems = ['tc1', 'mc1',]

def retrieveAllData():
    """" Gets the data for each system and returns an easy to plot list"""
    dm = DataManager(get_exporter('CP'), root_dir='/tmp/rcm')
    ret = list()
    for sys in systems:
        print('Retrieving values for ta:' + sys + ':diff', datetime.now())
        sys_data = list(dm.getData('ta:' + sys + ':diff', start=start_date, end=end_date))
        print("Retrieved", len(sys_data), "values for", sys, datetime.now())  # data[0] is (datetime, val)
        data_unzip = list(zip(*sys_data))
        data_unzip[1] = [x * 1000.0 for x in data_unzip[1]]  # convert to milliseconds
        ret.append(data_unzip)
    return ret


data = retrieveAllData()

fig, ax1 = plt.subplots()
plt.title("Time differences")
for val in data:
    ax1.plot(val[0], val[1])
ax1.grid(True)
ax1.set_ylabel("Milliseconds")
plt.gcf().autofmt_xdate()
plt.show()

print("Ciao", datetime.now())
