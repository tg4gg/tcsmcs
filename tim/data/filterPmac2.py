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
#
#  2018-04-02 (rjc): First functional version
#  2018-04-03 (tg):  Modified the command line arguments to simplify referring
#                    to the raw data
#  2018-04-03 (rjc): Refactored the code to include a specialized grouping function
#                    instead of the memoizing predicate we had before

from collections import namedtuple
from datetime import datetime, timedelta
import itertools
import argparse
import csv
import sys
import os
from pprint import pprint

ERRTHRESHOLD_ARCSEC = 1.5
VELTHRESHOLD = 0.004
# Number of consecutive errors that make a significant event
# With high-resolution data, we have 10 measurements per second
SIGNIFICANT = 5

# Error threshold, in degrees
ERRTHRESHOLD = ERRTHRESHOLD_ARCSEC/3600.0

# We're looking for consecutive values past the threshold, allowing
# for small gaps. This value defines how large the gap can be
MAXGAP = 30*10

# Site should be either 'cp' or 'mk'
SITE = 'cp'

if SITE == 'cp':
    # directory where the data is located
    root_data_dir = '/archive/tcsmcs/data'
    if not os.path.exists(root_data_dir):
        root_data_dir = '/net/cpostonfs-nv1/tier2/gem/sto/archiveRTEMS/tcsmcs/data'
else:
    raise NotImplementedError("The script hasn't still been adapted for MK")

DEBUG = True

Stats = namedtuple('Stats', 'avg max min med')
Bounds = namedtuple('Bounds', 'start end')
DataPoint = namedtuple('DataPoint', 'stamp value')

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
        self.raw = sorted(map(lambda x: DataPoint(*x), data))
        self.padding = timedelta(seconds=abs(padding))

    def __len__(self):
        return len(self.raw)

    def __lt__(self, stamp):
        return (self.time_bounds.end) < stamp

    def __gt__(self, stamp):
        return (self.time_bounds.startd) > stamp

    def __contains__(self, stamp):
        return (self.time_bounds.startd) <= stamp <= (self.time_bounds.end)

    def __iter__(self):
        return iter(self.raw)

    @property
    def timestamps(self):
        return (x.stamp for x in self.raw)

    @property
    def time_bounds(self):
        return Bounds(self.raw[0].stamp - self.padding, self.raw[-1].stamp + self.padding)

    @property
    def time_frame(self):
        return self.time_bounds.end - self.time_bounds.start        

    @property
    def errors(self):
        return (x[1] for x in self.raw)

    def intersects(self, rng):
        return rng.time_bounds.start <= self.time_bounds.end and rng.time_bounds.end >= self.time_bounds.start

    def split(self, rng):
        if rng.intersects(self):
            lbound, hbound = rng.time_bounds
            return DataRange(filter(lambda x: x.stamp < lbound, self.raw)), DataRange(filter(lambda x: x.stamp > hbound, self.raw))
        else:
            return (self,)

    def stats(self):
        """
        Returns a `Stats` tuple with some basic statistics on the errors
        contained by this `DataRange`
        """
        errs = list(self.errors)
        return Stats(sum(errs) / len(errs), max(errs), min(errs), errs[len(errs)/2])

    def __repr__(self):
        return "<DataRange {0} events [{1} - {2}]>".format(len(self), *self.time_bounds)

class DataRangeCollection(object):
    """
    Collection of `DataRange` instances. This is just an augmented
    `list`, to test for inclusion of a timestime within the contained
    instances.
    """
    def __init__(self, lst=()):
        self._lst = list(lst)

    def __iter__(self):
        return iter(self._lst)

    def __contains__(self, value):
        if self[0] > value or self[-1] < value:
            return False
        # This assumes that the DataRangeCollection is ordered
        return any(value in k for k in self)

    @property
    def lst(self):
        return self._lst

    def append(self, data):
        self._lst.append(data)

    def subtract(self, rng, is_significant):
        self._lst = filter(is_significant, itertools.chain.from_iterable(map(lambda x: x.split(rng), self._lst)))

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
    args.error_data = os.path.join(
            root_data_dir, SITE, 'mcs',
            '{0}PmacPosError'.format(args.axis),
            'txt', 
            '{0}_{1}_mc-{2}PmacPosError_export.txt'.format(args.date, SITE, args.axis)
        )

    if args.date == yesterday and DEBUG:
        args.error_data = (
            args.error_data.replace(yesterday, "2018-03-22")
                .replace(".txt", "_test.txt")
                .replace("azPmacPosError", "elPmacPosError")
            )
    
    args.vel_data = args.error_data.replace("PmacPosError","CurrentVel")    

    return args


args = parse_args()
err_producer = producer(args.error_data)
vel_producer = producer(args.vel_data)

def find_event_ranges(data, predicate, significant=SIGNIFICANT, gap=MAXGAP, indices=False):
    positive    = 0
    first, last = 0, 0
    events      = []
    queued      = []

    for n, k in enumerate(data):
        if predicate(k):
            if queued:
               events.extend(queued)
               queued = []
            events.append(k)
            positive += 1
        elif events:
            if len(queued) < gap:
                queued.append(k)
            else:
                if positive >= significant:
                    yield events
                queued = []
                events = []
                positive = 0
    else:
        if events:
            yield events
        raise StopIteration


# ---------- MAIN ----------
error_ranges = DataRangeCollection()
err_pred = lambda x: abs(x[1]) > args.pmac_eth_deg
for group in find_event_ranges(err_producer, err_pred, significant=args.significant_ev, gap=args.max_gap):
    error_ranges.append(DataRange(group))

rawErrLen = len(error_ranges.lst)
vel_pred = lambda x: abs(x[1]) > VELTHRESHOLD

is_significant = lambda dr: len(filter(err_pred, dr)) >= args.significant_ev
for group in find_event_ranges(vel_producer, vel_pred, significant=0, gap=args.max_gap):
    error_ranges.subtract(DataRange(group), is_significant)

prevTSEnd = error_ranges.lst[0].time_bounds.start
for rng in error_ranges:
    print "{0} ... {1} length: {2}, distance from previous: {3}".format(rng.time_bounds.start,\
             rng.time_bounds.end, rng.time_frame, rng.time_bounds.start-prevTSEnd)
    prevTSEnd = rng.time_bounds.end
print "Error zones: {0}, after velocity filter: {1}".format( rawErrLen, len(error_ranges.lst))

# print "Total events: {0}, of which significant: {1}".format(total, signif)
