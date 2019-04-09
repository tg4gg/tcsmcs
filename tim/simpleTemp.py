#! /usr/bin/python
"""
Obtain temperature values from GWS
Print out the lowest temperature over the period
"""
import sys
sys.path.append('../')
from swglib.export import DataManager, get_exporter
from datetime import datetime, timedelta, date

dm = DataManager(get_exporter('CP'), root_dir='/tmp/rcm')
data = list(dm.getData('ws:cpTemp50m', start=datetime(2018, 7, 19), end=datetime(2018, 7, 20)))

print "Analyzing" , len(data) , "values"
min_temp = (datetime(2018,1,1), 100.0)

for val in data:
	currTemp = val[1]
	if currTemp < min_temp[1]:
		min_temp = val
		print "New minimum found:", val[0], val[1]


print "\nLowest temperture during the requested period was: {0} on date: {1}".format(min_temp[1], min_temp[0])

if min_temp[1] == 0:
	print "Warning!! The lowest temperature might be a reading error, zero shows up often as a default value, double check the data manually."