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


FollowArray = namedtuple('FollowArray', 'timestamp now targetTime trackId azPos elPos diff')


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
        reader = csv.reader(source, delimiter=' ')

        for row in reader:
            if row[0].startswith('#'):
                continue
            if len(row) < 13:
                print row
                continue

            generationTime = datetime.fromtimestamp(float(row[4]))
            receptionTime = datetime.strptime(row[1]+' '+row[2], '%Y-%m-%d %H:%M:%S.%f')
            targetTime = datetime.fromtimestamp(float(row[6]))
            yield FollowArray(receptionTime, generationTime,\
                 targetTime,  datetime.fromtimestamp(float(row[8])), float(row[10]), float(row[12]), targetTime-generationTime \
                 )



# ---------- MAIN ----------

flw_producer = producer('./tcs2McsDems.txt')


diff_lst = list()
for dp in flw_producer:
    #print dp.targetTime-dp.now
    diff_lst.append((dp.timestamp, dp.diff.total_seconds()))

diffTime,diffVal=zip(*diff_lst)

fig, ax1 = plt.subplots()                                                                                                                                                         
plt.title("TCS-MCS Communication Analysis: data from \n Time before target time")
ax1.plot(diffTime, diffVal, "b.")                                               
ax1.grid(True)

plt.gcf().autofmt_xdate()                                                       
plt.show()
