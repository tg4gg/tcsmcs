import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt
import datetime as dt
import pandas as pd
import sys, os, fnmatch
import pickle
import pprint


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in xrange(0, len(l), n):
        yield l[i:i + n]

#compute number of days
f = sys.argv[1]
if "CPO" in f:
    site = "CPO"
else:
    site = "MKO"

df = pd.read_pickle(open(f, 'r'))
min_date = df['dates'][0]
max_date = df['dates'][len(df)-1]

#df_by_months = list(chunks(df, 30))
df_by_months = np.array_split(df, 6)

print df_by_months[1]['counts']
#pprint.pprint(df_by_months[1])
#pprint.pprint(df_by_months[2]['dates'])
#print df_by_months[1]['dates']
#sys.exit()
#current_month =  df_by_months[1]['dates']
#print current_month

nmonths=len(df_by_months)
ndays_in_month=len(df_by_months[0])
print "df_by_months size: %d by %d" % (nmonths, ndays_in_month)
#print df_by_months[1][:]

#system='testsystem'
#site='testsite'
outpath = './'
my_dpi=96;

fig, axs = plt.subplots(nrows=2, ncols=3, figsize=(1920/my_dpi, 1200/my_dpi), dpi=my_dpi, facecolor='w', edgecolor='k')
histfile = "%s/%s_hist_%s" % (outpath, os.path.splitext(os.path.basename(f))[0], '.png')
fig.subplots_adjust(hspace = 0.5)

#plt.hist(bad_counts, bins=length)
#ax.bar(range(length), df['counts'])
axs = axs.ravel()

for i in range(nmonths):
    pos = np.arange(len(df_by_months[i]['dates']))
    w=0.8

    cts = df_by_months[i]['counts']
    mask1 = cts <= 100
    mask2 = cts > 100

    axs[i].bar(pos[mask1], cts[mask1], w, alpha=0.5, color='b')
    axs[i].bar(pos[mask2], cts[mask2], w, alpha=0.5, color='r')
    #axs[i].set_title()
    #ax.bar([p + w for p in pos], df['r3counts'], w, alpha=0.5, color='g')
    #ax.bar([p + w for p in pos], df['r3counts'], w, alpha=0.5, color='g')
    #ax.bar([p + 3*w for p in pos], df['r3counts'], w, alpha=0.5, color='y')
    plt.sca(axs[i])
    plt.xticks([p-1 for p in pos], df_by_months[i]['dates'], rotation=70)
    #plt.setp(plt.gca().get_xticklabels(), visible=False)
    #plt.setp(plt.gca().get_xticklabels()[::35], visible=True)
    plt.xlim(min(pos)-1, max(pos)+1)

mytitle = "%s TCS to MCS Samples Delayed Greater Than 150 ms\n Out of 432000 samples per night total." % site
fig.suptitle(mytitle)
fig.savefig(histfile, dpi=my_dpi)
plt.show(fig)

print "done"
sys.exit()


