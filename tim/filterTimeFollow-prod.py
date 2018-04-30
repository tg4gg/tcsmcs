#!/usr/bin/env python

# vim: ai:sw=4:sts=4:expandtab

###########################################################
#
#	Analyze clock synchronization
#

from collections import namedtuple
from datetime import datetime, timedelta
import argparse
import sys
import csv
import matplotlib.pyplot as plt
import numpy as np

import os
from pprint import pprint

TCS_SYSTEM = 'tcs'
TCS_CA = 'tcs:drives:driveMCS.VALA'
MCS_SYSTEM = 'mcs'
MCS_CA = 'mc:followA.J'

FollowArray = namedtuple('FollowArray', 'timestamp now targetTime trackId azPos elPos diff')


ERRTHRESHOLD_ARCSEC = 1.5
VELTHRESHOLD = 0.04
# Number of consecutive errors that make a significant event
# With high-resolution data, we have 10 measurements per second
SIGNIFICANT = 5

# Error threshold, in degrees
ERRTHRESHOLD = ERRTHRESHOLD_ARCSEC/3600.0

# We're looking for consecutive values past the threshold, allowing
# for small gaps. This value defines how large the gap can be
MAXGAP = 90*10

# When a high velocity event occurs the error will raise naturally
# so we want to ignore X seconds before and after this event
HVEL_PADDING = 10 

# Padding to be used for plotting
PLOT_PADDING = 5 # seconds

# Site should be either 'cp' or 'mk'
SITE = 'cp'
if SITE == 'cp':
    # directory where the data is located
    root_data_dir = '/archive/tcsmcs/data'
    if not os.path.exists(root_data_dir):
        root_data_dir = '/net/cpostonfs-nv1/tier2/gem/sto/archiveRTEMS/tcsmcs/data'
else:
    raise NotImplementedError("The script hasn't still been adapted for MK")

DEBUG = False

def parse_args():
    yesterday = (datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d")
    enableDebugDate = "debug"

    parser = argparse.ArgumentParser(description='Filter PMAC Error data')
    parser.add_argument('-sys',    '--system',           dest='system',            default='mcs', help='System to be analyzed: tcs, mcs or both')
    parser.add_argument('-date',    '--date',           dest='date',            default=enableDebugDate, help='Date - format YYYY-MM-DD')
    parser.add_argument('-day',   '--eng_mode',        dest='eng_mode',          action='store_true', help='If used daytime will be analyzed 6am-6pm')

    args = parser.parse_args()

    day_str = "day_" if args.eng_mode else ""
    system = MCS_SYSTEM
    PV = MCS_CA
    if args.system == 'tcs':
    	system = TCS_SYSTEM
    	PV = TCS_CA

    #Get directory name
    pvdir = PV[PV.find(':')+1:].replace(':','_')
    
    #Construct the path to the data    
    args.data_path = os.path.join(
            root_data_dir, SITE, system,
            pvdir, 
            'txt', 
            '{0}_{1}_{2}_{3}export.txt'.format(args.date, SITE, PV.replace(':','-'), day_str)
        )

    if args.system == 'both':
		#Construct the path to the TCS data
		system = TCS_SYSTEM
		PV = TCS_CA
		pvdir = PV[PV.find(':')+1:].replace(':','_')
		args.tcs_data_path = os.path.join(
            root_data_dir, SITE, system,
            pvdir, 
            'txt', 
            '{0}_{1}_{2}_{3}export.txt'.format(args.date, SITE, PV.replace(':','-'), day_str)
        )


    if (args.date == enableDebugDate):
    	print "DEBUG MODE ENABLED -\_(\")_/-"
        args.data_path = (
            args.data_path.replace(enableDebugDate, "2018-04-08")
                .replace(".txt", "_test.txt")
            )
    
      

    print "Reading: {0}".format(args.data_path)
    return args

"""
Timestamp
** Element 0  = time now
** Element 1  = target time
** Element 2  = track identifier
** Element 3  = demanded Azimuth
** Element 4  = demanded Elevation

"""
def producer(filename):
    with open(filename) as source:
        reader = csv.reader(source, delimiter='\t')
        # Skip the headers
        next(reader); next(reader); next(reader); next(reader)

        for row in reader:
            if row[0].startswith('#') or row[1].startswith('#'):
                continue
            generationTime = datetime.fromtimestamp(float(row[1]))
            receptionTime = datetime.strptime(row[0][:-3], '%m/%d/%Y %H:%M:%S.%f')
            targetTime = datetime.fromtimestamp(float(row[2]))
            yield FollowArray(receptionTime, generationTime,\
                 targetTime,  datetime.fromtimestamp(float(row[3])), float(row[4]), float(row[5]), targetTime-receptionTime \
                 )


args = parse_args()

# ---------- MAIN ----------

flw_producer = producer(args.data_path)


diff_lst = list()
for dp in flw_producer:
    #print dp.targetTime-dp.now
    diff_lst.append((dp.timestamp, dp.diff.total_seconds()))

diffTime,diffVal=zip(*diff_lst)

fig, ax1 = plt.subplots()   
plt.title("TCS-MCS Communication Analysis: {0} data from {1}\n Time before target time".format(args.system, args.date))
ax1.plot(diffTime, diffVal, "b.")
ax1.grid(True)
ax1.set_ylim([-0.05,0.05])
#ax1.set_yticks(np.arange(-0.05, 0.05, step=0.005))


if args.system == 'both':
	flw_producer2 = producer(args.tcs_data_path)

	diff_lst2 = list()
	for dp in flw_producer2:
		diff_lst2.append((dp.timestamp, dp.diff.total_seconds()))

	diffTime2,diffVal2=zip(*diff_lst2)	

	#ax2 = ax1.twinx()
	ax1.plot(diffTime2, diffVal2, "r.")
	plt.gca().legend((MCS_SYSTEM+' entry', TCS_SYSTEM+' exit'))

plt.gcf().autofmt_xdate()
plt.show()


