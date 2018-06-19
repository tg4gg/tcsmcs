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

TCS_SYSTEM = 'tcs'
TCS_CA = 'tcs:drives:driveMCS.VALI'
MCS_SYSTEM = 'mcs'
# MCS_CA = 'mc:followA.J'
MCS_CA = 'mc:elPmacPosError'

FollowArray = namedtuple('FollowArray', 'timestamp traw dmdCnt corrCnt tick applyDT fltTime dtGetTelRD dtick tSuspFL azDmd elDmd dtraw')
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
    parser.add_argument('-cm',   '--ca_monitor',        dest='ca_mon',          action='store_true', help='use this option if you are analyzing data captured with camonitor')

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
        rwIdx = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        dl = '\t'
        if args.ca_mon:
            rwIdx = rwIdx + 3
            dl = ' '
        reader = csv.reader(source, delimiter=dl)
        # Skip the headers
        next(reader); next(reader); next(reader); next(reader)

        for row in reader:
            # print row
            # if row[0].startswith('#') or row[1].startswith('#') or re.search('[a-z]', row[1]) or re.search('[a-z]', row[4]):
            if row[0].startswith('#') or row[1].startswith('#'):
                continue
            if args.ca_mon:
                if re.search('[a-z]', row[1]) or re.search('[a-z]', row[4]):
                    continue
                # print row
                receptionTime = datetime.strptime(row[1]+' '+row[2], '%Y-%m-%d %H:%M:%S.%f')
            else:
                if float(row[1])==0:
                    continue
                receptionTime = datetime.strptime(row[0][:-3], '%m/%d/%Y %H:%M:%S.%f')
            # now = datetime.fromtimestamp(float(row[1]))
            #targetTime = datetime.fromtimestamp(float(row[2]))
            yield FollowArray(receptionTime, float(row[rwIdx[0]]),\
                              float(row[rwIdx[1]]), float(row[rwIdx[2]]), float(row[rwIdx[3]]),\
                              float(row[rwIdx[4]]), float(row[rwIdx[5]]), float(row[rwIdx[6]]),\
                              float(row[rwIdx[7]]), float(row[rwIdx[8]]), float(row[rwIdx[9]]),\
                              float(row[rwIdx[10]]), float(row[rwIdx[11]]))

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
vDmd_lst = list()
dmd_lst = list()
corr_lst = list()
flt_lst = list()
dmdC_lst = list()
applyDt_lst = list()
sendDt_lst = list()
dtfl_lst = list()



prevTraw = flw_producer.next().traw
prevTick = flw_producer.next().tick
prevElDmd = flw_producer.next().elDmd
prevCorrCnt = flw_producer.next().corrCnt
prevDmdCnt = flw_producer.next().dmdCnt
# prevFltCnt = flw_producer.next().fltCnt

outliersInPeriod = 0
periodLimits = Limits(-1,1)


for dp in flw_producer:
    # tBetweenDemands = (dp.traw-prevTraw).total_seconds()
    tBetweenDemands = dp.traw-prevTraw
    tBetweenTicks = dp.tick-prevTick
    dDemands = dp.elDmd - prevElDmd
    dCorrCnt = dp.corrCnt - prevCorrCnt
    dDmdCnt = dp.dmdCnt - prevDmdCnt
    # dFltCnt = dp.fltCnt - prevFltCnt

    # if dDmdCnt > 1 and ( dCorrCnt == 0  or dFltCnt == 0):
    if ( dDmdCnt > 1 ) and ( dCorrCnt == 0 ):
        dDemands = dDemands / 2
        tBetweenTicks = tBetweenTicks / 2
        tBetweenDemands = tBetweenDemands / 2

    diff_lst.append((dp.timestamp, dp.dtraw*1000.0))
    exec_lst.append((dp.timestamp, dp.dtick*1000.0))
    dDmd_lst.append((dp.timestamp, dDemands*3600))

    if tBetweenTicks > 0:
        vDemands = dDemands / tBetweenTicks
        vDmd_lst.append((dp.timestamp, vDemands*3600))

    applyDt_lst.append((dp.timestamp, dp.applyDT*1000.0))
    dtfl_lst.append((dp.timestamp, dp.fltTime*1000.0))
    corr_lst.append((dp.timestamp, dCorrCnt))
    dmdC_lst.append((dp.timestamp, dDmdCnt))
    dmd_lst.append((dp.timestamp, dp.elDmd*3600))

    prevTraw = dp.traw
    prevTick = dp.tick
    prevElDmd = dp.elDmd
    prevCorrCnt = dp.corrCnt
    prevDmdCnt = dp.dmdCnt

    # if(when<dp.timestamp):
        # if (tBetweenDemands > 1.0):
            # print "tBetweenDemands={0} at GEA time: {1}".format(tBetweenDemands, dp.timestamp)
        # else:
            # diff_lst.append((dp.timestamp, tBetweenDemands*1000.0))
        # exec_lst.append((dp.timestamp, dp.azPos*1000.0))
    # prevTraw = dp.now
    if tBetweenDemands > periodLimits.upper or tBetweenDemands < periodLimits.lower:
        print "Period out of limits: {0} on date: {1}".format(tBetweenDemands, dp.timestamp)
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

ax1 = plt.subplot2grid((10,2), (0,0), colspan = 1, rowspan = 2)
plt.title("TCS-MCS Communication Analysis: {0} data from {1}".format(args.system, args.date))
ax1.plot(diffTime, diffVal, "b.")
ax1.grid(True)
ax1.tick_params("y", colors="b")
ax1.set_ylabel("Diff traw\n[ms]", color="b")
ax1.set_ylim(-500, 1500)

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

# ax2 = plt.subplot(512, sharex=ax1)
ax2 = plt.subplot2grid((10,2), (2,0), colspan = 1, rowspan = 2, sharex=ax1 )
ax2.grid(True)
ax2.plot(execTime, execVal, "r.")
ax2.tick_params("y", colors="r")
ax2.set_ylabel("Diff Tick [ms]", color="r")
ax2.set_ylim(-500, 1500)

# Plot 3
# pmacTime, pmacVal=zip(*mcs_lst)

# ax4 = plt.subplot(413, sharex=ax1)
# ax4.grid(True)
# ax4.plot(pmacTime, pmacVal, "r-")
# ax4.tick_params("y", colors="r")
# ax4.set_ylabel("Elevation Pmac Error [arcsec]", color="r")
# ax4.set_ylim(-15, 15)

# adtTime, adt=zip(*applyDt_lst)

# # ax4 = plt.subplot(513, sharex=ax1)
# ax4 = plt.subplot2grid((10,2), (4,0), colspan = 1, rowspan = 2, sharex=ax1 )
# ax4.grid(True)
# ax4.plot(adtTime, adt, "r.-")
# ax4.tick_params("y", colors="r")
# ax4.set_ylabel("Tick - Traw\n[ms]", color="r")
# ax4.set_ylim(-100, 200)

flTime, dtFl=zip(*dtfl_lst)

# ax4 = plt.subplot(513, sharex=ax1)
ax4 = plt.subplot2grid((10,2), (4,0), colspan = 1, rowspan = 2, sharex=ax1 )
ax4.grid(True)
ax4.plot(flTime, dtFl, "r.-")
ax4.tick_params("y", colors="r")
ax4.set_ylabel("Fast Loop\nExec Time\n[ms]", color="r")
ax4.set_ylim(0, 5)

# Plot 4
corrTime, diffCorr=zip(*corr_lst)

# ax5 = plt.subplot(514, sharex=ax1)
ax5 = plt.subplot2grid((10,2), (6,0), colspan = 1, sharex=ax1 )
ax5.plot(corrTime, diffCorr, "g.-")
ax5.grid(True)
ax5.tick_params("y", colors="b")
ax5.set_ylabel("Diff\nCorr Cnt\n[un]", color="b")
ax5.set_ylim(-1, 3)

# Plot 5
dmdCTime, diffDmdC=zip(*dmdC_lst)

# ax6 = plt.subplot(514, sharex=ax1)
ax6 = plt.subplot2grid((10,2), (7,0), colspan = 1, sharex=ax1 )
ax6.plot(dmdCTime, diffDmdC, "r.-")
ax6.grid(True)
ax6.tick_params("y", colors="b")
ax6.set_ylabel("Diff\nDmd Cnt\n[un]", color="b")
ax6.set_ylim(0, 4)

# Plot 6
dmdTime, diffDmd=zip(*dDmd_lst)

# ax3 = plt.subplot(515, sharex=ax1)
ax3 = plt.subplot2grid((10,2), (8,0), colspan = 1, rowspan = 2, sharex=ax1 )
ax3.plot(dmdTime, diffDmd, "g-")
ax3.grid(True)
ax3.tick_params("y", colors="b")
ax3.set_ylabel("Diff EL Demand\n[arcsec]", color="b")
ax3.set_ylim(-10, 10)

# Plot 7
pmacTime, pmacVal=zip(*mcs_lst)

ax8 = plt.subplot2grid((10,2), (0,1), colspan = 1, rowspan = 2, sharex=ax1 )
ax8.plot(pmacTime, pmacVal, "r-")
ax8.grid(True)
ax8.tick_params("y", colors="r")
ax8.set_ylabel("Elevation\nPmac Error\n[arcsec]", color="r")
ax8.set_ylim(-15, 15)

# vdmdTime, vdmd=zip(*vDmd_lst)

# ax8 = plt.subplot2grid((10,2), (0,1), colspan = 1, rowspan = 2, sharex=ax1 )
# ax8.plot(vdmdTime, vdmd, "g.-")
# ax8.grid(True)
# ax8.tick_params("y", colors="b")
# ax8.set_ylabel("vel EL Demand\n[arcsec/sec]", color="b")
# ax8.set_ylim(-20, 20)

# Plot 8
dmdTime, dmd=zip(*dmd_lst)

# ax7 = plt.subplot(515, sharex=ax1)
ax7 = plt.subplot2grid((10,2), (2,1), colspan = 1, rowspan = 8, sharex=ax1 )
ax7.plot(dmdTime, dmd, "g.-")
ax7.grid(True)
ax7.tick_params("y", colors="b")
ax7.set_ylabel("EL Demand\n[arcsec]", color="b")
# ax7.set_ylim(-10, 10)

plt.setp(ax1.get_xticklabels(), fontsize=9, visible=False)
plt.setp(ax2.get_xticklabels(), fontsize=9, visible=False)
plt.setp(ax4.get_xticklabels(), fontsize=9, visible=False)
plt.setp(ax5.get_xticklabels(), fontsize=9, visible=False)
plt.setp(ax6.get_xticklabels(), fontsize=9, visible=False)
plt.setp(ax8.get_xticklabels(), fontsize=9, visible=False)
ax3.xaxis.set_major_locator(ticker.MaxNLocator(10))
ax3.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d/%m %H:%M:%S.%f"))
ax3.xaxis.set_minor_locator(ticker.MaxNLocator(200))
plt.setp(ax3.get_xticklabels(), fontsize=9, rotation=30, ha='right')
ax7.xaxis.set_major_locator(ticker.MaxNLocator(10))
ax7.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d/%m %H:%M:%S.%f"))
ax7.xaxis.set_minor_locator(ticker.MaxNLocator(200))
plt.setp(ax7.get_xticklabels(), fontsize=9, rotation=30, ha='right')


print "Number of detected period outliers: {0}".format(outliersInPeriod)

# plt.gcf().autofmt_xdate()
plt.show()


