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

from datetime import datetime, timedelta
import itertools
import argparse
import csv
import sys
import os
from pprint import pprint

from swglib import DataRange, DataRangeCollection
from swglib import producer, find_event_ranges

ERRTHRESHOLD_ARCSEC = 1.5
VELTHRESHOLD = 0.004
# Number of consecutive errors that make a significant event
# With high-resolution data, we have 10 measurements per second
SIGNIFICANT = 20

# Error threshold, in degrees
ERRTHRESHOLD = ERRTHRESHOLD_ARCSEC/3600.0

# We're looking for consecutive values past the threshold, allowing
# for small gaps. This value defines how large the gap can be
MAXGAP = 30

# Site should be either 'cp' or 'mk'
SITE = 'cp'

if SITE == 'cp':
    # directory where the data is located
    root_data_dir = '/archive/tcsmcs/data'
    if not os.path.exists(root_data_dir):
        root_data_dir = '/net/cpostonfs-nv1/tier2/gem/sto/archivertems/tcsmcs/data'
else:
    raise NotImplementedError("The script hasn't still been adapted for MK")

DEBUG = True

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

error_ranges = DataRangeCollection()
err_pred = lambda x: abs(x[1]) > args.pmac_eth_deg
for group in find_event_ranges(err_producer, err_pred, significant=args.significant_ev, gap=args.max_gap):
    error_ranges.append(DataRange(group, err_pred))

vel_pred = lambda x: abs(x[1]) > VELTHRESHOLD

is_significant = lambda dr: len(filter(err_pred, dr)) >= args.significant_ev
for group in find_event_ranges(vel_producer, vel_pred, significant=0, gap=args.max_gap):
    error_ranges.subtract(DataRange(group, vel_pred, padding=10), is_significant)

for rng in error_ranges:
    print "{0} ... {1}".format(*rng.time_bounds)

# print "Total events: {0}, of which significant: {1}".format(total, signif)
