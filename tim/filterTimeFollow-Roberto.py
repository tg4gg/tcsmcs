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

LineArray = namedtuple('LineArray', 'timestamp now targetTime diff')

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

    parser = argparse.ArgumentParser(description='Analyze  data')
    parser.add_argument('-p',    '--path',           dest='data_path',            default='./test1_13apr2018', help='Path to the camonitor data')
    parser.add_argument('-t',    '--title',           dest='title',               default='', help='A title to better identify data when saving images to disk')
    #parser.add_argument('-day',   '--eng_mode',        dest='eng_mode',          action='store_true', help='If used daytime will be analyzed 6am-6pm')

    args = parser.parse_args()

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
        reader = csv.reader(source, delimiter=' ', skipinitialspace=True)
        # Skip the headers
        next(reader); next(reader); next(reader); next(reader)
        linenr = 0
        try:
            for row in reader:
                linenr += 1
                if len(row) < 5:
                	print "Line not analyzed", row
        		continue
                if row[0].startswith('#') or row[1].startswith('#'):
                       continue
                try: 
                    now = datetime.fromtimestamp(float(row[4]))
                    receptionTime =  datetime.strptime(row[1]+' '+row[2], '%Y-%m-%d %H:%M:%S.%f')
                    targetTime = datetime.fromtimestamp(float(row[5])) #Target time is just now

                    if (linenr%100000== 0):
                        print linenr/1000, "K rows read...", receptionTime

                    yield LineArray(receptionTime, now, targetTime, now-targetTime)
                except Exception as exF:
                    print "ERROR after line:", row
                    print "Exception on line:", linenr
                    print exF
                    pass

        except Exception as ex:
            print "ERROR after line:", row 
            print "Exception on line:", linenr
            print ex
            pass

args = parse_args()

# ---------- MAIN ----------
flw_producer = producer(args.data_path)

tolerance = 0.5 # In miliseconds
limits = (-tolerance, tolerance)
#print "limites:", limits
diff_lst = list()
first = flw_producer.next()
prevTime, prevOutlierTime = first.now,  first.now
maxVal, minVal, outlierCont = -1000.0, 1000.0, 0
for dp in flw_producer:
#    diff = ((dp.now - prevTime).total_seconds()*1000.)-100 #subtract expected value
#    if  limits[0] > diff or diff > limits[1] :
#    	print dp.timestamp, " outlier:", diff, "prevOutlier:", (dp.now-prevOutlierTime).total_seconds()
#    	prevOutlierTime = dp.now
#    	outlierCont += 1
#    print dp
    diff = dp.diff.total_seconds()*1000.0
    maxVal = max(diff, maxVal)
    minVal = min(diff, minVal)
    prevTime = dp.now
    diff_lst.append((dp.timestamp, diff))

print "Last date read:", dp.timestamp
print "Max:", maxVal, " Min:", minVal, "Total outliers:", outlierCont

diffTime,diffVal=zip(*diff_lst)

fig, ax1 = plt.subplots()                                                                                                                                                         
plt.title("TCS-MCS Communication Analysis: {0} \n Time before target time (in milliseconds)".format(args.title))
ax1.plot(diffTime[1:], diffVal[1:], "b.") #Ignore first wrong sample                                               
ax1.grid(True)
#ax1.set_ylim(99.9, 100.1)
plt.gcf().autofmt_xdate()                                                       
plt.show()

