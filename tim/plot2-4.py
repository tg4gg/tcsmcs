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

	pdb.set_trace()
	return mydata['values']


if (len(sys.argv) < 2):
    print  "Useage: python plot2.2.py <threshold>"
    print  "	    example: $python plot2.2.py 0.5"
    sys.exit()

system = 'mcs'
site = 'CPO'
threshold = float(sys.argv[1])

outpath = './png/azDemandPos/'
rawFilePath = './binary/azDemandPos/'
print "Looking for pickles inside %s." % rawFilePath
dates = []
exclude_counts = []
r1counts = []
r2counts = []
r3counts = []

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
	#tt2 = movingaverage(tt1, 2)

        #Basic stats on our data
        mu = np.mean(tt1)
        sigma = np.std(tt1)

        print "Dataset %s has:\n\t%d samples\n\tmean %f\n\tstd %f" % (f, len(tt1), mu, sigma)

        #3-Sigma Rule 68, 95, and 99.7
        s1Left = (mu - sigma)
        s1Right = (mu + sigma)
        s2Left = (mu - 2*sigma)
        s2Right = (mu + 2*sigma)
        s3Left = (mu - 3*sigma)
        s3Right = (mu + 3*sigma)

        # The masks apply to ranges you don't want, they're MASKED!
        #   the result is an array with the values you do want
        #
        # Include points not exceeding the input threshold
        mx_include = ma.masked_array(tt1, mask = (tt1 > threshold))

        # Exclude points that exceed the input threshold
        mx_exclude = ma.masked_array(tt1, mask = (tt1 < threshold))
        exclude_counts.append(mx_exclude.count())
        print len(tt1)
        
        r1counts.append( len([ i for i in tt1 if ( (s1Left <= i)  & (i <= s1Right)) ] ) )
        r2counts.append( len([ i for i in tt1 if ( ((s1Left >= i)  & (s2Left <= i)) | ((i >= s1Right) & (i <= s2Right)))] ) )
        r3counts.append( len([ i for i in tt1 if ( ((s2Left >= i)  & (s3Left <= i)) | ((i >= s2Right) & (i <= s3Right)))] ) )

        
        #range1 = ma.masked_array(tt1, mask = (s1Left >= tt1) | (tt1 >= s1Right)& 
        #                                     (s2Left <= tt1) | (tt1 <= s2Right) )# ~0.6827 #Strictly in the -1sigma and +1sigma band

        #range2 = ma.masked_array(tt1, mask = (s2Left >= tt1) & (tt1 >= s2Right) &
        #                                     (s3Left <= tt1) & (tt1 <= s3Right) )# ~0.9545 #Strictly in the -2sigma and +2sigma band

        #range3 = ma.masked_array(tt1, mask = (s3Left >= tt1) & (tt1 >= s3Right) &
        #                                     (0.0 <= tt1) & (tt1 <= float('inf')) )# ~0.9973

	print '\tExtreme counts greater than %f = %d\n\tR1C=%d, R2C=%d, R3C=%d' % (threshold, mx_exclude.count(), 
                                                                                   r1counts[-1], r2counts[-1], r3counts[-1] )
	num_bins = 100
        my_dpi=96

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



