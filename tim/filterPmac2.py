#!/usr/bin/env python

# vim: ai:sw=4:sts=4:expandtab

from datetime import datetime
from itertools import groupby
import csv
import sys
import pdb

# Given in arcsec. ERRTHRESHOLD is in degrees
ERRTHRESHOLD = 1.5/3600
# Number of consecutive errors that make a significant event
# With high-resolution data, we have 10 measurements per second
SIGNIFICANT = 20

def producer(filename):
    with open(filename) as source:
        reader = csv.reader(source, delimiter='\t')
        # Skip the headers
        next(reader); next(reader); next(reader); next(reader)

        for row in reader:
            if row[0].startswith('#'):
                continue
            main, _, nanosec = row[0].partition('.')
            yield datetime.strptime('{0}.{1}'.format(main, nanosec[:6]), '%m/%d/%Y %H:%M:%S.%f'), float(row[1])
        pdb.set_trace()

total, signif = 0, 0
for k, group in groupby(producer(sys.argv[1]), lambda x: abs(x[1]) > ERRTHRESHOLD):
    lst = list(group)
    total += len(lst)
    if k and len(lst) > SIGNIFICANT:
        signif += len(lst)
        errors = sorted([abs(x[1]) for x in lst])
        print "Group of {0} events starting at {1}.\tAvg/max/med: {2:.4f}/{3:.4f}/{4:.4f}".format(len(lst), lst[0][0], sum(errors)/len(lst), max(errors), errors[len(errors)/2])

print "Total events: {0}, of which significant: {1}".format(total, signif)
pdb.set_trace()