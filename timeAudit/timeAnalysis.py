#! /usr/bin/python
"""
Print time differences
"""
import sys

sys.path.append('../')
from swglib.export import DataManager, get_exporter
from datetime import datetime, timedelta, date, timezone
import pdb
import matplotlib.pyplot as plt

SITE = 'CP'
start_date = datetime(2020, 4, 6, 10)
end_date = datetime(2020, 4, 6, 16)
systems = ['tc1', 'mc1', ]

if SITE == 'CP':  # Archiver returns UTC dates need to cover for that
    UTC_OFFSET = timedelta(hours=4)
    TZ = 'America/Santiago'


def retrieveAllData():
    """" Gets the data for each system and returns an easy to plot list"""
    dm = DataManager(get_exporter(SITE), root_dir='/tmp/rcm')
    ret = list()
    for sys in systems:
        start = datetime.now()
        print(start, 'Retrieving values for ta:' + sys + ':diff')
        sys_data = list(dm.getData('ta:' + sys + ':diff', start=start_date + UTC_OFFSET, end=end_date + UTC_OFFSET))
        print("Retrieved", len(sys_data), "values for", sys, "elapsed time ", datetime.now() - start)
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
# ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5))
ax1.legend()
ax1.set_ylim([-5., 5.])
ax1.xaxis_date(TZ)
plt.show()

print("Ciao", datetime.now())
