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
import numpy as np
import os

SITE = 'CP'
RETRIEVE_RMS = False
TOP = 'ta:'
start_date = datetime(2020, 5, 12, 9, 0)
#start_date = datetime(2020, 4, 24, 23, 44, 0)
#start_date = datetime(2020, 4, 20, 7, 10)
end_date = datetime(2020, 4, 24, 23, 44, 30)
end_date = datetime(2020, 5, 12, 12, 55)

TITLE_SUFFIX = "\nTotal data set length: " + start_date.strftime("%Y.%m.%d-%H:%M:%S") + \
               '->' + end_date.strftime("%Y.%m.%d-%H:%M:%S")

SystemData = namedtuple('SystemData', 'name times vals')

if SITE == 'CP':  # Archiver returns UTC dates, need to cover for that
    UTC_OFFSET = timedelta(hours=4)
    TZ = 'America/Santiago'
    DB = 'sbflab'
    TITLE_PREFIX = 'SBF Lab: '
    systems = ['ta', 'mc1', ]
    # systems = [ 'ta', 'mc1', 'ta3', 'ta4']
    # systems = ['tc1', 'ta3', ]
    # systems = ['tc1', 'ta2', 'ta4']


if SITE == 'MK':
    UTC_OFFSET = timedelta(hours=10)
    TZ = 'Pacific/Honolulu'
    DB = 'temporary'
    TITLE_PREFIX = 'MKO Telescope: '
    systems = ['tcs', 'mc', 'ta', 'm2', 'ag']
    systems = ['mc', 'ta', 'm2', 'cr',]
    systems = ['mc','ta', 'ag']

def retrieveChannels(systems):
    """ Gets the channel names to be plotted based on: TOP, systems and RETRIEVE_RMS"""
    chans = []
    for sys in systems:
        chans.append(TOP+sys+":diff")
        if RETRIEVE_RMS:
            chans.append(TOP+sys+":rmsErr.VALJ")
    return chans
# chans = [ TOP+sys+":diff" for sys in systems ]

def fromCache(pvname, start, end, db):
    """ If query is cached retrieve it directly from disk """
    TMP_DIR = '/tmp/rcm2/'
    path = TMP_DIR + pvname + "/" + SITE + "/" + start.strftime("%Y%m%d-%H%M%S") + "/"
    fn = path + end.strftime("%Y%m%d-%H%M%S") + ".npy"
    if os.path.exists(fn):  # Return from cache
        return np.load(fn, allow_pickle=True)

    else:  # Retrieve data and cache it for next query
        dm = DataManager(get_exporter(SITE), root_dir='/tmp/rcm')
        sys_data = list(dm.getData(pvname, start=start, end=end, db=db))
        start = datetime.now()
        os.makedirs(path, exist_ok=True)
        np.save(fn, np.array(sys_data))
        print("Time invested in saving pickle:", datetime.now() - start)
        return sys_data


def retrieveAllData():
    """" Gets the data for each system and returns an easy to plot list"""
    ret = list()
    chans = retrieveChannels(systems)
    for chan in chans:
        start = datetime.now()
        print(start, '\nRetrieving values for:' + chan)
        chan_data = fromCache(chan, start=start_date + UTC_OFFSET, end=end_date + UTC_OFFSET, db=DB)
        print(('Retrieved {0} values for {1} elapsed time {2} speed: {3:.3f} ms./sample').format(
            len(chan_data), chan, datetime.now() - start, (datetime.now() - start).total_seconds() * 1000. / len(
                                                                                                     chan_data)))
        data_unzip = list(zip(*chan_data))  # data[0] is (datetime, val)
        if len(data_unzip) > 0:
            chan_data = SystemData(chan, data_unzip[0], [x * 1000.0 for x in data_unzip[1]])  # convert to milliseconds
            # periodicity = [abs((chan_data.vals[i+1]-chan_data.vals[i])) for i in range(len(chan_data.vals)-1)]
            # [if period  for period in periodicity]
            # pdb.set_trace()
            print("Max val:", max(chan_data.vals), " Min val:", min(chan_data.vals))
            ret.append(chan_data)
        else:
            print("No data found for {0} in the specified period.".format(sys))  # TODO: Warning
    return ret


data = retrieveAllData()

fig, ax1 = plt.subplots()
plt.title(TITLE_PREFIX + "Time differences, generated at: {}".format(datetime.now()) + TITLE_SUFFIX)

color_id, color = -1, 'C0.'
for sd in data:
    # With this plotting technique we are requiring a specific order for the input
    if not "rmsErr" in sd.name:
        color_id += 1
        color = 'C' + str(color_id) + "."
        #alpha = 0.2
    else:  # RMS will be plotted as lines
        color = 'C' + str(color_id) + "-"
        #alpha = 1.0

    ax1.plot(sd.times, sd.vals, color, label=sd.name)

ax1.grid(True)
ax1.set_ylabel("Milliseconds")
plt.gcf().autofmt_xdate()
# ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5))
ax1.legend()
ax1.set_ylim([-5., 5.])
ax1.xaxis_date(TZ)
# pdb.set_trace()
plt.show()

print("Ciao ", datetime.now())
