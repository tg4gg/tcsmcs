#!/usr/bin/env python

# vim: ai:sw=4:sts=4:expandtab

###########################################################
#
#  Author:        Ricardo Cardenes <rcardenes@gemini.edu>
#
#  2018-04-05 (rjc):
#      Started a module off the core parts of filterPmac.py
#  2018-05-01 (rjc):
#      Modified producer to stop using the csv module
###########################################################

from collections import namedtuple
from datetime import datetime, timedelta
import itertools
import argparse
import sys
import os

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
    def __init__(self, data, predicate, padding=0):
        self.raw = sorted(map(lambda x: DataPoint(*x), data))
        self.padding = timedelta(seconds=abs(padding))
        self._pred = predicate
        self._outliers = None

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
    def outliers(self):
        if self._outliers is None:
            self._outliers = len(filter(self._pred, self.raw))
        return self._outliers

    @property
    def timestamps(self):
        return (x.stamp for x in self.raw)

    @property
    def time_bounds(self):
        return Bounds(self.raw[0].stamp - self.padding, self.raw[-1].stamp + self.padding)
    
    @property
    def period_length(self):
        return self.time_bounds.end - self.time_bounds.start        

    @property
    def values(self):
        return (x[1] for x in self.raw)

    def intersects(self, rng):
        return rng.time_bounds.start <= self.time_bounds.end and rng.time_bounds.end >= self.time_bounds.start

    def split(self, rng):
        if rng.intersects(self):
            lbound, hbound = rng.time_bounds
            return (
                DataRange(filter(lambda x: x.stamp < lbound, self.raw), self._pred, self.padding.seconds),
                DataRange(filter(lambda x: x.stamp > hbound, self.raw), self._pred, self.padding.seconds)
                )
        else:
            return (self,)

    def stats(self):
        """
        Returns a `Stats` tuple with some basic statistics on the error data
        contained by this `DataRange`
        """
        errs = list(self.values)
        return Stats(sum(errs) / len(errs), max(errs), min(errs), errs[len(errs)/2])

    def __repr__(self):
        if len(self):
            return "<DataRange {0} events [{1} - {2}]>".format(len(self), *self.time_bounds)
        else:
            return "<DataRange 0 events>"

class DataRangeCollection(object):
    """
    Collection of `DataRange` instances. This is just an augmented
    `list`, to test for inclusion of a timestime within the contained
    instances.
    """
    def __init__(self, lst=()):
        self._lst = list(lst)

    def __len__(self):
        return len(self._lst)

    def __iter__(self):
        return iter(self._lst)

    def __contains__(self, value):
        if self[0] > value or self[-1] < value:
            return False
        # This assumes that the DataRangeCollection is ordered
        return any(value in k for k in self)

    @property
    def time_bounds(self):
        return Bounds(self._lst[0].time_bounds.start, self._lst[-1].time_bounds.end)

    def append(self, data):
        self._lst.append(data)

    def subtract(self, rng, is_significant):
        self._lst = filter(is_significant, itertools.chain.from_iterable(map(lambda x: x.split(rng), self._lst)))

def producer(filename):
    with open(filename) as source:
        for line in source:
            line = line.strip()
            if line == '' or line.startswith('#'):
                continue
            parts = line.split('\t')
            date = parts[0]
            rest = parts[1:]
            dt = datetime.strptime(date[:-3] if len(date) == 29 else date, '%m/%d/%Y %H:%M:%S.%f')
            yield (dt,) + tuple(float(x) for x in rest)

def find_event_ranges(data, predicate, significant, gap):
    positive    = 0
    events      = [] # Error data
    queued      = [] # Non-error data, potential gap

    for k in data:
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
