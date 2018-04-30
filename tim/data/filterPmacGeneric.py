#!/usr/bin/env python

# vim: ai:sw=4:sts=4:expandtab

###########################################################
#
#  PMAC Error Data Filtering
#
#  This script is designed to filter PMAC position error data,
#  matching it against a velocity, in order to identify potential
#  periods where MCS is not properly following the TCS positioning
#  stream
#
#  Author:        Ricardo Cardenes <rcardenes@gemini.edu>
#  Last modfied:  2018-04-02

import argparse
from collections import namedtuple
from datetime import datetime, timedelta
from itertools import dropwhile, groupby
from operator import attrgetter, itemgetter
import csv
import sys
import socket

ERRTHRESHOLD_ARCSEC = 1.5
# Number of consecutive errors that make a significant event
# With high-resolution data, we have 10 measurements per second
SIGNIFICANT = 20

# Error threshold, in degrees
ERRTHRESHOLD = ERRTHRESHOLD_ARCSEC/3600.0

# We're looking for consecutive values past the threshold, allowing
# for small gaps. This value defines how large the gap can be
MAXGAP = 30

# directory where the data is located
root_data_dir = '/net/cpostonfs-nv1/tier2/gem/sto/archivertems/tcsmcs/data/'
if (socket.gethostname() == 'sbfrtdev-lv1.cl.gemini.edu'):
	root_data_dir = '/archive/tcsmcs/data/'

# Site should be cp or mk
SITE = 'cp'

DEBUG = True

Stats = namedtuple('Stats', 'avg max min med')

class DataRange(object):
    """
    Container class that keeps a list of error datapoints. Initialized
    passing a list of `(timestamp, value)` pairs and, optionally, a
    `padding`, measured in seconds, which must be non-negative.

    By default, `padding = 0`. When comparing an instance of `DataRange` with
    a timestamp, the bounding limits will be `smallest_timestamp - padding`
    and `largest_timestamp + padding`.
    """
    def __init__(self, data, padding=0):
        self.raw = sorted(data)
        self.padding = timedelta(seconds=abs(padding))

    def __len__(self):
        return len(self.raw)

    def __lt__(self, stamp):
        return (self.time_bounds[1] + self.padding) < stamp

    def __gt__(self, stamp):
        return (self.time_bounds[0] - self.padding) > stamp

    def __contains__(self, stamp):
        return (self.time_bounds[0] - self.padding) <= stamp <= (self.time_bounds[1] + self.padding)

    @property
    def timestamps(self):
        return (x[0] for x in self.raw)

    @property
    def time_bounds(self):
        return (self.raw[0][0], self.raw[-1][0])

    @property
    def errors(self):
        return (x[1] for x in self.raw)

    def stats(self):
        """
        Returns a `Stats` tuple with some basic statistics on the errors
        contained by this `DataRange`
        """
        errs = list(self.errors)
        return Stats(sum(errs) / len(errs), max(errs), min(errs), errs[len(errs)/2])

    def __repr__(self):
        return "<DataRange {0} events [{1} - {2}]>".format(len(self), *self.time_bounds)

class DataRangeCollection(list):
    """
    Collection of `DataRange` instances. This is just an augmented
    `list`, to test for inclusion of a timestime within the contained
    instances.
    """
    def __contains__(self, value):
        if self[0] > value or self[-1] < value:
            return False
        # This assumes that the DataRangeCollection is ordered
        return any(value in k for k in self)

class MemoizingPredicate(object):
    def __init__(self, predicate, gap=MAXGAP):
        self._mem  = []
        self._gap  = gap
        self._pred = predicate

    def __call__(self, data):
        res = self._pred(data)
        if res:
            self._mem.append(True)
            return True
        elif (self._gap > 0) and any(self._mem[-self._gap:]):
            self._mem.append(res)
            return True

        self._mem = []
        return False

def producer(filename):
    with open(filename) as source:
        reader = csv.reader(source, delimiter='\t')
        # Skip the headers
        next(reader); next(reader); next(reader); next(reader)

        for row in reader:
            if row[0].startswith('#'):
                continue
            yield datetime.strptime(row[0][:-3], '%m/%d/%Y %H:%M:%S.%f'), float(row[1])

def parse_args():
    yesterday = (datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d")
    
    parser = argparse.ArgumentParser(description='Filter PMAC Error data')
    thrhold = parser.add_mutually_exclusive_group()
    thrhold.add_argument('-a', dest='pmac_eth_arc', default=ERRTHRESHOLD_ARCSEC,
                               type=float, help='PMAC error threshold, in arcsec')
    thrhold.add_argument('-d', dest='pmac_eth_deg', default=ERRTHRESHOLD, type=float, help='PMAC error threshold, in degrees')
    parser.add_argument('-s', dest='significant_ev', default=SIGNIFICANT, type=int, help='Number of consecutive errors considered as significant')
    parser.add_argument('-g', dest='max_gap', default=MAXGAP, type=int, help='Number of values under threshold that still count as within a significant chunk of error data')
    #parser.add_argument('error_data', help='Path to the file with the PMAC error data')
    #parser.add_argument('vel_data', help='Path to the file with the velocity data')
    parser.add_argument('-axis', dest='axis', default='az', help='Axis to be analyzed, should be az or el')
    parser.add_argument('-date', dest='date', default=yesterday, help='Date - format YYYY-MM-DD')

    args = parser.parse_args()
    if args.pmac_eth_deg != ERRTHRESHOLD:
        args.pmac_eth_arc = args.pmac_eth_deg * 3600.0
    elif args.pmac_eth_arc != ERRTHRESHOLD_ARCSEC:
        args.pmac_eth_deg = args.pmac_eth_arc / 3600.0

    if args.max_gap < 0:
        print sys.stderr >> "Can't accept negative numbers for the gap"
        sys.exit(-1)
    
    #Construct the path to the data    
    args.error_data = ROOT_DATA_DIR + SITE + '/mcs/' + args.axis + 'PmacPosError/txt/' +\
        args.date + '_' + SITE + '_mc-' + args.axis + 'PmacPosError_export.txt'         

    if args.date == yesterday and DEBUG:
        args.error_data = args.error_data.replace(yesterday, "2018-03-22").replace(".txt", "_test.txt")
        args.error_data = args.error_data.replace("azPmacPosError", "elPmacPosError")
    
    args.vel_data = args.error_data.replace("PmacPosError","CurrentVel")    
    
    return args


args = parse_args()

err_producer = producer(args.error_data)
vel_producer = producer(args.vel_data)

error_ranges = DataRangeCollection()

def rstrip_events(lst, predicate):
    return tuple(reversed(tuple(dropwhile(lambda x: not predicate(x), reversed(lst)))))

pred = lambda x: abs(x[1]) > args.pmac_eth_deg
for k, group in groupby(err_producer, MemoizingPredicate(predicate=pred, gap=args.max_gap)):
    if not k:
        continue
    lst = list(group)
    if len(lst) > args.significant_ev:
        lst2 = rstrip_events(lst, pred)
        dr = DataRange(rstrip_events(lst, pred))
        error_ranges.append(dr)

events = []
pred = lambda x: abs(x[1]) <= 0.1 and x[0] in error_ranges
for k, group in groupby(vel_producer, MemoizingPredicate(predicate=pred, gap=args.max_gap)):
    if k:
        lst = rstrip_events(list(group), pred)
        print "Found a potential match between {0} and {1}".format(lst[0][0], lst[-1][0])

# print "Total events: {0}, of which significant: {1}".format(total, signif)
