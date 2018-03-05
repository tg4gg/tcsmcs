# tcsmcs
A very crude set of scripts for analyzing Gemini TCS-->MCS data 
The entire process has a few key steps to generate scatter plots of sample rate performance between the TCS and MCS.
1. Harvest the **full** data for the channel and period of interest directly on GEA.
2. Download the dataset to your computer and into a directory structure consistent with SITE and SYSTEM.
3. Process the Raw data on your computer to generate pickles which properly format large data sets into a binary form.
4. Generate scatter plots.

## Gemini South
### Harvest
1. Login to software@geasouth.
2. Use the python script **/export/home/software/archiveExport.py** below to harvest full sample rate data.
3. Taylor this script for the daterange, channels and output directories of your choice.
```python
from subprocess import call
import sys, datetime, shlex

dt = datetime.datetime(2017, 11, 30, 18, 00, 00)
end = datetime.datetime(2017, 12, 4)
step = datetime.timedelta(hours=12)
indexfile = '/gemsoft/var/data/gea/data/data/mcs/master_index'
#indexfile = '/gemsoft/var/data/gea/data/data/crcs/master_index'
channel = 'mc:azDemandPos'
#channel = 'cr:crDemandPos'
outpath = '/export/home/software/mrippa/mcs'
#outpath = '/export/home/software/mrippa/crcs'
site = 'CPO'

while dt < end:
    daystart = dt.strftime('%m/%d/%Y %H:%M:%S')
    outname = "%s/%s_%sexport.txt" % (outpath, dt.strftime('%Y-%m-%d'), site)
    dt += step
    dayend = dt.strftime('%m/%d/%Y %H:%M:%S')
    command = "ArchiveExport %s -m \"%s\" -s \"%s\" -e \"%s\" -o %s" % (indexfile, channel, daystart, dayend, outname)
    dt += step
    args = shlex.split(command)
    print "Processing %s ..." % (outname)
    #print args
    call(args)
```
4. Run the script to get your data in the outpath.
### Download

### Process

### Generate


## Gemini North
