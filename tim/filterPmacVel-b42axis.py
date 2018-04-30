#!/usr/bin/env python

# vim: ai:sw=4:sts=4:expandtab

import argparse
from collections import namedtuple
from datetime import datetime, timedelta
from itertools import groupby
from operator import attrgetter, itemgetter
import csv
import sys
import pdb
import matplotlib.pyplot as plt

ERRTHRESHOLD_ARCSEC = 1.5
# Number of consecutive errors that make a significant event
# With high-resolution data, we have 10 measurements per second
SIGNIFICANT = 20

# Error threshold, in degrees
ERRTHRESHOLD = ERRTHRESHOLD_ARCSEC/3600.0

Stats = namedtuple('Stats', 'avg max min med')

class DataRange(object):
    def __init__(self, data, padding=0):
        self.raw = sorted(data)
        self.padding = timedelta(seconds=abs(padding))

    def __len__(self):
        return len(self.raw)

    def __lt__(self, stamp):
        return self.time_bounds[1] < stamp

    def __gt__(self, stamp):
        return self.time_bounds[0] > stamp

    def __contains__(self, stamp):
        return (self.time_bounds[0] - self.padding) <= stamp <= (self.time_bounds[1] + self.padding)

    @property
    def timestamps(self):
        return (x[0] for x in self.raw)

    @property
    def time_bounds(self):
        return (self.raw[0][0], self.raw[-1][0])

    @property
    def values(self):
        return (x[1] for x in self.raw)

    def stats(self):
        errs = list(self.errors)
        return Stats(sum(errs) / len(errs), max(errs), min(errs), errs[len(errs)/2])       

    def __repr__(self):
        return "<DataRange {0} events [{1} - {2}]>".format(len(self), *self.time_bounds)

class DataRangeCollection(list):
    def __contains__(self, value):
        if self[0] > value or self[-1] < value:
            return False
        # This assumes that the DataRangeCollection is ordered
        return any(value in k for k in self)

    def getIndex(self, stamp):
        if stamp in self:
            for index, dr in enumerate(self):
                if stamp in dr:
                    return index
        return -1

    def getSubset(self, begin, end):
        return -1


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

def parse_args():
    parser = argparse.ArgumentParser(description='Filter PMAC Error data')
    thrhold = parser.add_mutually_exclusive_group()
    thrhold.add_argument('-a', dest='pmac_eth_arc', default=ERRTHRESHOLD_ARCSEC,
                               type=float, help='PMAC error threshold, in arcsec')
    thrhold.add_argument('-d', dest='pmac_eth_deg', default=ERRTHRESHOLD, type=float, help='PMAC error threshold, in degrees')
    parser.add_argument('-s', dest='significant_ev', default=SIGNIFICANT, type=int, help='Number of consecutive errors considered as significant')
    parser.add_argument('error_data', help='Path to the file with the PMAC error data')
    parser.add_argument('vel_data', help='Path to the file with the velocity data')

    args = parser.parse_args()

    if args.pmac_eth_deg != ERRTHRESHOLD:
        args.pmac_eth_arc = args.pmac_eth_deg * 3600.0
    elif args.pmac_eth_arc != ERRTHRESHOLD_ARCSEC:
        args.pmac_eth_deg = args.pmac_eth_arc / 3600.0

    return args


args = parse_args()
total, signif = 0, 0
err_producer = producer(args.error_data)
vel_producer = producer(args.vel_data)

error_ranges = DataRangeCollection()

for k, group in groupby(err_producer, lambda x: abs(x[1]) > args.pmac_eth_deg):
    lst = list(group)
    total += len(lst)
    if k and len(lst) > args.significant_ev:
        signif += len(lst)
        dr = DataRange(lst)
        error_ranges.append(dr)

events = []
conflict_ranges = DataRangeCollection()

for k, group in groupby(vel_producer, lambda x: abs(x[1]) < 0.1 and x[0] in error_ranges):
    if k:
        lst = list(group)
        #if not ( lst[0] in conflict_ranges ) :
        #    conflict_ranges.append(DataRange(lst))
        #pdb.set_trace()
        #print error_ranges.getIndex(lst[0][0])
        print "Found a potential match between {0} and {1}".format(lst[0][0], lst[-1][0])

vel_producer2 = producer(args.vel_data)

for dr in error_ranges:
    #pdb.set_trace()
    
    begin, end = dr.time_bounds
    begin -= timedelta(seconds=5)
    end += timedelta(seconds=5)
    vel_lst = list()

    for x in vel_producer2:
        if x[0] > begin:
            vel_lst.append((x[0], x[1]*3600.))
        if x[0] > end:
            #pdb.set_trace()
            break
    velTime,velVal=zip(*vel_lst)
    
    plt.grid(True)
    plt.title("PMAC Position Error\n%s" % dr )

    plt.plot(velTime,velVal, "b.-")
    plt.plot([ts for ts in dr.timestamps], [val*3600. for val in dr.values], "r.")
    plt.gcf().autofmt_xdate()
    plt.show()
print "Total events: {0}, of which significant: {1}".format(total, signif)
#