#! /usr/bin/python
"""
Print time differences
Known errors: When Archiver is down/restarted ArchiveExport reports 2 false zeros with the same time stamps as
              the last record
  -sys SYSTEMS [SYSTEMS ...], --systems SYSTEMS [SYSTEMS ...]
                        The systems to be analyzed eg: tc1 ta mc1
  -s STARTDATE, --startdate STARTDATE
                        The Start Date - format YYYYMMDD-HHmm
  -e ENDDATE, --enddate ENDDATE
                        The End Date - format YYYYMMDD-HHmm
  -si SITE, --site SITE
                        The site: MKO, CPO, HBF or SBF
  -r, --rms             Plot also RMS errors
  -y YLIMS [YLIMS ...], --ylims YLIMS [YLIMS ...]
                        The plot Y limits: bottom top
  -l, --lines           Plot with lines instead of dots
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
import argparse


SystemData = namedtuple('SystemData', 'name times vals')


def valid_date(s):
    try:
        return datetime.strptime(s, "%Y%m%d-%H%M")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


def parseArgs():
    """ Parses cmd line arguments """
    parser = argparse.ArgumentParser(description='Plot time differences')

    parser.add_argument('-sys','--systems', nargs='+',
                        help='The systems to be analyzed eg: tc1 ta mc1', required=True)

    parser.add_argument("-s",
                        "--startdate",
                        help="The Start Date - format YYYYMMDD-HHmm",
                        required=True,
                        type=valid_date)
    parser.add_argument("-e",
                        "--enddate",
                        help="The End Date - format YYYYMMDD-HHmm",
                        required=True,
                        type=valid_date)

    parser.add_argument('-si','--site',
                        help='The site: MKO, CPO, HBF or SBF', required=True)

    parser.add_argument('-r','--rms', action="store_true",
                        help='Plot also RMS errors')

    parser.add_argument('-y', '--ylims', nargs='+',
                        help='The plot Y limits: bottom top', type=float)

    parser.add_argument('-l','--lines', action="store_true",
                        help='Plot with lines instead of dots')

    return parser.parse_args()


def retrieveChannels(systems):
    """ Gets the channel names to be plotted based on: TOP, systems and args.rms"""
    chans = []
    for sys in systems:
        chans.append(TOP+sys+":diff")
        if args.rms:
            chans.append(TOP+sys+":rmsErr.VALJ")
    return chans
# chans = [ TOP+sys+":diff" for sys in systems ]


def fromCache(pvname, start, end, db):
    """ If query is cached retrieve it directly from disk """
    TMP_DIR = '/tmp/rcm2/'
    path = TMP_DIR + pvname + "/" + args.site + "/" + start.strftime("%Y%m%d-%H%M%S") + "/"
    fn = path + end.strftime("%Y%m%d-%H%M%S") + ".npy"
    if os.path.exists(fn):  # Return from cache
        return np.load(fn, allow_pickle=True)

    else:  # Retrieve data and cache it for next query
        dm = DataManager(get_exporter(args.exporter), root_dir='/tmp/rcm')
        sys_data = list(dm.getData(pvname, start=start, end=end, db=db))
        start = datetime.now()
        os.makedirs(path, exist_ok=True)
        np.save(fn, np.array(sys_data))
        print("Time invested in saving pickle:", datetime.now() - start)
        return sys_data


def retrieveAllData():
    """" Gets the data for each system and returns an easy to plot list"""
    ret = list()
    chans = retrieveChannels(args.systems)
    for chan in chans:
        start = datetime.now()
        print(start, '\nRetrieving values for: ' + chan)
        chan_data = fromCache(chan, start=args.startdate + UTC_OFFSET, end=args.enddate + UTC_OFFSET, db=DB)
        print('Retrieved {0} values for {1} elapsed time {2} speed: {3:.3f} ms./sample'.format(
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
            print("No data found for {0} in the specified period.".format(sys))  # TODO: Send warning

    return ret


# --------------- MAIN ------------------

TOP = 'ta:'

args = parseArgs()

# Site specific adjustments
if args.site == 'SBF':  # Archiver returns UTC dates, need to cover for that
    UTC_OFFSET = timedelta(hours=4)
    TZ = 'America/Santiago'
    DB = 'sbflab'
    TITLE_PREFIX = 'SBF Lab: '
    args.exporter = 'CP'
    # systems = [ 'ta', 'mc1', 'ta3', 'ta4']

if args.site == 'MKO':
    UTC_OFFSET = timedelta(hours=10)
    TZ = 'Pacific/Honolulu'
    DB = 'temporary'
    TITLE_PREFIX = 'MKO Telescope: '
    args.exporter = 'MK'
    # systems = ['tcs', 'mc', 'ta', 'm2', 'ag']

# Core function
data = retrieveAllData()

# Now format and plot
fig, ax1 = plt.subplots()
TITLE_SUFFIX = "\nTotal data set length: " + args.startdate.strftime("%Y.%m.%d-%H:%M:%S") + \
               '->' + args.enddate.strftime("%Y.%m.%d-%H:%M:%S")
plt.title(TITLE_PREFIX + "Time differences, generated at: {}".format(datetime.now()) + TITLE_SUFFIX)

# Plotted data and its corresponding RMS will use the same color
color_id, color = -1, 'C0.'
for sd in data:
    # With this plotting technique we are requiring a specific order for the input
    if not "rmsErr" in sd.name:
        color_id += 1
        color = 'C' + str(color_id) + "-" if args.lines else "."
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
if args.ylims:
    ax1.set_ylim(args.ylims)
ax1.xaxis_date(TZ)
# pdb.set_trace()
plt.show()

print("Ciao ", datetime.now())
