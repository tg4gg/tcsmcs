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


LineArray = namedtuple('LineArray', 'timestamp now')


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

        for row in reader:
            if row[0].startswith('#'):
                continue
            if len(row) < 5:
                print row
                continue

            now = datetime.fromtimestamp(float(row[3]))
            receptionTime = datetime.strptime(row[1]+' '+row[2], '%Y-%m-%d %H:%M:%S.%f')
            #targetTime = datetime.fromtimestamp(float(row[6]))
            yield LineArray(receptionTime, now)



# ---------- MAIN ----------

fileName = './dataTime.txt'
fileName = './2018-04-12_miPrimerIOC_timeVal.txt'
fileName = './2018-04-13_miPrimerIOC-CP-2.txt'
flw_producer = producer(fileName)

tolerance = 0.5 # In miliseconds
limits = (-tolerance, tolerance)
print "limites:", limits
diff_lst = list()
prevTime, prevOutlierTime = datetime.now(),  datetime.now()
maxVal, minVal, outlierCont = 0.0, 0.0, 0
for dp in flw_producer:
    diff = ((dp.now - prevTime).total_seconds()*1000.)-100 #subtract expected value
    if  limits[0] > diff or diff > limits[1] :
    	print dp.timestamp, " outlier:", diff, "prevOutlier:", (dp.now-prevOutlierTime).total_seconds()
    	prevOutlierTime = dp.now
    	outlierCont += 1
    maxVal = max(diff, maxVal)
    minVal = min(diff, minVal)
    prevTime = dp.now
    diff_lst.append((dp.timestamp, diff))

print "Max:", maxVal, " Min:", minVal, "Total outliers:", outlierCont

diffTime,diffVal=zip(*diff_lst)

fig, ax1 = plt.subplots()                                                                                                                                                         
plt.title("TCS-MCS Communication Analysis: data from \n Time before target time (in milliseconds)")
ax1.plot(diffTime[1:], diffVal[1:], "b.") #Ignore first wrong sample                                               
ax1.grid(True)
#ax1.set_ylim(99.9, 100.1)
plt.gcf().autofmt_xdate()                                                       
plt.show()
