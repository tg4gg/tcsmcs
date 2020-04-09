#! /usr/bin/python
"""
Print time differences
When Archiver is down/restarted ArchiveExport reports 2 false zeros with the same time stamps as the last record
"""
import sys

sys.path.append('../')
from swglib.export import DataManager, get_exporter
from datetime import datetime, timedelta, date, timezone
import pdb
import matplotlib.pyplot as plt
from collections import namedtuple

SITE = 'CP'
start_date = datetime(2020, 4, 8, 17, 00)
end_date =   datetime(2020, 4, 9, 5, 00)
systems = ['tc1', 'mc1', ]
SystemData = namedtuple('SystemData', 'name times vals')

if SITE == 'CP':  # Archiver returns UTC dates, need to cover for that
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
        if len(data_unzip) > 0:
            sys_data = SystemData(sys, data_unzip[0], [x * 1000.0 for x in data_unzip[1]])  # convert to milliseconds
            #periodicity = [abs((sys_data.vals[i+1]-sys_data.vals[i])) for i in range(len(sys_data.vals)-1)]
            #[if period  for period in periodicity]
            #pdb.set_trace()
            ret.append(sys_data)
        else:
            print("No data found for {0} in the specified period.".format(sys))
    return ret


data = retrieveAllData()

fig, ax1 = plt.subplots()
plt.title("Time differences - ta is running as VME IOC connected to the Timebus, mc1 is down")
for sys in data:
    ax1.plot(sys.times, sys.vals, ".",label=sys.name)
ax1.grid(True)
ax1.set_ylabel("Milliseconds")
plt.gcf().autofmt_xdate()
# ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5))
ax1.legend()
ax1.set_ylim([-5., 5.])
ax1.xaxis_date(TZ)
#pdb.set_trace()
plt.show()

print("Ciao ", datetime.now())
