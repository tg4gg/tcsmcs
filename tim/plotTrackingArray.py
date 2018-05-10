#!/usr/bin/env python

# vim: ai:sw=4:sts=4:expandtab

###########################################################
#
#    Analyze clock synchronization
#

from collections import namedtuple
from datetime import datetime, timedelta
from dateutil import tz
import pytz
import argparse
import sys
import csv
import matplotlib.pyplot as plt
import numpy as np
import pdb

import os

LEGEND_LOCATION = 'lower left'
TZ = 'America/Santiago'
PLOT_ZONE_FILE = './zones.cfg'
MARKERSIZE = 0.5


TCS_SYSTEM = 'tcs'
TCS_CA = 'tcs:drives:driveMCS.VALA'
MCS_SYSTEM = 'mcs'
MCS_CA = 'mc:followA.J'

# Modes
EXEC_TIME_MODE = 'execTime'
POS_DIFF_MODE = 'posDiff' #shortcut for rawDiff -cols 4,5
PERIOD_MODE = 'period'
RAW_MODE = 'raw'

FollowArray = namedtuple('FollowArray', 'timestamp now targetTime trackId azPos elPos diff')
ZoneArray = namedtuple('ZoneArray', 'title begin end color')
Limits = namedtuple('Limits', 'lower upper')


# Site should be either 'cp' or 'mk'
SITE = 'cp'
if SITE == 'cp':
    # directory where the data is located
    root_data_dir = '/archive/tcsmcs/data'
    if not os.path.exists(root_data_dir):
        root_data_dir = '/net/cpostonfs-nv1/tier2/gem/sto/archiveRTEMS/tcsmcs/data'
else:
    raise NotImplementedError("The script hasn't still been adapted for MK")

timezone = pytz.timezone(TZ)

DEBUG = False

def parse_args():
    yesterday = (datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d")
    enableDebugDate = "debug"

    parser = argparse.ArgumentParser(description='Filter PMAC Error data')
    parser.add_argument('-sys',    '--system',           dest='system',            default='tcs', help='System to be analyzed: tcs, mcs or both')
    parser.add_argument('-date',    '--date',           dest='date',            default=enableDebugDate, help='Date - format YYYY-MM-DD')
    parser.add_argument('-day',   '--eng_mode',        dest='eng_mode',          action='store_true', help='If used daytime will be analyzed 6am-6pm')
    parser.add_argument('-mode',   '--plot_mode',               dest='mode',          default=EXEC_TIME_MODE,
                        help='Different ways of representing the data, could be: {0}, {1} or {2}'.format(EXEC_TIME_MODE, POS_DIFF_MODE, PERIOD_MODE))

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


def fromtimestampTz(ts):
    return datetime.fromtimestamp(ts, timezone)

def strptimeTz(dateStr, US=False):
    if US:
        when = datetime.strptime(dateStr, '%m/%d/%Y %H:%M:%S.%f')
    else:
        when = datetime.strptime(dateStr, '%Y-%m-%d %H:%M:%S')
    return timezone.localize(when)

"""
If part of the zone is inside the range adjust limits
if its not inside the plotted range None is returned
"""
def insideRange(begin, end, zone):
    if begin > zone.end or end < zone.begin:
        return None
    
    retZone = ZoneArray(zone.title, zone.begin, zone.end, zone.color)
    if zone.begin < begin:
        retZone = retZone._replace(begin=begin)
    if zone.end > end:
        retZone = retZone._replace(end=end)
        
    return retZone
    


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
            generationTime = fromtimestampTz(float(row[1]))
            receptionTime = strptimeTz(row[0][:-3], True)
            targetTime = fromtimestampTz(float(row[2]))
            yield FollowArray(receptionTime, generationTime,\
                 targetTime,  fromtimestampTz(float(row[3])), float(row[4]), float(row[5]), targetTime-receptionTime \
                 )

def readZonesFromFile(begin, end):
    markedZones = []
    try:
        with open(PLOT_ZONE_FILE) as source:
            reader = csv.reader(source, skipinitialspace=True)
            for row in reader:
                if len(row)>3:
                    za = ZoneArray(row[0].strip(), strptimeTz(row[1].strip()), strptimeTz(row[2].strip()), row[3].strip())  
                    za = insideRange(begin, end, za)
                    if za:
                        markedZones.append(za)
    except Exception as ex:
        print "Exception reading zones file:"
        print ex
        pass
    return markedZones

def addZones(ax, begin, end):
    markedZones = readZonesFromFile(begin, end)    
    
    for ii, za in enumerate(markedZones):
        ax.axvspan(za.begin, za.end, facecolor=za.color, label=za.title, alpha=0.3)
    
    ax.legend(loc=LEGEND_LOCATION)
    
def plotPeriod():
    """
    Here we are measuring periodicity between executions
    and periodicity (or duration) between consecutive targetTime calculations
    """
    flw_producer = producer(args.data_path)
    
    first = flw_producer.next()
    diffNow_lst, diffTarget_lst = list(), list()
    prevNowT, prevTargetT = first.now, first.targetTime
    outliersInPeriod = 0
    periodLimits = Limits(-1,1)
    
    when = strptimeTz("2017-04-26 11:18:00")#TODO implement this as a argument
    
    for dp in flw_producer:
        tBetweenExecutions = (dp.now-prevNowT).total_seconds()
        tBetweenTargets = (dp.targetTime-prevTargetT).total_seconds()
        if(when<dp.timestamp):
            if tBetweenExecutions > periodLimits.upper or tBetweenExecutions < periodLimits.lower:
                print "tBetweenExecutions={0} tBetweenTargets={1} at GEA time: {2}".format(
                        tBetweenExecutions, tBetweenTargets, dp.timestamp)
                outliersInPeriod += 1
            else:
                diffNow_lst.append((dp.timestamp, tBetweenExecutions*1000.0))
                diffTarget_lst.append((dp.timestamp, tBetweenTargets*1000.0))
        prevNowT, prevTargetT = dp.now, dp.targetTime
         
    print "Last read line with date:", dp.timestamp
    periodTime,periodVal=zip(*diffNow_lst)
    
    fig, ax1 = plt.subplots()   
    plt.title("TCS-MCS Communication Analysis: {0} data from {1}".format(args.system, args.date))
    ax1.plot(periodTime, periodVal, "b.", markersize=MARKERSIZE)
    ax1.grid(True)
    ax1.tick_params("y", colors="b")
    ax1.set_ylabel("timeNow - previous timeNow (milliseconds)", color="b")
    
    #if outliersInPeriod > 0:
        #ax1.set_ylim(*periodLimits)
    #    print "Fixed scaling due to outliers"
    #else:
    #print "Rescaling Period axis due to no outliers in sample set"
    #ax1.set_yticks(np.arange(-0.05, 0.05, step=0.005))
    #ax1.axvspan(when, when+timedelta(minutes=230), facecolor='0.2', alpha=0.3)    
    
    if True: #Plot also diffs in target time
        targetTime, targetVal=zip(*diffTarget_lst)
    
        ax2 = ax1.twinx()
        ax2.plot(targetTime, targetVal, "r.", markersize=MARKERSIZE)
        ax2.tick_params("y", colors="r")
        ax2.set_ylabel("targetTime - previous targetTime (milliseconds)", color="r")
    
    print "Number of detected period outliers: {0}".format(outliersInPeriod)
    
    addZones(ax1, periodTime[0], periodTime[-1])
    plt.gcf().autofmt_xdate()
    plt.show()

# -----------------------------------------------------------------------------
# ------------------------------------ MAIN -----------------------------------
# -----------------------------------------------------------------------------
args = parse_args()

if args.mode == EXEC_TIME_MODE :
    
    flw_producer = producer(args.data_path)
    
    diff_lst = list()
    for dp in flw_producer:
        #print dp.targetTime-dp.now
        diff_lst.append((dp.timestamp, dp.diff.total_seconds()))
    
    diffTime,diffVal=zip(*diff_lst)
    
    fig, ax1 = plt.subplots()   
    plt.title("TCS-MCS Communication Analysis: {0} data from {1}\n Time before target time".format(args.system, args.date))
    ax1.plot(diffTime, diffVal, "b.", markersize=MARKERSIZE)
    ax1.grid(True)
    #ax1.set_ylim([-0.05,0.05])
    #ax1.set_yticks(np.arange(-0.05, 0.05, step=0.005))
 
    if args.system == 'both':
        flw_producer2 = producer(args.tcs_data_path)
        #TODO: Fix legend issues when plotting both subsystems
        diff_lst2 = list()
        for dp in flw_producer2:
            diff_lst2.append((dp.timestamp, dp.diff.total_seconds()))
    
        diffTime2,diffVal2=zip(*diff_lst2)    
    
        #ax2 = ax1.twinx()
        ax1.plot(diffTime2, diffVal2, "r.", markersize=MARKERSIZE)
        plt.gca().legend((MCS_SYSTEM+' entry', TCS_SYSTEM+' exit'))
    
    addZones(ax1, diffTime[0],diffTime[-1])
    plt.gcf().autofmt_xdate()
    plt.show()

elif args.mode == POS_DIFF_MODE:
    flw_producer = producer(args.data_path)

    firstVal = flw_producer.next()
    outliersInPeriod = 0
    periodLimits = Limits(-0.1,0.7)
    prevAz = firstVal.azPos
    prevEl = firstVal.elPos
    prevTimestamp = firstVal.targetTime
    az_lst, el_lst = list(), list()
    for dp in flw_producer:
        tBetweenSamples = (dp.targetTime-prevTimestamp).total_seconds()
        az_lst.append((dp.targetTime, (prevAz - dp.azPos)*3600.0))
        el_lst.append((dp.targetTime, (prevEl - dp.elPos)*3600.0))
        prevAz = dp.azPos
        prevEl = dp.elPos
        prevTimestamp = dp.targetTime
        if tBetweenSamples > periodLimits.upper or tBetweenSamples < periodLimits.lower:
            print "Period out of limits: {0} on date: {1}".format(tBetweenSamples, dp.timestamp)
            outliersInPeriod += 1
            
    print "Last read line with date:", dp.timestamp, dp.now, dp.targetTime
    azTime,azVal=zip(*az_lst)
    elTime,elVal=zip(*el_lst)
    
    
    fig, ax1 = plt.subplots()   
    plt.title("TCS-MCS Communication Analysis: {0} data from {1}".format(args.system, args.date))
    
    #Plot AZ
    ax1.plot(azTime, azVal, "b.-", markersize=MARKERSIZE)
    ax1.grid(True)
    ax1.tick_params("y", colors="b")
    ax1.set_ylabel("Azimuth difference between samples (not respecting timestamp - velocity)", color="b")
    ax1.set_ylim(-10, 10)
    
    #Plot EL
    elTime, elVal=zip(*el_lst)
    ax2 = ax1.twinx()
    ax2.plot(elTime, elVal, "r.-", markersize=MARKERSIZE)
    ax2.tick_params("y", colors="r")
    ax2.set_ylabel("Elevation", color="r")
    ax2.set_ylim(-10, 10)

    print "Number of detected period outliers: {0}".format(outliersInPeriod)
    print "Watch out: plot ylim set to -10 , 10 some information may not be shown on the graph" #TODO: At least count samples left out and report
    addZones(ax1, azTime[0],azTime[-1])
    plt.gcf().autofmt_xdate()
    plt.show()
    
elif args.mode == RAW_MODE:
    flw_producer = producer(args.data_path)
    elements = args.cols.split(",")
    
    timeBase, aLst, bLst = list(), list(), list()
    for dp in flw_producer:
        timeBase.append(dp.timestamp)
        aLst.append(elements[0])
        if len(elements) > 1:
            bLst.append(elements[1])
            
    fig, ax1 = plt.sublplots()

elif args.mode == PERIOD_MODE:
   plotPeriod()
   
else:
    print "Mode not found, check spelling"
