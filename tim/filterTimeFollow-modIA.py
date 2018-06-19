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
import matplotlib.ticker as ticker
import matplotlib
import numpy as np
import re

import os
from pprint import pprint

sys.path.append('../')
from swglib.export import DataManager, get_exporter

TCS_SYSTEM = 'tcs'
TCS_CA = 'tcs:drives:driveMCS.VALA'
MCS_SYSTEM = 'mcs'
# MCS_CA = 'mc:followA.J'
MCS_CA = 'mc:elPmacPosError'

FollowArray = namedtuple('FollowArray', 'timestamp now targetTime trackId azPos elPos diff')
MCSArray = namedtuple('MCSArray', 'timestamp pmacError')
Limits = namedtuple('Limits', 'lower upper')


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
    args.tcs_data_path = os.path.join(
            root_data_dir, SITE, system,
            pvdir,
            'txt',
            '{0}_{1}_{2}_{3}export.txt'.format(args.date, SITE, PV.replace(':','-'), day_str)
        )

    if args.system == 'both':
        system = MCS_SYSTEM
        PV = MCS_CA
        pvdir = PV[PV.find(':')+1:].replace(':','_')
        args.mcs_data_path = os.path.join(
            root_data_dir, SITE, system,
            pvdir,
            'txt',
            '{0}_{1}_{2}_{3}export.txt'.format(args.date, SITE, PV.replace(':','-'), day_str)
        )
        system = TCS_SYSTEM
        PV = TCS_CA
        pvdir = PV[PV.find(':')+1:].replace(':','_')
        args.tcs_data_path = os.path.join(root_data_dir, SITE, system, pvdir, 'txt', '{0}_{1}_{2}_{3}export.txt'.format(args.date, SITE, PV.replace(':','-'), day_str))


    if (args.date == enableDebugDate):
    	print "DEBUG MODE ENABLED -\_(\")_/-"
        args.data_path = (
            args.data_path.replace(enableDebugDate, "2018-04-08")
                .replace(".txt", "_test.txt")
            )



    print "Reading: {0}".format(args.tcs_data_path)
    if args.system == 'both':
        print "Reading: {0}".format(args.mcs_data_path)
    return args

"""
Timestamp
** Element 0  = time now
** Element 1  = target time
** Element 2  = track identifier
** Element 3  = demanded Azimuth
** Element 4  = demanded Elevation

"""
def producerTCS(filename):
    with open(filename) as source:
        reader = csv.reader(source, delimiter='\t')
        # Skip the headers
        next(reader); next(reader); next(reader); next(reader)

        for row in reader:
            if row[0].startswith('#') or row[1].startswith('#'):
                continue
            receptionTime = datetime.strptime(row[0][:-3], '%m/%d/%Y %H:%M:%S.%f')
            # now = datetime.fromtimestamp(float(row[1]))
            now = float(row[1])
            #targetTime = datetime.fromtimestamp(float(row[2]))
            yield FollowArray(receptionTime, now,\
                 float(row[2]),  float(row[3]), float(row[4]), float(row[5]), 0.0)


def producerMCS(filename):
    with open(filename) as source:
        reader = csv.reader(source, delimiter='\t')
        # Skip the headers
        next(reader); next(reader); next(reader); next(reader)

        for row in reader:
            if row[0].startswith('#') or row[1].startswith('#'):
                continue
            yield MCSArray(datetime.strptime(row[0][:-3], '%m/%d/%Y %H:%M:%S.%f'), float(row[1]))

args = parse_args()

# ---------- MAIN ----------

flw_producer = producerTCS(args.tcs_data_path)


diff_lst = list()
exec_lst = list()
dDmd_lst = list()
prevTimestamp = flw_producer.next().now
prevTarget = flw_producer.next().targetTime
prevElPos = flw_producer.next().elPos
outliersInPeriod = 0
periodLimits = Limits(-1,1)

#FollowArray = namedtuple('FollowArray', 'timestamp now targetTime trackId azPos elPos diff')
# when = datetime.strptime("2018-04-26 11:18", "%Y-%m-%d %H:%M")

for dp in flw_producer:
    #print dp.targetTime-dp.now
    #print dp.diff.total_seconds()
    # tBetweenSamples = (dp.now-prevTimestamp).total_seconds()
    tBetweenSamples = dp.now-prevTimestamp
    # tBetweenTargets = dp.targetTime-prevTarget
    tBetweenTargets = dp.targetTime - dp.now
    dDemands = dp.elPos - prevElPos
    diff_lst.append((dp.timestamp, tBetweenSamples*1000.0))
    exec_lst.append((dp.timestamp, tBetweenTargets*1000.0))
    dDmd_lst.append((dp.timestamp, dDemands*3600))
    prevTimestamp = dp.now
    prevTarget = dp.targetTime
    prevElPos = dp.elPos
    # if(when<dp.timestamp):
        # if (tBetweenSamples > 1.0):
            # print "tBetweenSamples={0} at GEA time: {1}".format(tBetweenSamples, dp.timestamp)
        # else:
            # diff_lst.append((dp.timestamp, tBetweenSamples*1000.0))
        # exec_lst.append((dp.timestamp, dp.azPos*1000.0))
    # prevTimestamp = dp.now
    if tBetweenSamples > periodLimits.upper or tBetweenSamples < periodLimits.lower:
        print "Period out of limits: {0} on date: {1}".format(tBetweenSamples, dp.timestamp)
        outliersInPeriod += 1


print "Last read line with date:", dp.timestamp


if args.system=='both':
    mcs_lst = list()
    mcs_producer = producerMCS(args.mcs_data_path)
    for dp in mcs_producer:
        mcs_lst.append((dp.timestamp, dp.pmacError*3600))

# PLOTTING SECTION
# Plot 1
diffTime,diffVal=zip(*diff_lst)

ax1 = plt.subplot(411)
plt.title("TCS-MCS Communication Analysis: {0} data from {1}".format(args.system, args.date))
ax1.plot(diffTime, diffVal, "b.")
ax1.grid(True)
ax1.tick_params("y", colors="b")
ax1.set_ylabel("Diff timeNow [ms]", color="b")
ax1.set_ylim(-200, 500)

if outliersInPeriod > 0:
    #ax1.set_ylim(*periodLimits)
    print "Fixed scaling due to outliers"
else:
    print "Rescaling Period axis due to no outliers in sample set"
#ax1.set_yticks(np.arange(-0.05, 0.05, step=0.005))
when = datetime.strptime("2018-04-18 09:45", "%Y-%m-%d %H:%M")
#ax1.axvspan(when, when+timedelta(minutes=230), facecolor='0.2', alpha=0.3)

# Plot 2
execTime, execVal=zip(*exec_lst)

ax2 = plt.subplot(412, sharex=ax1)
ax2.grid(True)
ax2.plot(execTime, execVal, "r.")
ax2.tick_params("y", colors="r")
ax2.set_ylabel("Tick - tnow [ms]", color="r")
ax2.set_ylim(-10, 60)

# Plot 3
pmacTime, pmacVal=zip(*mcs_lst)

ax4 = plt.subplot(413, sharex=ax1)
ax4.grid(True)
ax4.plot(pmacTime, pmacVal, "r-")
ax4.tick_params("y", colors="r")
ax4.set_ylabel("Elevation Pmac Error [arcsec]", color="r")
ax4.set_ylim(-15, 15)

# Plot 4
dmdTime, diffDmd=zip(*dDmd_lst)

ax3 = plt.subplot(414, sharex=ax1)
ax3.plot(dmdTime, diffDmd, "g.-")
ax3.grid(True)
ax3.tick_params("y", colors="b")
ax3.set_ylabel("Diff EL Demand [arcsec]", color="b")
ax3.set_ylim(-10, 10)

plt.setp(ax1.get_xticklabels(), fontsize=9, visible=False)
plt.setp(ax2.get_xticklabels(), fontsize=9, visible=False)
plt.setp(ax4.get_xticklabels(), fontsize=9, visible=False)
ax3.xaxis.set_major_locator(ticker.MaxNLocator(10))
ax3.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d/%m %H:%M:%S.%f"))
ax3.xaxis.set_minor_locator(ticker.MaxNLocator(200))
plt.setp(ax3.get_xticklabels(), fontsize=9, rotation=20, ha='right')

print "Number of detected period outliers: {0}".format(outliersInPeriod)

# plt.gcf().autofmt_xdate()
plt.show()


