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

start_date = datetime(2020, 4, 2, 22, 10)
end_date = datetime(2020, 4, 2, 22, 11)

dm = DataManager(get_exporter('CP'), root_dir='/tmp/rcm')
data = list(dm.getData('ta:tc1:diff', start=start_date, end=end_date))

print("Analyzing", len(data), "values")  # data[0] is (datetime, val)

data_unzip = list(zip(*data))
dates = data_unzip[0]
vals = [x * 1000.0 for x in data_unzip[1]]  # convert to milliseconds
# pdb.set_trace()

fig, ax1 = plt.subplots()
plt.title("Time differences")
ax1.plot(dates, vals, "b.")
ax1.grid(True)
ax1.set_ylabel("Milliseconds")
plt.gcf().autofmt_xdate()
plt.show()

print("Ciao", datetime.now())
