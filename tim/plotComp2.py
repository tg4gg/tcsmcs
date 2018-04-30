import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt
import datetime as dt
import pandas as pd
import sys, os, fnmatch
import pickle

plt.close('all')

f = './azPmacbinaryCPO/2018-03-05_CPOexport.txt.data.pkl'
f2 = './azPmacbinaryCPO/2018-03-05_CPOexport.txt.pkl'
f2mcs = './mcsbinaryCPO/2018-03-05_CPOexport.txt.pkl'

data = pd.read_pickle(open(f,'r'))
data = data * 3600
ts = pd.read_pickle(open(f2,'r'))

tsmcs = pd.read_pickle(open(f2mcs,'r'))
diffs = np.diff(tsmcs)
datamcs = diffs / np.timedelta64(1, 's')

# f, (g1, g2) = plt.subplots(2, sharex=True)

f, g1 = plt.subplots()
g1.plot(ts, data, "r-") #azPmac pos error
g1.set_ylim(-3, +3)

g2 = g1.twinx()
g2.plot(tsmcs[1:tsmcs.size], datamcs, "b.") #mcs jitter

plt.gcf().autofmt_xdate()

plt.show()



