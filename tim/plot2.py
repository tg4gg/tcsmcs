import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt
import datetime as dt
import pandas as pd
import sys, os, fnmatch
import pickle

def returnold(folder):
    matches = []
    for root, dirnames, filenames in os.walk(folder):
        for filename in fnmatch.filter(filenames, '*.*'):
            matches.append(os.path.join(root, filename))
    return sorted(matches, key=os.path.getmtime)

def movingaverage(interval, window_size):
    window= np.ones(int(window_size))/float(window_size)
    return np.convolve(interval, window, 'same')


if (len(sys.argv) < 3):
    print  "Useage: python plot2.py <site> <system> <threshold>"
    print  "	    example: $python plot2.py MKO crcs"
    sys.exit()

site = sys.argv[1]
system = sys.argv[2]
threshold = float(sys.argv[3])

outpath = './'+system+'Png'+site
rawFilePath = './'+system+'binary'+site
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
	fig, ax1 = plt.subplots(figsize=(1920/my_dpi, 1200/my_dpi), dpi=my_dpi, facecolor='w', edgecolor='k')
	# the histogram of the data
	#n, bins, patches = ax.hist(tt1, num_bins)
	
	ax1.plot(mx_include,"b.", markersize=2)
	#plt.plot(tt2,"r")
	ax1.grid(True)
	ax1.set_title("%s %s Sample Rate Jitter\nRange %s " % (site, system, myrange) )
	ax1.set_xlabel("Sample Number")
	ax1.set_ylabel("Delta T (seconds)")
        ax1.set_ylim(0, threshold)
        ax1.tick_params('y', colors='b')
	
        ax2 = ax1.twinx()
	ax2.plot(mx_exclude,"r.", markersize=10)
	ax2.set_ylabel("Excluded Delta T values (seconds)", color='r')
        ax2.tick_params('y', colors='r')

	fig.tight_layout()
	fig.savefig(outfile, dpi=my_dpi)
        plt.close(fig)
        #sys.exit()

print "sorting dates..."

#Save data for Full Range historgram to pickle
df = pd.DataFrame({'dates':dates,
                   'counts':exclude_counts,
                   'r1counts':r1counts,
                   'r2counts':r2counts,
                   'r3counts':r3counts})
picklefile= "hist%s_%s_%s.pkl" % (site, system, threshold)
dfFile = open(picklefile, 'w')
pickle.dump(df, dfFile) 
print "done"



