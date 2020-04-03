#! /usr/bin/python
"""
Print time differences
"""
import sys
sys.path.append('../')
from swglib.export import DataManager, get_exporter
from datetime import datetime, timedelta, date
import pdb
import matplotlib.pyplot as plt
import Qt4Agg

dm = DataManager(get_exporter('CP'), root_dir='/tmp/rcm')
data = list(dm.getData('ta:tc1:diff', start=datetime(2020, 04, 02, 22), end=datetime(2020, 04, 03, 06)))

print "Analyzing" , len(data) , "values" # data[0] is (datetime, val)

datazip = zip(*data)
dates = datazip[0]
vals = datazip[1]
#pdb.set_trace()


fig, ax1 = plt.subplots()
plt.title("TCS-MCS C")
ax1.plot(dates, vals, "b.")
ax1.grid(True)
plt.show()

print "Ciao",datetime.now()
