import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
import pandas as pd
import sys, os, fnmatch
import pickle

def returnold(folder):
    matches = []
    for root, dirnames, filenames in os.walk(folder):
        for filename in fnmatch.filter(filenames, '*.txt'):
            matches.append(os.path.join(root, filename))
    return sorted(matches, key=os.path.getmtime)

if (len(sys.argv) < 2):
    print  "Useage: python procRaw.py <site> <system>"
    print  "	    example: $python procRaw.py MKO crcs"
    sys.exit()

site = sys.argv[1]
system = sys.argv[2]
rawFilePath = './'+system+'Data'+site
binoutpath = './'+system+'binary'+site

print "Looking for RAW Data inside %s." % rawFilePath

dateconv = lambda x: dt.datetime.strptime(x,'%m/%d/%Y %H:%M:%S:.%f')
col_names = ["Timestamp", "data1"]
dtypes = ["object", "float"]

for f in returnold(rawFilePath):
    tsFilename = "%s/%s%s" % (binoutpath, os.path.basename(f), '.pkl')
    # Has pickle file been processed inside the binary folder yet?
    if os.path.isfile(tsFilename):
        print "Will BYPASS %s..." % (f)
        continue
    else:
        print "Will process %s..." % (f)
        try:
            mydata = np.genfromtxt(f, delimiter='\t',names=col_names, dtype=dtypes, converters={"Time": dateconv})
            myrange = "%s to %s" % (mydata['Timestamp'][0], mydata['Timestamp'][mydata.size-1] )
            print mydata['Timestamp']
            print 'Processing %d lines for Range %s' % (mydata.size, myrange)
            ts = pd.to_datetime(mydata['Timestamp'])
            print ts
            tsFile = open(tsFilename, 'w')
            print "Saving %s to disk." % tsFilename
            pickle.dump(ts, tsFile)
            print "done"
        except ValueError:
            print "Could not convert data proper format."
        #sys.exit()

print "done."
