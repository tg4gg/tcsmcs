"""
Hardcoded path for testing
and plots also the following error
Should respect timestamps
"""

import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt
import datetime as dt
import pandas as pd
import sys, os, fnmatch
import pickle
from mpl_toolkits.axes_grid1 import host_subplot
import mpl_toolkits.axisartist as AA
import pdb


def returnold(folder):
    matches = []
    for root, dirnames, filenames in os.walk(folder):
        for filename in fnmatch.filter(filenames, '*.*'):
            matches.append(os.path.join(root, filename))
    #return sorted(matches, key=os.path.getmtime)[-3:]
    return sorted(matches, key=os.path.getmtime)[-1:]

def movingaverage(interval, window_size):
    window= np.ones(int(window_size))/float(window_size)
    return np.convolve(interval, window, 'same')

def getFE():
	print "///////////////////////////////////"
	f2 = f.replace(".pkl","").replace("binary/azDemandPos", "data/azPmacPosError")
	dateconv = lambda x: dt.datetime.strptime(x,'%m/%d/%Y %H:%M:%S:.%f')
	scaleconv = lambda x: x*3600
	col_names = ["timestamp", "values"]
	dtypes = ["object", "float"]
	mydata = np.genfromtxt(f2, delimiter='\t',names=col_names, dtype=dtypes, converters={"Time": dateconv, "values": scaleconv , })
	myrange = "%s to %s" % (mydata['timestamp'][0], mydata['timestamp'][mydata.size-1] )

	print "Following error range:", myrange

#	pdb.set_trace()
	return mydata['values']


system = 'mcs'
site = 'CPO'
threshold = float(sys.argv[1])

outpath = './png/azDemandPos/'
rawFilePath = './binary/azDemandPos/'
print "Looking for pickles inside %s." % rawFilePath
dates = []

for f in returnold(rawFilePath):
	
    outfile = "%s/%s%s" % (outpath, os.path.splitext(os.path.basename(f))[0], '.png')
    # Has pickle file been processed inside the binary folder yet?
    if os.path.isfile(outfile):
        print "Will BYPASS %s..." % (f)
        continue
    else:
        ts = pd.read_pickle(open(f, 'r'))
        #print ts
        #myrange = "%s to %s" % (mydata['Timestamp'][0], mydata['Timestamp'][mydata.size-1] )
        myrange = "%s to %s" % (ts[0], ts[ts.size-1])
        dates.append(ts[0].date())
	diffs = np.diff(ts)
	tt1 = diffs / np.timedelta64(1, 's')

        #Basic stats on our data
        mu = np.mean(tt1)
        sigma = np.std(tt1)

        print "Dataset %s has:\n\t%d samples\n\tmean %f\n\tstd %f" % (f, len(tt1), mu, sigma)

    followingError = getFE()

    host = host_subplot(111, axes_class=AA.Axes)
    plt.subplots_adjust(right=0.75)
    # the histogram of the data
    #n, bins, patches = ax.hist(tt1, num_bins)
    host.plot(mx_include,"b.", markersize=2)
    #plt.plot(tt2,"r")
    host.grid(True)
    host.set_title("%s %s Sample Rate Jitter\nRange %s " % (site, system, myrange) )
    host.set_xlabel("Sample Number")
    host.set_ylabel("Delta T (seconds)")
    host.set_ylim(0, threshold)
    host.tick_params('y', colors='b')

    ax2 = host.twinx()
    ax2.plot(mx_exclude,"r.", markersize=10)
    ax2.set_ylabel("Excluded Delta T values (seconds)", color='r')
    ax2.tick_params('y', colors='r')

    ax3 = host.twinx()
    ax3.plot(followingError,"g.", markersize=2)
    ax3.set_ylabel("Following error (arcseconds)", color='g')
    ax3.tick_params('y', colors='g')

    #align 3rd axis
    offset = 60
    new_fixed_axis = ax3.get_grid_helper().new_fixed_axis
    ax3.axis["right"] = new_fixed_axis(loc="right", axes=ax3,
                                        offset=(offset, 0))
    ax3.axis["right"].toggle(all=True)
    ax3.set_ylim(-5, 5)

    #fig.tight_layout()
    #fig.savefig(outfile, dpi=my_dpi)
    plt.show()
    #plt.close(fig)
    #sys.exit()


print "done"



