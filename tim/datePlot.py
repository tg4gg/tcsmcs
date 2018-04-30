#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 28 15:39:00 2018

@author: tgaggstatter
"""

from datetime import datetime as dt
from datetime import timedelta as td

dates = ['01/02/1991 08:00','01/03/1991 01:00','01/04/1991 08:00']
x = [dt.strptime(d,'%m/%d/%Y %H:%M') for d in dates]
y = range(len(x)) # many thanks to Kyss Tao for setting me straight here
y2 = range(2) # many thanks to Kyss Tao for setting me straight here

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

#plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%Y'))
#plt.gca().xaxis.set_major_locator(mdates.DayLocator())

a0 = dt.now()
a1 = dt.now() - td(days=1)
a2 = dt.now() - td(days=2)
a3 = dt.now() - td(days=3)
a4 = dt.now() - td(days=4)
a5 = dt.now() - td(days=5)



x2 = [a5, a4]
x3 = [a5, a3, a0]

plt.plot(x2,y2)
plt.plot(x3,y)

plt.gcf().autofmt_xdate()
plt.show()
