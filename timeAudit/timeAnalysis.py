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

start_date = datetime(2020, 4, 6, 9)
end_date = datetime(2020, 4, 6, 15)
systems = ['tc1', 'mc1', ]


def retrieveAllData():
    """" Gets the data for each system and returns an easy to plot list"""
    dm = DataManager(get_exporter('CP'), root_dir='/tmp/rcm')
    ret = list()
    for sys in systems:
        start = datetime.now()
        print(start, 'Retrieving values for ta:' + sys + ':diff')
        sys_data = list(dm.getData('ta:' + sys + ':diff', start=start_date, end=end_date))
        print("Retrieved", len(sys_data), "values for", sys, "elapsed time ",datetime.now() - start)
        data_unzip = list(zip(*sys_data))  # data[0] is (datetime, val)
        data_unzip[1] = [x * 1000.0 for x in data_unzip[1]]  # convert to milliseconds
        data_unzip.append(sys)
        ret.append(data_unzip)
    return ret


data = retrieveAllData()

fig, ax1 = plt.subplots()
plt.title("Time differences")
for val in data:
    ax1.plot(val[0], val[1], label=val[2])
ax1.grid(True)
ax1.set_ylabel("Milliseconds")
plt.gcf().autofmt_xdate()
#ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5))
ax1.legend()
plt.show()

print("Ciao", datetime.now())
